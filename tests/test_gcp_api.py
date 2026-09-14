from fastapi.testclient import TestClient

from gcp_dash.config import Settings
from gcp_dash.main import create_app
from tests.conftest import FakeGcpProvider


def test_get_instances(client):
    body = client.get("/api/gcp/instances").json()
    assert body["kind"] == "instances"
    assert body["error"] is None
    assert body["fetched_at"] is not None
    assert body["items"][0]["name"] == "vm-a"


def test_get_project_is_single_object(client):
    body = client.get("/api/gcp/project").json()
    assert body["items"]["project_id"] == "test-project"


def test_unknown_kind_404(client):
    assert client.get("/api/gcp/widgets").status_code == 404


def test_error_is_reported_in_body():
    app = create_app(Settings(gcp_project="p"), gcp_provider=FakeGcpProvider(fail={"list_buckets"}))
    body = TestClient(app).get("/api/gcp/buckets").json()
    assert body["items"] is None and "permission denied" in body["error"]


def test_refresh_query_and_endpoint(client, provider):
    client.get("/api/gcp/networks")
    client.get("/api/gcp/networks")
    client.get("/api/gcp/networks?refresh=true")
    assert client.post("/api/gcp/refresh").status_code == 204
    client.get("/api/gcp/networks")
    assert provider.calls.count("list_networks") == 3
