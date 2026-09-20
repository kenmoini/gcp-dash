import logging
import threading

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


def test_provider_construction_does_not_block_other_fetches():
    started = threading.Event()
    release = threading.Event()
    call_count = []

    def factory():
        call_count.append(1)
        started.set()
        assert release.wait(timeout=5)
        return FakeGcpProvider()

    svc = GcpService(TTLCache(60), factory, "test-project")
    results = {}

    def run_instances():
        results["instances"] = svc.fetch("instances")

    t1 = threading.Thread(target=run_instances)
    t1.start()
    assert started.wait(timeout=5)

    def run_buckets():
        results["buckets"] = svc.fetch("buckets")

    t2 = threading.Thread(target=run_buckets)
    t2.start()

    # The second fetch also needs the provider, so it legitimately blocks too -
    # but it is not deadlocked: it makes progress once released, same as the first.
    t2.join(timeout=0.2)
    assert t2.is_alive()

    release.set()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert not t1.is_alive() and not t2.is_alive()
    assert results["instances"].value[0].name == "vm-a"
    assert results["buckets"].value[0].name == "bucket-a"
    assert len(call_count) >= 1


def _records(caplog, level):
    return [r for r in caplog.records if r.name == "gcp_dash.gcp.service" and r.levelno == level]


def test_failed_fetch_logs_warning_with_traceback_at_debug(caplog):
    caplog.set_level(logging.DEBUG, logger="gcp_dash.gcp.service")
    svc = GcpService(TTLCache(60), lambda: FakeGcpProvider(fail={"list_firewalls"}), "p")
    svc.fetch("firewalls")
    [record] = _records(caplog, logging.WARNING)
    assert "kind=firewalls" in record.getMessage() and "permission denied" in record.getMessage()
    assert record.exc_info is not None


def test_failed_fetch_logs_warning_without_traceback_at_info(caplog):
    caplog.set_level(logging.INFO, logger="gcp_dash.gcp.service")
    svc = GcpService(TTLCache(60), lambda: FakeGcpProvider(fail={"list_firewalls"}), "p")
    svc.fetch("firewalls")
    [record] = _records(caplog, logging.WARNING)
    assert not record.exc_info


def test_successful_fetch_logs_info(caplog):
    caplog.set_level(logging.INFO, logger="gcp_dash.gcp.service")
    svc = GcpService(TTLCache(60), lambda: FakeGcpProvider(), "p")
    svc.fetch("instances")
    [record] = _records(caplog, logging.INFO)
    assert "kind=instances items=1" in record.getMessage()


def test_provider_construction_failure_is_logged(caplog):
    caplog.set_level(logging.INFO, logger="gcp_dash.gcp.service")

    def factory():
        raise GcpError("could not load Google credentials")

    GcpService(TTLCache(60), factory, None).fetch("project")
    [record] = _records(caplog, logging.WARNING)
    assert "could not load Google credentials" in record.getMessage()
