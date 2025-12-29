# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_adapters/test_http_adapter.py
# role: tests
# neighbors: __init__.py
# exports: EchoRequest, EchoResponse, TestAppBootstrap, TestAuthentication, TestOperationsRegistry, TestJobExecution, TestIdempotency, TestDirectOperationInvocation (+6 more)
# git_branch: refactor/toolkitWorkflow
# git_commit: e4fa88d
# === QV-LLM:END ===



"""
Comprehensive test suite for HTTP adapter with dependency injection.
"""

import time
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from quack_core.adapters.http.app import create_app
from quack_core.adapters.http.config import HttpAdapterConfig
from quack_core.lib.registry import get_registry, reset_registry


class EchoRequest(BaseModel):
    """Test request model."""
    text: str


class EchoResponse(BaseModel):
    """Test response model."""
    echoed: str


def echo_operation(req: EchoRequest) -> dict[str, Any]:
    """Test operation."""
    return {"echoed": f"Echo: {req.text}"}


@pytest.fixture
def registry():
    """Provide clean registry for each test."""
    reset_registry()
    reg = get_registry()

    # Register test operation
    reg.register(
        name="test.echo",
        callable=echo_operation,
        request_model=EchoRequest,
        response_model=EchoResponse,
        description="Echo test operation",
        tags=["test"],
    )

    yield reg

    reset_registry()


@pytest.fixture
def config():
    """Provide test configuration."""
    return HttpAdapterConfig(
        host="0.0.0.0",
        port=8080,
        auth_token="test-token-123",
        hmac_secret="test-secret",
        max_workers=2,
    )


@pytest.fixture
def client(config, registry):
    """Provide test client with injected dependencies."""
    from quack_core.lib.jobs import InMemoryJobStore, ThreadPoolJobRunner

    # Create test store and runner
    store = InMemoryJobStore()
    runner = ThreadPoolJobRunner(
        registry=registry,
        store=store,
        max_workers=2,
        hmac_secret=config.hmac_secret,
    )

    # Create app with injected dependencies
    app = create_app(
        config,
        registry=registry,
        job_store=store,
        job_runner=runner,
    )

    client = TestClient(app)

    yield client

    # Cleanup
    runner.shutdown(wait=False)


class TestAppBootstrap:
    """Test application initialization."""

    def test_app_boots(self, client):
        """App should boot successfully."""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_config_in_state(self, client, config):
        """Config should be available in app state."""
        assert client.app.state.cfg == config

    def test_job_system_initialized(self, client):
        """Job system should be initialized."""
        assert hasattr(client.app.state, "job_store")
        assert hasattr(client.app.state, "job_runner")
        assert hasattr(client.app.state, "registry")


