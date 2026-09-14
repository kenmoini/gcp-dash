import pytest
from fastapi.testclient import TestClient

from gcp_dash.config import Settings
from gcp_dash.gcp.models import Bucket, FirewallRule, Instance, Network, Project, Subnetwork
from gcp_dash.gcp.provider import GcpError
from gcp_dash.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(gcp_project="test-project", gcp_cache_ttl_seconds=60, controls_enabled=True)


class FakeGcpProvider:
    project_id = "test-project"

    def __init__(self, fail: set[str] | None = None):
        self.fail = fail or set()
        self.calls: list[str] = []

    def _maybe_fail(self, name: str):
        self.calls.append(name)
        if name in self.fail:
            raise GcpError(f"{name} failed: permission denied")

    def get_project(self):
        self._maybe_fail("get_project")
        return Project("test-project", "Test Project", "123456", "ACTIVE")

    def list_instances(self):
        self._maybe_fail("list_instances")
        return [Instance("vm-a", "us-central1-a", "e2-small", "RUNNING", "10.0.0.2", "34.1.1.1")]

    def list_buckets(self):
        self._maybe_fail("list_buckets")
        return [Bucket("bucket-a", "US", "STANDARD", "2024-01-01T00:00:00+00:00")]

    def list_networks(self):
        self._maybe_fail("list_networks")
        return [Network("default", True, 3, "REGIONAL")]

    def list_subnetworks(self):
        self._maybe_fail("list_subnetworks")
        return [Subnetwork("default", "us-central1", "default", "10.128.0.0/20", False)]

    def list_firewalls(self):
        self._maybe_fail("list_firewalls")
        return [FirewallRule("allow-ssh", "default", "INGRESS", 1000, "allow", "tcp:22", ["0.0.0.0/0"], [])]


@pytest.fixture
def provider() -> FakeGcpProvider:
    return FakeGcpProvider()


@pytest.fixture
def app(settings, provider):
    return create_app(settings, gcp_provider=provider)


@pytest.fixture
def client(app):
    return TestClient(app)
