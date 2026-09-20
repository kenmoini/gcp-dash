import logging

from gcp_dash import logging_setup
from gcp_dash.config import Settings
from gcp_dash.logging_setup import (
    MAX_EXTRA_CHARS,
    REDACTED,
    GoogleExtraFormatter,
    configure_logging,
)


def _record(msg="hello", **extra) -> logging.LogRecord:
    record = logging.LogRecord("google.test", logging.DEBUG, __file__, 1, msg, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_configure_logging_is_idempotent():
    configure_logging(Settings())
    configure_logging(Settings())
    ours = [h for h in logging.getLogger().handlers if h is logging_setup._HANDLER]
    assert len(ours) == 1


def test_gcp_debug_enables_google_and_urllib3_debug():
    configure_logging(Settings(gcp_debug=True))
    google = logging.getLogger("google")
    assert google.level == logging.DEBUG and google.propagate is True
    assert logging.getLogger("urllib3").level == logging.DEBUG
    assert logging.getLogger("gcp_dash.gcp").level == logging.DEBUG

    configure_logging(Settings(gcp_debug=False))
    assert logging.getLogger("google").level == logging.INFO
    assert logging.getLogger("google").propagate is True
    assert logging.getLogger("urllib3").level == logging.NOTSET
    assert logging.getLogger("gcp_dash.gcp").level == logging.NOTSET


def test_log_level_sets_root():
    configure_logging(Settings(log_level="DEBUG"))
    assert logging.getLogger().level == logging.DEBUG
    configure_logging(Settings(log_level="INFO"))
    assert logging.getLogger().level == logging.INFO


def test_formatter_renders_and_redacts_google_extras():
    fmt = GoogleExtraFormatter("%(levelname)s %(name)s: %(message)s")
    out = fmt.format(
        _record(
            httpRequest={
                "url": "https://sts.googleapis.com/v1/token",
                "headers": {"Authorization": "Bearer abc", "Content-Type": "x"},
                "body": {"subject_token": "jwt", "grant_type": "exchange"},
            },
            rpcName="Exchange",
        )
    )
    assert out.startswith("DEBUG google.test: hello | ")
    assert "https://sts.googleapis.com/v1/token" in out
    assert "exchange" in out and "Exchange" in out
    assert REDACTED in out
    assert "Bearer abc" not in out and "jwt" not in out


def test_formatter_without_extras_is_plain():
    fmt = GoogleExtraFormatter("%(message)s")
    assert fmt.format(_record("plain")) == "plain"


def test_formatter_truncates_large_extras():
    fmt = GoogleExtraFormatter("%(message)s")
    out = fmt.format(_record(httpResponse={"payload": "x" * 100_000}))
    assert "truncated" in out
    assert len(out) < MAX_EXTRA_CHARS + 200
