# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_http/conftest.py
# role: tests
# neighbors: __init__.py, test_auth.py, test_config.py, test_integration.py, test_jobs.py, test_routes_jobs.py (+2 more)
# exports: clear_job_state, test_config, test_app, test_client, auth_headers, no_auth_config, no_auth_client
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
Test configuration for HTTP adapter tests.
"""

import pytest
from fastapi.testclient import TestClient

from quack_core.adapters.http.config import HttpAdapterConfig
from quack_core.adapters.http.app import create_app
from quack_core.adapters.http.jobs import clear_jobs


@pytest.fixture(autouse=True)
def clear_job_state():
    """Clear job state before each test."""
    clear_jobs()
    yield
    clear_jobs()


@pytest.fixture
def test_config():
    """Create test configuration."""
    return HttpAdapterConfig(
        auth_token="test-token",
        job_ttl_seconds=60,
        max_workers=2,
        request_timeout_seconds=30
    )


@pytest.fixture
def test_app(test_config):
    """Create test FastAPI app."""
    return create_app(test_config)


@pytest.fixture
def test_client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def auth_headers():
    """Create auth headers for testing."""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def no_auth_config():
    """Create config without auth for testing."""
    return HttpAdapterConfig(auth_token=None)


@pytest.fixture
def no_auth_client(no_auth_config):
    """Create client without auth."""
    app = create_app(no_auth_config)
    return TestClient(app)