import time

from gcp_dash.cpu_load import CpuLoad


def test_start_and_stop_workers():
    load = CpuLoad()
    assert load.status() == {"active": False, "workers": 0}
    load.start(1)
    try:
        assert load.status()["active"] is True
        assert load.status()["workers"] == 1
        time.sleep(0.2)
        assert all(p.is_alive() for p in load._procs)
    finally:
        load.stop()
    assert load.status() == {"active": False, "workers": 0}


def test_start_is_idempotent_and_clamped():
    load = CpuLoad()
    load.start(1)
    load.start(4)  # ignored while running
    try:
        assert load.status()["workers"] == 1
    finally:
        load.stop()
    load.start(0)  # clamps to at least 1
    try:
        assert load.status()["workers"] == 1
    finally:
        load.stop()