class TestAuthentication:
    """Test authentication enforcement."""

    def test_health_no_auth_required(self, client):
        """Health endpoints should not require auth."""
        response = client.get("/health/live")
        assert response.status_code == 200

        response = client.get("/health/ready")
        assert response.status_code == 200

    def test_jobs_require_auth(self, client):
        """Job endpoints should require auth."""
        response = client.post("/jobs", json={
            "op": "test.echo",
            "params": {"text": "hello"},
        })
        assert response.status_code == 401

    def test_valid_auth_accepted(self, client):
        """Valid auth token should be accepted."""
        response = client.post(
            "/jobs",
            json={
                "op": "test.echo",
                "params": {"text": "hello"},
            },
            headers={"Authorization": "Bearer test-token-123"},
        )
        assert response.status_code == 200

    def test_invalid_auth_rejected(self, client):
        """Invalid auth token should be rejected."""
        response = client.post(
            "/jobs",
            json={
                "op": "test.echo",
                "params": {"text": "hello"},
            },
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert response.status_code == 401


class TestOperationsRegistry:
    """Test operations registry integration."""

    def test_list_operations(self, client):
        """Should list registered operations."""
        response = client.get(
            "/ops",
            headers={"Authorization": "Bearer test-token-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "operations" in data
        assert len(data["operations"]) == 1
        assert data["operations"][0]["name"] == "test.echo"

    def test_unsupported_operation_errors(self, client):
        """Unsupported operation should return 400 with structured error."""
        response = client.post(
            "/jobs",
            json={
                "op": "nonexistent.operation",
                "params": {},
            },
            headers={"Authorization": "Bearer test-token-123"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "OPERATION_NOT_FOUND"
        assert "nonexistent.operation" in data["detail"]["error"]["message"]


class TestJobExecution:
    """Test job execution flow."""

    def test_enqueue_job(self, client):
        """Should enqueue a job."""
        response = client.post(
            "/jobs",
            json={
                "op": "test.echo",
                "params": {"text": "hello"},
            },
            headers={"Authorization": "Bearer test-token-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"

    def test_job_status_transitions(self, client):
        """Job should transition from queued -> running -> done."""
        # Enqueue job
        response = client.post(
            "/jobs",
            json={
                "op": "test.echo",
                "params": {"text": "hello"},
            },
            headers={"Authorization": "Bearer test-token-123"},
        )
        job_id = response.json()["job_id"]

        # Wait for completion
        time.sleep(0.2)

        # Check status
        response = client.get(
            f"/jobs/{job_id}",
            headers={"Authorization": "Bearer test-token-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "done"
        assert data["result"]["echoed"] == "Echo: hello"

    def test_job_not_found(self, client):
        """Should return 404 for nonexistent job."""
        response = client.get(
            "/jobs/nonexistent-id",
            headers={"Authorization": "Bearer test-token-123"},
        )
        assert response.status_code == 404


class TestIdempotency:
    """Test idempotency handling."""

    def test_idempotency_key_header(self, client):
        """Should handle idempotency key in header."""
        # First request
        response1 = client.post(
            "/jobs",
            json={
                "op": "test.echo",
                "params": {"text": "hello"},
            },
            headers={
                "Authorization": "Bearer test-token-123",
                "Idempotency-Key": "test-key-1",
            },
        )
        job_id_1 = response1.json()["job_id"]

        # Second request with same key
        response2 = client.post(
            "/jobs",
            json={
                "op": "test.echo",
                "params": {"text": "hello"},
            },
            headers={
                "Authorization": "Bearer test-token-123",
                "Idempotency-Key": "test-key-1",
            },
        )
        job_id_2 = response2.json()["job_id"]

        assert job_id_1 == job_id_2

    def test_idempotency_key_body(self, client):
        """Should handle idempotency key in body."""
        # First request
        response1 = client.post(
            "/jobs",
            json={
                "op": "test.echo",
                "params": {"text": "hello"},
                "idempotency_key": "test-key-2",
            },
            headers={"Authorization": "Bearer test-token-123"},
        )
        job_id_1 = response1.json()["job_id"]

        # Second request with same key
        response2 = client.post(
            "/jobs",
            json={
                "op": "test.echo",
                "params": {"text": "hello"},
                "idempotency_key": "test-key-2",
            },
            headers={"Authorization": "Bearer test-token-123"},
        )
        job_id_2 = response2.json()["job_id"]

        assert job_id_1 == job_id_2


class TestDirectOperationInvocation:
    """Test direct operation invocation."""

    def test_invoke_operation_sync(self, client):
        """Should invoke operation synchronously."""
        response = client.post(
            "/ops/test.echo",
            json={"text": "hello"},
            headers={"Authorization": "Bearer test-token-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["echoed"] == "Echo: hello"

    def test_invoke_operation_async(self, registry, client):
        """Should invoke async operation."""

        async def async_echo(req: EchoRequest) -> dict[str, Any]:
            return {"echoed": f"Async: {req.text}"}

        registry.register(
            name="test.async_echo",
            callable=async_echo,
            request_model=EchoRequest,
            description="Async echo operation",
        )

        response = client.post(
            "/ops/test.async_echo",
            json={"text": "hello"},
            headers={"Authorization": "Bearer test-token-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["echoed"] == "Async: hello"

    def test_invoke_nonexistent_operation(self, client):
        """Should return 404 with stable error shape for nonexistent operation."""
        response = client.post(
            "/ops/nonexistent.op",
            json={},
            headers={"Authorization": "Bearer test-token-123"},
        )
        assert response.status_code == 404
        data = response.json()
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "OPERATION_NOT_FOUND"

    def test_validation_error_stable_shape(self, client):
        """Should return 400 with stable error shape for validation errors."""
        response = client.post(
            "/ops/test.echo",
            json={"wrong_field": "hello"},
            headers={"Authorization": "Bearer test-token-123"},
        )
        assert response.status_code == 400
        data = response.json()
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "VALIDATION_ERROR"


class TestCallbackSigning:
    """Test callback signature generation and posting."""

    def test_sign_payload(self):
        """Should generate valid HMAC signature."""
        from quack_core.adapters.http.auth import sign_payload

        payload = {"job_id": "123", "status": "done"}
        signature = sign_payload(payload, "test-secret")

        assert signature.startswith("sha256=")
        assert len(signature) > 7

    def test_signature_consistent(self):
        """Same payload should produce same signature."""
        from quack_core.adapters.http.auth import sign_payload

        payload = {"job_id": "123", "status": "done"}
        sig1 = sign_payload(payload, "test-secret")
        sig2 = sign_payload(payload, "test-secret")

        assert sig1 == sig2

    def test_signature_changes_with_payload(self):
        """Different payloads should produce different signatures."""
        from quack_core.adapters.http.auth import sign_payload

        payload1 = {"job_id": "123", "status": "done"}
        payload2 = {"job_id": "456", "status": "done"}

        sig1 = sign_payload(payload1, "test-secret")
        sig2 = sign_payload(payload2, "test-secret")

        assert sig1 != sig2

    @patch('quack_core.adapters.http.util.httpx.AsyncClient')
    def test_post_callback(self, mock_client):
        """Should post callback with signature header."""
        import asyncio
        from quack_core.adapters.http.util import post_callback

        # Setup mock
        mock_post = AsyncMock()
        mock_client.return_value.__aenter__.return_value.post = mock_post

        # Call function
        body = {"job_id": "123", "status": "done"}
        signature = "sha256=abc123"

        asyncio.run(post_callback("https://example.com/callback", body, signature))

        # Verify call
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"] == body
        assert call_kwargs["headers"]["X-Quack-Signature"] == signature


class TestErrorHandling:
    """Test error handling."""

    def test_operation_error_captured(self, registry, client):
        """Operation errors should be captured in job status."""

        def failing_op(req: EchoRequest) -> dict[str, Any]:
            raise ValueError("Operation failed")

        registry.register(
            name="test.failing",
            callable=failing_op,
            request_model=EchoRequest,
            description="Failing operation",
        )

        # Enqueue job
        response = client.post(
            "/jobs",
            json={
                "op": "test.failing",
                "params": {"text": "hello"},
            },
            headers={"Authorization": "Bearer test-token-123"},
        )
        job_id = response.json()["job_id"]

        # Wait for completion
        time.sleep(0.2)

        # Check status
        response = client.get(
            f"/jobs/{job_id}",
            headers={"Authorization": "Bearer test-token-123"},
        )
        data = response.json()
        assert data["status"] == "error"
        assert "Operation failed" in data["error"]

    def test_validation_error_in_job(self, client):
        """Invalid params should return 400 validation error immediately."""
        response = client.post(
            "/jobs",
            json={
                "op": "test.echo",
                "params": {"wrong_field": "hello"},
            },
            headers={"Authorization": "Bearer test-token-123"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "VALIDATION_ERROR"

    def test_job_not_found_error_shape(self, client):
        """Job not found should return structured error."""
        response = client.get(
            "/jobs/nonexistent-id",
            headers={"Authorization": "Bearer test-token-123"},
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"]["code"] == "JOB_NOT_FOUND"

    def test_async_operation_in_job(self, registry, client):
        """Async operations should work in jobs (not just direct invocation)."""

        async def async_echo(req: EchoRequest) -> dict[str, Any]:
            # Simulate async work
            import asyncio
            await asyncio.sleep(0.01)
            return {"echoed": f"Async Job: {req.text}"}

        registry.register(
            name="test.async_job",
            callable=async_echo,
            request_model=EchoRequest,
            description="Async echo for job testing",
        )

        # Enqueue async job
        response = client.post(
            "/jobs",
            json={
                "op": "test.async_job",
                "params": {"text": "hello"},
            },
            headers={"Authorization": "Bearer test-token-123"},
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]

        # Wait for completion
        time.sleep(0.3)

        # Check status
        response = client.get(
            f"/jobs/{job_id}",
            headers={"Authorization": "Bearer test-token-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "done"
        assert data["result"]["echoed"] == "Async Job: hello"