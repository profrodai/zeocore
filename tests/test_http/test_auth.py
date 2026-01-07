# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_http/test_auth.py
# role: tests
# neighbors: __init__.py, conftest.py, test_config.py, test_integration.py, test_jobs.py, test_routes_jobs.py (+2 more)
# exports: test_require_bearer_no_auth_configured, test_require_bearer_missing_header, test_require_bearer_wrong_scheme, test_require_bearer_wrong_token, test_require_bearer_success, test_sign_payload, test_health_endpoint_with_auth, test_health_endpoint_without_auth (+1 more)
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

"""
Tests for authentication functionality.
"""

import pytest
from quack_core.adapters.http.auth import require_bearer, sign_payload
from quack_core.adapters.http.config import HttpAdapterConfig


def test_require_bearer_no_auth_configured():
    """Test that auth is bypassed when not configured."""
    cfg = HttpAdapterConfig(auth_token=None)

    # Mock request without auth header
    class MockRequest:
        def __init__(self):
            self.headers = {}

    request = MockRequest()

    # Should not raise
    require_bearer(request, cfg)


def test_require_bearer_missing_header():
    """Test auth failure when header missing."""
    cfg = HttpAdapterConfig(auth_token="secret")

    class MockRequest:
        def __init__(self):
            self.headers = {}

    request = MockRequest()

    with pytest.raises(Exception) as exc_info:
        require_bearer(request, cfg)

    assert "Authorization header required" in str(exc_info.value)


def test_require_bearer_wrong_scheme():
    """Test auth failure with wrong scheme."""
    cfg = HttpAdapterConfig(auth_token="secret")

    class MockRequest:
        def __init__(self):
            self.headers = {"Authorization": "Basic dGVzdA=="}

    request = MockRequest()

    with pytest.raises(Exception) as exc_info:
        require_bearer(request, cfg)

    assert "Bearer token required" in str(exc_info.value)


def test_require_bearer_wrong_token():
    """Test auth failure with wrong token."""
    cfg = HttpAdapterConfig(auth_token="secret")

    class MockRequest:
        def __init__(self):
            self.headers = {"Authorization": "Bearer wrong-token"}

    request = MockRequest()

    with pytest.raises(Exception) as exc_info:
        require_bearer(request, cfg)

    assert "Invalid token" in str(exc_info.value)


def test_require_bearer_success():
    """Test successful auth."""
    cfg = HttpAdapterConfig(auth_token="secret")

    class MockRequest:
        def __init__(self):
            self.headers = {"Authorization": "Bearer secret"}

    request = MockRequest()

    # Should not raise
    require_bearer(request, cfg)


def test_sign_payload():
    """Test payload signing."""
    payload = {"job_id": "123", "status": "done"}
    secret = "test-secret"

    signature = sign_payload(payload, secret)

    assert signature.startswith("sha256=")
    assert len(signature) == 71  # "sha256=" + 64 hex chars

    # Test consistency
    signature2 = sign_payload(payload, secret)
    assert signature == signature2

    # Test different payload gives different signature
    payload2 = {"job_id": "456", "status": "done"}
    signature3 = sign_payload(payload2, secret)
    assert signature != signature3


def test_health_endpoint_with_auth(test_client, auth_headers):
    """Test health endpoint works with auth."""
    response = test_client.get("/health/live", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_health_endpoint_without_auth(no_auth_client):
    """Test health endpoint works without auth when not required."""
    response = no_auth_client.get("/health/live")
    assert response.status_code == 200


def test_health_endpoint_no_auth_required(no_auth_client):
    """Test health endpoint works when auth not required."""
    response = no_auth_client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
