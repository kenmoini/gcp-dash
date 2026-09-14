def test_live_ok_by_default(client):
    r = client.get("/healthz/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_ok_by_default(client):
    r = client.get("/healthz/ready")
    assert r.status_code == 200


def test_live_503_when_disabled(app, client):
    app.state.runtime.set_live(False)
    r = client.get("/healthz/live")
    assert r.status_code == 503
    assert r.json()["status"] == "failing"


def test_ready_503_when_disabled(app, client):
    app.state.runtime.set_ready(False)
    assert client.get("/healthz/ready").status_code == 503
    assert client.get("/healthz/live").status_code == 200
