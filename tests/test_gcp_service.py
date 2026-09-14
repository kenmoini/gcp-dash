import pytest

from gcp_dash.gcp.cache import TTLCache
from gcp_dash.gcp.provider import GcpError
from gcp_dash.gcp.service import KINDS, GcpService
from tests.conftest import FakeGcpProvider


def test_kinds():
    assert KINDS == ("project", "instances", "buckets", "networks", "subnetworks", "firewalls")


def test_fetch_uses_cache(provider):
    svc = GcpService(TTLCache(60), lambda: provider, "test-project")
    a = svc.fetch("instances")
    b = svc.fetch("instances")
    assert a.value[0].name == "vm-a" and a is b
    assert provider.calls == ["list_instances"]


def test_fetch_force_and_refresh_all(provider):
    svc = GcpService(TTLCache(60), lambda: provider, "test-project")
    svc.fetch("buckets")
    svc.fetch("buckets", force=True)
    svc.refresh_all()
    svc.fetch("buckets")
    assert provider.calls == ["list_buckets"] * 3


def test_provider_error_becomes_entry_error():
    svc = GcpService(TTLCache(60), lambda: FakeGcpProvider(fail={"list_firewalls"}), "p")
    entry = svc.fetch("firewalls")
    assert entry.value is None and "permission denied" in entry.error


def test_provider_construction_error_is_captured():
    def factory():
        raise GcpError("could not load Google credentials")

    svc = GcpService(TTLCache(60), factory, None)
    entry = svc.fetch("project")
    assert entry.error == "could not load Google credentials"
    assert svc.project_id is None


def test_unknown_kind():
    svc = GcpService(TTLCache(60), lambda: FakeGcpProvider(), "p")
    with pytest.raises(KeyError):
        svc.fetch("nope")
