import pytest
from fastapi.testclient import TestClient

from gcp_dash.config import Settings
from gcp_dash.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(gcp_project="test-project", gcp_cache_ttl_seconds=60, controls_enabled=True)


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    return TestClient(app)
