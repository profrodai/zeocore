# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_http/conftest.py
# role: tests
# neighbors: __init__.py, test_auth.py, test_config.py, test_integration.py, test_jobs.py, test_routes_jobs.py (+2 more)
# exports: clear_job_state, test_config, test_app, test_client, auth_headers, no_auth_config, no_auth_client, job_store, job_runner
# git_branch: feat/9-make-setup-work
# git_commit: f4879df3
# === QV-LLM:END ===

"""
Test configuration for HTTP adapter tests.
"""

import pytest
from fastapi.testclient import TestClient
from quack_core.adapters.http.app import create_app
from quack_core.adapters.http.config import HttpAdapterConfig
from quack_core.core.jobs import InMemoryJobStore, ThreadPoolJobRunner
from quack_core.core.registry import OperationRegistry


@pytest.fixture
def job_store():
    """Create a fresh job store for testing."""
    store = InMemoryJobStore()
    yield store
    store.clear()


@pytest.fixture
def test_registry():
    """Create a test operation registry."""
    return OperationRegistry()


@pytest.fixture
def job_runner(test_registry, job_store):
    """Create a job runner for testing."""
    runner = ThreadPoolJobRunner(
        registry=test_registry,
        store=job_store,
        max_workers=2
    )
    yield runner
    runner.shutdown(wait=True)


@pytest.fixture(autouse=True)
def clear_job_state(job_store):
    """Clear job state before and after each test."""
    job_store.clear()
    yield
    job_store.clear()


@pytest.fixture
def test_config():
    """Create test configuration."""
    return HttpAdapterConfig(
        auth_token="test-token",  # noqa: S106 -- test fixture, fake credential value, not a real secret
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
