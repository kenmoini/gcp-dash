import pytest
from fastapi.testclient import TestClient

from gcp_dash.config import Settings
from gcp_dash.main import create_app


def test_toggle_liveness_off_and_on(client):
    r = client.post("/controls/liveness", data={"enabled": "false"})
    assert r.status_code == 200
    assert r.json()["live"] is False
    assert client.get("/healthz/live").status_code == 503

    r = client.post("/controls/liveness", data={"enabled": "true"})
    assert r.json()["live"] is True
    assert client.get("/healthz/live").status_code == 200


def test_toggle_readiness(client):
    client.post("/controls/readiness", data={"enabled": "false"})
    assert client.get("/healthz/ready").status_code == 503
    assert client.get("/api/state").json()["ready"] is False


def test_crash_schedules_exit(app, client):
    calls = []
    app.state.exit_fn = lambda code: calls.append(code)
    r = client.post("/controls/crash", data={"exit_code": "3"})
    assert r.status_code == 202
    assert r.json()["exit_code"] == 3
    # crash fires on a 0.5 s timer; wait for it
    import time

    deadline = time.time() + 3
    while not calls and time.time() < deadline:
        time.sleep(0.05)
    assert calls == [3]


def test_controls_disabled_returns_403():
    app = create_app(Settings(controls_enabled=False))
    c = TestClient(app)
    assert c.post("/controls/liveness", data={"enabled": "false"}).status_code == 403
    assert c.post("/controls/crash", data={"exit_code": "1"}).status_code == 403
    assert c.get("/healthz/live").status_code == 200


@pytest.mark.parametrize("bad", ["-1", "256", "abc"])
def test_crash_rejects_bad_exit_code(client, bad):
    assert client.post("/controls/crash", data={"exit_code": bad}).status_code == 422


def test_cpu_load_toggle(app, client):
    try:
        r = client.post("/controls/cpu", data={"enabled": "true", "workers": "1"})
        assert r.status_code == 200
        assert r.json()["cpu_load"] == {"active": True, "workers": 1}
    finally:
        r = client.post("/controls/cpu", data={"enabled": "false"})
    assert r.json()["cpu_load"] == {"active": False, "workers": 0}
