from fastapi.testclient import TestClient

from gcp_dash.config import Settings
from gcp_dash.main import create_app
from tests.conftest import FakeGcpProvider


def test_index_renders_runtime_and_controls(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert "Runtime" in html and 'id="controls"' in html
    assert "/static/htmx.min.js" in html


def test_runtime_partial(client):
    r = client.get("/partials/runtime")
    assert r.status_code == 200
    assert "Orchestrator" in r.text


def test_controls_partial_reflects_state(app, client):
    app.state.runtime.set_ready(False)
    html = client.get("/partials/controls").text
    assert "Readiness" in html and "FAILING" in html


def test_htmx_post_returns_controls_fragment(client):
    r = client.post("/controls/liveness", data={"enabled": "false"}, headers={"HX-Request": "true"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert 'id="controls"' in r.text and "FAILING" in r.text


def test_gcp_page_has_lazy_panels(client):
    html = client.get("/gcp").text
    for kind in ("project", "instances", "buckets", "networks", "subnetworks", "firewalls"):
        assert f'hx-get="/partials/gcp/{kind}"' in html


def test_gcp_instances_partial(client):
    html = client.get("/partials/gcp/instances").text
    assert "vm-a" in html and "us-central1-a" in html and "34.1.1.1" in html


def test_gcp_partial_shows_error_banner():
    app = create_app(Settings(gcp_project="p"), gcp_provider=FakeGcpProvider(fail={"list_networks"}))
    html = TestClient(app).get("/partials/gcp/networks").text
    assert 'class="error"' in html and "permission denied" in html


def test_gcp_partial_unknown_kind_404(client):
    assert client.get("/partials/gcp/nope").status_code == 404


def test_controls_hidden_when_disabled():
    app = create_app(Settings(controls_enabled=False), gcp_provider=FakeGcpProvider())
    html = TestClient(app).get("/").text
    assert "Controls are disabled" in html
