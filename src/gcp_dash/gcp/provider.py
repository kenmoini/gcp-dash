from __future__ import annotations

import logging
import os
from typing import Any, Protocol

from gcp_dash.gcp.models import Bucket, FirewallRule, Instance, Network, Project, Subnetwork

log = logging.getLogger(__name__)


class GcpError(Exception):
    """Any failure talking to GCP, with a message safe to show in the UI."""


class GcpProvider(Protocol):
    project_id: str

    def get_project(self) -> Project: ...
    def list_instances(self) -> list[Instance]: ...
    def list_buckets(self) -> list[Bucket]: ...
    def list_networks(self) -> list[Network]: ...
    def list_subnetworks(self) -> list[Subnetwork]: ...
    def list_firewalls(self) -> list[FirewallRule]: ...


def _short(url: str | None) -> str:
    return (url or "").rsplit("/", 1)[-1]


# --- pure mapping functions (duck-typed so tests can use SimpleNamespace) ---

def instance_from_api(inst: Any) -> Instance:
    nics = list(getattr(inst, "network_interfaces", []) or [])
    internal = external = None
    if nics:
        internal = getattr(nics[0], "network_i_p", None) or None
        access = list(getattr(nics[0], "access_configs", []) or [])
        if access:
            external = getattr(access[0], "nat_i_p", None) or None
    return Instance(
        name=inst.name,
        zone=_short(inst.zone),
        machine_type=_short(inst.machine_type),
        status=str(inst.status),
        internal_ip=internal,
        external_ip=external,
    )


def bucket_from_api(b: Any) -> Bucket:
    created = getattr(b, "time_created", None)
    return Bucket(
        name=b.name,
        location=b.location or "",
        storage_class=b.storage_class or "",
        created=created.isoformat() if created else None,
    )


def network_from_api(n: Any) -> Network:
    routing = getattr(n, "routing_config", None)
    return Network(
        name=n.name,
        auto_subnets=bool(n.auto_create_subnetworks),
        subnet_count=len(list(getattr(n, "subnetworks", []) or [])),
        routing_mode=str(getattr(routing, "routing_mode", "") or ""),
    )


def subnetwork_from_api(s: Any) -> Subnetwork:
    return Subnetwork(
        name=s.name,
        region=_short(s.region),
        network=_short(s.network),
        cidr=s.ip_cidr_range,
        private_google_access=bool(s.private_ip_google_access),
    )


def _rules_text(entries: Any) -> str:
    parts = []
    for e in entries or []:
        proto = getattr(e, "I_p_protocol", "") or ""
        ports = list(getattr(e, "ports", []) or [])
        parts.append(f"{proto}:{','.join(ports)}" if ports else proto)
    return ", ".join(parts)


def firewall_from_api(f: Any) -> FirewallRule:
    allowed = list(getattr(f, "allowed", []) or [])
    denied = list(getattr(f, "denied", []) or [])
    action = "allow" if allowed else "deny"
    return FirewallRule(
        name=f.name,
        network=_short(f.network),
        direction=str(f.direction),
        priority=int(f.priority),
        action=action,
        rules=_rules_text(allowed if allowed else denied),
        source_ranges=list(getattr(f, "source_ranges", []) or []),
        target_tags=list(getattr(f, "target_tags", []) or []),
    )


def project_from_api(p: Any) -> Project:
    state = getattr(p, "state", "")
    return Project(
        project_id=p.project_id,
        display_name=p.display_name or p.project_id,
        number=_short(p.name),
        state=getattr(state, "name", str(state)),
    )


# --- live implementation ---

class LiveGcpProvider:
    """Wraps google-cloud-* clients. Constructed lazily; every method raises GcpError on failure."""

    def __init__(self, project_id: str | None = None) -> None:
        log.debug(
            "loading application default credentials (GOOGLE_APPLICATION_CREDENTIALS=%s)",
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
        )
        try:
            import google.auth

            self._credentials, default_project = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        except Exception as exc:  # DefaultCredentialsError etc.
            raise GcpError(f"could not load Google credentials: {exc}") from exc
        resolved = project_id or default_project
        if not resolved:
            raise GcpError("no GCP project: set GCP_PROJECT or use credentials that carry a project")
        self.project_id: str = resolved
        creds = self._credentials
        log.info(
            "google credentials loaded: type=%s service_account=%s quota_project=%s "
            "adc_file=%s default_project=%s project=%s (from %s)",
            type(creds).__name__,
            getattr(creds, "service_account_email", None),
            getattr(creds, "quota_project_id", None),
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
            default_project,
            resolved,
            "GCP_PROJECT" if project_id else "credentials",
        )

    def _call(self, fn):
        try:
            return fn()
        except GcpError:
            raise
        except Exception as exc:
            raise GcpError(f"{type(exc).__name__}: {exc}") from exc

    def get_project(self) -> Project:
        from google.cloud import resourcemanager_v3

        def go():
            client = resourcemanager_v3.ProjectsClient(credentials=self._credentials)
            return project_from_api(client.get_project(name=f"projects/{self.project_id}"))

        return self._call(go)

    def list_instances(self) -> list[Instance]:
        from google.cloud import compute_v1

        def go():
            client = compute_v1.InstancesClient(credentials=self._credentials)
            out = []
            for _zone, scoped in client.aggregated_list(project=self.project_id):
                out.extend(instance_from_api(i) for i in scoped.instances)
            return sorted(out, key=lambda i: (i.zone, i.name))

        return self._call(go)

    def list_buckets(self) -> list[Bucket]:
        from google.cloud import storage

        def go():
            client = storage.Client(project=self.project_id, credentials=self._credentials)
            return [bucket_from_api(b) for b in client.list_buckets()]

        return self._call(go)

    def list_networks(self) -> list[Network]:
        from google.cloud import compute_v1

        def go():
            client = compute_v1.NetworksClient(credentials=self._credentials)
            return [network_from_api(n) for n in client.list(project=self.project_id)]

        return self._call(go)

    def list_subnetworks(self) -> list[Subnetwork]:
        from google.cloud import compute_v1

        def go():
            client = compute_v1.SubnetworksClient(credentials=self._credentials)
            out = []
            for _region, scoped in client.aggregated_list(project=self.project_id):
                out.extend(subnetwork_from_api(s) for s in scoped.subnetworks)
            return sorted(out, key=lambda s: (s.region, s.name))

        return self._call(go)

    def list_firewalls(self) -> list[FirewallRule]:
        from google.cloud import compute_v1

        def go():
            client = compute_v1.FirewallsClient(credentials=self._credentials)
            return [firewall_from_api(f) for f in client.list(project=self.project_id)]

        return self._call(go)
