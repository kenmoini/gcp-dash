"""Process-wide logging configuration.

Two knobs from `Settings`:

- `log_level` sets the root logger, i.e. how chatty the app itself is.
- `gcp_debug` turns on request/response logging from the Google client libraries
  (`google.*`), connection-level lines from `urllib3`, and tracebacks for failed
  GCP fetches. It is independent of `log_level`.

The Google libraries (`google.api_core.client_logging`, `google.auth._helpers`) set the
`google` logger to `propagate=False` on first use *unless* the application configured that
logger already. Setting its level here counts as "configured", and we set `propagate=True`
explicitly so the records reach our root handler regardless of import order.

Those libraries put the interesting data (URL, status, payload, headers) in `extra` fields
on the record, which a plain `%(message)s` formatter drops. `GoogleExtraFormatter` renders
them as JSON after the message, redacting credentials and truncating large payloads.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from gcp_dash.config import Settings

# Extra fields emitted by google-api-core / google-auth at DEBUG level.
GOOGLE_EXTRA_FIELDS: tuple[str, ...] = (
    "serviceName",
    "rpcName",
    "httpRequest",
    "httpResponse",
    "request",
    "response",
    "metadata",
    "retryAttempt",
    "credentialsType",
    "credentialsInfo",
)

# Keys (case-insensitive, at any depth) whose values are replaced before logging. google-auth
# hashes a few token fields itself but logs `assertion`, `subject_token` and request headers
# (including `authorization: Bearer ...` on the IAM impersonation call) verbatim.
REDACTED_KEYS: frozenset[str] = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "x-goog-api-key",
        "cookie",
        "set-cookie",
        "assertion",
        "subject_token",
        "actor_token",
        "access_token",
        "accesstoken",
        "id_token",
        "refresh_token",
        "client_secret",
        "private_key",
        "token",
    }
)

REDACTED = "<redacted>"
MAX_EXTRA_CHARS = 32_768
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

_HANDLER: logging.Handler | None = None


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: (REDACTED if str(k).lower() in REDACTED_KEYS else _redact(v))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(v) for v in value]
    return value


def _truncate(text: str, limit: int = MAX_EXTRA_CHARS) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}…[truncated {len(text) - limit} chars]"


class GoogleExtraFormatter(logging.Formatter):
    """Standard formatter that appends recognised Google extra fields as redacted JSON."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = {
            name: getattr(record, name)
            for name in GOOGLE_EXTRA_FIELDS
            if getattr(record, name, None) is not None
        }
        if not extras:
            return base
        rendered = json.dumps(_redact(extras), default=str, separators=(",", ":"))
        return f"{base} | {_truncate(rendered)}"


def configure_logging(settings: Settings) -> None:
    """Idempotent: safe to call on every `create_app()`."""
    global _HANDLER
    root = logging.getLogger()
    if _HANDLER is None:
        _HANDLER = logging.StreamHandler(sys.stderr)
        _HANDLER.setFormatter(GoogleExtraFormatter(LOG_FORMAT))
    if _HANDLER not in root.handlers:
        root.addHandler(_HANDLER)
    root.setLevel(settings.log_level)

    debug = settings.gcp_debug
    logging.getLogger("gcp_dash.gcp").setLevel(logging.DEBUG if debug else logging.NOTSET)

    google = logging.getLogger("google")
    google.propagate = True
    google.setLevel(logging.DEBUG if debug else logging.INFO)

    logging.getLogger("urllib3").setLevel(logging.DEBUG if debug else logging.NOTSET)
