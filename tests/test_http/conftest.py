"""
Test configuration for HTTP adapter tests.
"""

from collections.abc import Callable, Generator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from zeo_core.adapters.http.app import create_app
from zeo_core.adapters.http.config import HttpAdapterConfig
from zeo_core.core.jobs import InMemoryJobStore, ThreadPoolJobRunner
from zeo_core.core.registry import OperationRegistry


@pytest.fixture
def job_store() -> Generator[InMemoryJobStore, None, None]:
    """Create a fresh job store for testing."""
    store = InMemoryJobStore()
    yield store
    store.clear()


class _ZeoMediaRequest(BaseModel):
    """Request model for the test-only zeo-media.* operations registered
    below. Accepts arbitrary extra params so the various route tests that
    post different param shapes (idempotency, callback_url, slice/
    transcribe/frame-extract params) all validate -- these stand in for
    the real zeo-media operations the tests exercise via the generic
    /jobs and /ops surfaces (the concrete zeo-media.* ROUTES were
    retired in favor of that generic interface, per operations.py's own
    docstring; there was never a real production zeo-media operation
    implementation to fall back on -- grep across zeocore/src finds
    zero references to transcribe_audio/extract_frames outside tests)."""

    model_config = {"extra": "allow"}


def _make_zeomedia_operation(
    op_name: str,
) -> Callable[[_ZeoMediaRequest], dict[str, Any]]:
    """Build a test-only stand-in operation body for `op_name`: reports
    success, the operation name, and echoes back the submitted params
    without doing any real file I/O, matching what test_job_lifecycle /
    test_full_job_workflow / test_routes_zeomedia.py assert."""

    def _op(req: _ZeoMediaRequest) -> dict[str, Any]:
        return {"success": True, "operation": op_name, "params": req.model_dump()}

    return _op


_ZEOMEDIA_OPERATIONS = (
    "zeo-media.slice_video",
    "zeo-media.transcribe_audio",
    "zeo-media.extract_frames",
)


@pytest.fixture
def test_registry() -> OperationRegistry:
    """Create a test operation registry, pre-populated with the
    zeo-media.* operations the /jobs and /ops route tests submit
    against."""
    registry = OperationRegistry()
    for op_name in _ZEOMEDIA_OPERATIONS:
        registry.register(
            name=op_name,
            callable_=_make_zeomedia_operation(op_name),
            request_model=_ZeoMediaRequest,
        )
    return registry


@pytest.fixture
def job_runner(
    test_registry: OperationRegistry, job_store: InMemoryJobStore
) -> Generator[ThreadPoolJobRunner, None, None]:
    """Create a job runner for testing."""
    runner = ThreadPoolJobRunner(registry=test_registry, store=job_store, max_workers=2)
    yield runner
    runner.shutdown(wait=True)


@pytest.fixture(autouse=True)
def clear_job_state(job_store: InMemoryJobStore) -> Generator[None, None, None]:
    """Clear job state before and after each test."""
    job_store.clear()
    yield
    job_store.clear()


@pytest.fixture
def test_config() -> HttpAdapterConfig:
    """Create test configuration."""
    return HttpAdapterConfig(
        auth_token="test-token",  # noqa: S106 -- test fixture, fake credential value, not a real secret
        job_ttl_seconds=60,
        max_workers=2,
        request_timeout_seconds=30,
    )


@pytest.fixture
def test_app(
    test_config: HttpAdapterConfig,
    test_registry: OperationRegistry,
    job_store: InMemoryJobStore,
    job_runner: ThreadPoolJobRunner,
) -> FastAPI:
    """Create test FastAPI app.

    Passes registry/job_store/job_runner explicitly via create_app's own
    documented DI parameters ("Optional registry override (for testing)").
    This is required, not cosmetic: FastAPI's lifespan handler only runs
    when TestClient is entered as a context manager (`with TestClient(...)`);
    bare `TestClient(app)` (what test_client below does) never triggers it,
    so app.state.registry/job_store/job_runner are never populated by the
    app's own startup path in tests. Injecting them here bypasses lifespan
    entirely and gives each test isolated, real state instead.
    """
    return create_app(
        test_config,
        registry=test_registry,
        job_store=job_store,
        job_runner=job_runner,
    )


@pytest.fixture
def test_client(test_app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Create auth headers for testing."""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def no_auth_config() -> HttpAdapterConfig:
    """Create config without auth for testing."""
    return HttpAdapterConfig(auth_token=None)


@pytest.fixture
def no_auth_client(no_auth_config: HttpAdapterConfig) -> TestClient:
    """Create client without auth."""
    app = create_app(no_auth_config)
    return TestClient(app)
