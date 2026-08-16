# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_http/test_integration.py
# === QV-LLM:END ===

"""
Integration tests for the HTTP adapter.
"""

import time
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from quack_core.adapters.http.app import create_app
from quack_core.adapters.http.config import HttpAdapterConfig
from quack_core.core.jobs import InMemoryJobStore, ThreadPoolJobRunner
from quack_core.core.registry import OperationRegistry


class _QuackMediaRequest(BaseModel):
    """Request model for the test-only quack-media.* operations registered
    below -- see conftest.py's own copy for the full rationale. Accepts
    arbitrary extra params since these tests post varied param shapes."""

    model_config = {"extra": "allow"}


def _make_quackmedia_operation(
    op_name: str,
) -> Callable[[_QuackMediaRequest], dict[str, Any]]:
    """Test-only stand-in: reports success, the operation name, and
    echoes params, matching what test_full_job_workflow /
    test_sync_vs_async_consistency assert."""

    def _op(req: _QuackMediaRequest) -> dict[str, Any]:
        return {"success": True, "operation": op_name, "params": req.model_dump()}

    return _op


@pytest.fixture
def integration_client() -> TestClient:
    """Create client for integration testing.

    Builds its own registry/job_store/job_runner and passes them via
    create_app's DI parameters -- bare TestClient(app) never triggers
    FastAPI's lifespan handler (that only runs when TestClient is entered
    as a context manager), so app.state.registry/job_store/job_runner
    would otherwise never be populated. See conftest.py's test_app
    fixture for the same rationale in more detail.
    """
    config = HttpAdapterConfig(
        auth_token="integration-test-token",  # noqa: S106 -- test fixture, fake credential value, not a real secret
        max_workers=1,
        job_ttl_seconds=30,
    )
    registry = OperationRegistry()
    registry.register(
        name="quack-media.slice_video",
        callable_=_make_quackmedia_operation("quack-media.slice_video"),
        request_model=_QuackMediaRequest,
    )
    job_store = InMemoryJobStore()
    job_runner = ThreadPoolJobRunner(registry=registry, store=job_store, max_workers=1)
    app = create_app(
        config, registry=registry, job_store=job_store, job_runner=job_runner
    )
    return TestClient(app)


@pytest.fixture
def integration_headers() -> dict[str, str]:
    """Auth headers for integration tests."""
    return {"Authorization": "Bearer integration-test-token"}


def test_full_job_workflow(
    integration_client: TestClient, integration_headers: dict[str, str]
) -> None:
    """Test complete job workflow from creation to completion."""
    # Create job
    create_response = integration_client.post(
        "/jobs",
        json={
            "op": "quack-media.slice_video",
            "params": {
                "input_path": "/test/input.mp4",
                "output_path": "/test/output.mp4",
                "start": "00:00:10",
                "end": "00:00:20",
            },
        },
        headers=integration_headers,
    )

    assert create_response.status_code == 200
    job_data = create_response.json()
    job_id = job_data["job_id"]

    # Poll for completion
    max_attempts = 20
    for _attempt in range(max_attempts):
        status_response = integration_client.get(
            f"/jobs/{job_id}", headers=integration_headers
        )

        if status_response.status_code == 200:
            status_data = status_response.json()
            if status_data["status"] in ["done", "error"]:
                break

        time.sleep(0.1)

    # Verify we got a response
    assert status_response.status_code == 200
    assert status_data["status"] == "done"
    assert status_data["result"]["success"] is True
    assert "input_path" in status_data["result"]["params"]


def test_sync_vs_async_consistency(
    integration_client: TestClient, integration_headers: dict[str, str]
) -> None:
    """Test that sync (/ops) and async (/jobs) invocation of the same
    operation return consistent results. The old dedicated
    "/quack-media/slice" sync route was retired in favor of the generic
    /ops/{op_name} interface (operations.py's own docstring); /ops IS the
    current sync surface, so this test now exercises that."""
    params = {
        "input_path": "/test.mp4",
        "output_path": "/out.mp4",
        "start": "00:00:05",
        "end": "00:00:10",
    }

    # Test sync endpoint
    sync_response = integration_client.post(
        "/ops/quack-media.slice_video", json=params, headers=integration_headers
    )
    assert sync_response.status_code == 200
    sync_result = sync_response.json()["data"]

    # Test async endpoint
    async_response = integration_client.post(
        "/jobs",
        json={"op": "quack-media.slice_video", "params": params},
        headers=integration_headers,
    )

    job_id = async_response.json()["job_id"]

    # Wait for async completion
    for _ in range(20):
        status_response = integration_client.get(
            f"/jobs/{job_id}", headers=integration_headers
        )

        if status_response.status_code == 200:
            status_data = status_response.json()
            if status_data["status"] == "done":
                break
        time.sleep(0.1)

    async_result = status_data["result"]

    # Results should be consistent
    assert sync_result["success"] == async_result["success"]
    assert sync_result["operation"] == async_result["operation"]


def test_health_endpoints(integration_client: TestClient) -> None:
    """Test health endpoints work without auth."""
    # Health endpoints should work without auth
    live_response = integration_client.get("/health/live")
    assert live_response.status_code == 200
    assert live_response.json() == {"ok": True}

    ready_response = integration_client.get("/health/ready")
    assert ready_response.status_code == 200
    assert ready_response.json() == {"ok": True}


def test_cors_headers(integration_client: TestClient) -> None:
    """Test CORS handling."""
    # This is a basic test - full CORS testing would require
    # configuring CORS origins and testing preflight requests
    response = integration_client.get("/health/live")
    assert response.status_code == 200


def test_openapi_docs(integration_client: TestClient) -> None:
    """Test that OpenAPI documentation is available."""
    docs_response = integration_client.get("/docs")
    # Should redirect or return HTML
    assert docs_response.status_code in [200, 307]

    openapi_response = integration_client.get("/openapi.json")
    assert openapi_response.status_code == 200

    openapi_data = openapi_response.json()
    assert "openapi" in openapi_data
    assert "info" in openapi_data
    assert openapi_data["info"]["title"] == "QuackCore API"
