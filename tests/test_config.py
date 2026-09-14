from gcp_dash.config import Settings


def test_defaults_when_env_empty():
    s = Settings.from_env({})
    assert s.port == 8080
    assert s.gcp_project is None
    assert s.gcp_cache_ttl_seconds == 60
    assert s.controls_enabled is True


def test_reads_values_from_env():
    s = Settings.from_env(
        {
            "PORT": "9000",
            "GCP_PROJECT": "my-proj",
            "GCP_CACHE_TTL_SECONDS": "5",
            "CONTROLS_ENABLED": "false",
        }
    )
    assert s.port == 9000
    assert s.gcp_project == "my-proj"
    assert s.gcp_cache_ttl_seconds == 5
    assert s.controls_enabled is False


def test_empty_project_string_becomes_none():
    assert Settings.from_env({"GCP_PROJECT": ""}).gcp_project is None
