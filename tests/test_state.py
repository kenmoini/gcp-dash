from gcp_dash.state import RuntimeState


def test_defaults_are_healthy():
    s = RuntimeState()
    assert s.live is True
    assert s.ready is True


def test_toggles_and_snapshot():
    s = RuntimeState()
    s.set_live(False)
    s.set_ready(False)
    snap = s.snapshot()
    assert snap["live"] is False
    assert snap["ready"] is False
    assert snap["uptime_seconds"] >= 0
