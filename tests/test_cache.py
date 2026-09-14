from gcp_dash.gcp.cache import TTLCache


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def test_loader_called_once_within_ttl():
    clock = Clock()
    cache = TTLCache(ttl_seconds=60, clock=clock, wall=clock)
    calls = []
    entry = cache.get("k", lambda: calls.append(1) or "v1")
    assert entry.value == "v1" and entry.error is None and entry.fetched_at == 100.0
    clock.t += 30
    assert cache.get("k", lambda: calls.append(1) or "v2").value == "v1"
    assert len(calls) == 1


def test_reloads_after_ttl_and_on_force():
    clock = Clock()
    cache = TTLCache(ttl_seconds=60, clock=clock, wall=clock)
    cache.get("k", lambda: "v1")
    clock.t += 61
    assert cache.get("k", lambda: "v2").value == "v2"
    assert cache.get("k", lambda: "v3", force=True).value == "v3"


def test_error_keeps_previous_value():
    clock = Clock()
    cache = TTLCache(ttl_seconds=60, clock=clock, wall=clock)
    cache.get("k", lambda: ["old"])

    def boom():
        raise RuntimeError("quota exceeded")

    entry = cache.get("k", boom, force=True)
    assert entry.value == ["old"]
    assert entry.error == "quota exceeded"


def test_error_with_no_previous_value():
    cache = TTLCache(ttl_seconds=60)

    def boom():
        raise RuntimeError("nope")

    entry = cache.get("k", boom)
    assert entry.value is None and entry.error == "nope"


def test_invalidate_all():
    clock = Clock()
    cache = TTLCache(ttl_seconds=60, clock=clock, wall=clock)
    cache.get("k", lambda: "v1")
    cache.invalidate_all()
    assert cache.get("k", lambda: "v2").value == "v2"
