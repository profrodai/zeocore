# quack-core/tests/test_integrations/github/conftest.py
"""Shared fixtures for GitHub integration tests."""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
import requests

from quack_core.errors import QuackQuotaExceededError
from quack_core.integrations.core import (
    AuthProviderProtocol,
    AuthResult,
    ConfigProviderProtocol,
)
from quack_core.integrations.github.auth import GitHubAuthProvider
from quack_core.integrations.github.client import GitHubClient
from quack_core.integrations.github.config import GitHubConfigProvider
from quack_core.integrations.github.models import (
    GitHubRepo,
    GitHubUser,
    PullRequest,
    PullRequestStatus,
)
from quack_core.integrations.github.service import GitHubIntegration

# ------------------------------
# Environment & HTTP Client Fixtures
# ------------------------------


@pytest.fixture
def mock_environment_token() -> None:
    """Fixture to provide a mock GitHub token in the environment."""
    original = os.environ.get("GITHUB_TOKEN")
    os.environ["GITHUB_TOKEN"] = "mock-github-token"
    yield
    if original is None:
        del os.environ["GITHUB_TOKEN"]
    else:
        os.environ["GITHUB_TOKEN"] = original


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Create a mock HTTP client for testing."""
    mock_client = MagicMock(spec=requests)

    # Setup default successful response.
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.headers = {"X-RateLimit-Remaining": "100"}
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "login": "test_user",
        "html_url": "https://github.com/test_user",
        "name": "Test User",
        "email": "test@example.com",
        "avatar_url": "https://github.com/test_user.png",
    }

    mock_client.get.return_value = mock_response
    mock_client.post.return_value = mock_response
    mock_client.put.return_value = mock_response
    mock_client.delete.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_rate_limited_client() -> MagicMock:
    """Create a mock HTTP client that simulates rate limiting."""
    mock_client = MagicMock(spec=requests)

    # Create a rate-limited response.
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 429
    mock_response.headers = {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": str(int(time.time()) + 60),
    }

    # Have raise_for_status throw an HTTPError.
    http_error = requests.exceptions.HTTPError(response=mock_response)
    http_error.response = mock_response
    mock_response.raise_for_status.side_effect = http_error

    mock_client.get.return_value = mock_response
    mock_client.post.return_value = mock_response
    mock_client.put.return_value = mock_response
    mock_client.delete.return_value = mock_response

    return mock_client


# ------------------------------
# Registry Patching Fixtures
# ------------------------------


@pytest.fixture
def patch_integration_registry() -> MagicMock:
    """Patch the integration registry for testing."""
    mock_registry = MagicMock()
    mock_registry.integrations = []
    # Define both potential registration methods
    mock_registry.register = MagicMock()
    mock_registry.get_integration = MagicMock(return_value="mocked_github_integration")

    with patch("quack_core.integrations.core.registry", mock_registry):
        yield mock_registry


@pytest.fixture
def patch_registry_register() -> MagicMock:
    """Patch the registry register method."""
    # Create a mock registry that has the register method
    mock_registry = MagicMock()
    mock_registry.register = MagicMock()

    # Patch the entire registry module
    with patch("quack_core.integrations.core.registry", mock_registry):
        yield mock_registry.register


# ------------------------------
# Credentials and Configuration File Fixtures
# ------------------------------


@pytest.fixture
def github_credentials_file(tmp_path: Path) -> Path:
    """Create a temporary GitHub credentials file."""
    creds_file = tmp_path / "github_creds.json"
    creds_data = {
        "token": "test_token",
        "saved_at": 1611111111,
        "user_info": {
            "login": "test_user",
            "name": "Test User",
            "email": "test@example.com",
        },
    }

    creds_file.write_text(json.dumps(creds_data))
    return creds_file


@pytest.fixture
def github_config_file(tmp_path: Path) -> Path:
    """Create a temporary GitHub config file."""
    config_file = tmp_path / "github_config.json"
    config_data = {
        "github": {
            "token": "mock_token",
            "api_url": "https://api.github.com",
            "timeout_seconds": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
        }
    }

    config_file.write_text(json.dumps(config_data))
    return config_file


# ------------------------------
# Provider Fixtures
# ------------------------------


@pytest.fixture
def mock_github_auth_provider() -> AuthProviderProtocol:
    """Create a mock GitHub authentication provider."""
    # Use spec_set to enforce the interface.
    auth_provider = MagicMock(spec_set=GitHubAuthProvider)
    # Instead of assignment (which may fail for read-only properties), use configure_mock.
    auth_provider.configure_mock(name="GitHub")
    auth_provider.get_credentials.return_value = {"token": "test_token"}

    # Create a successful auth result.
    auth_result = MagicMock(spec=AuthResult)
    auth_result.success = True
    auth_result.token = "test_token"
    auth_result.message = "Successfully authenticated with GitHub"
    auth_result.error = None

    auth_provider.authenticate.return_value = auth_result
    return cast(AuthProviderProtocol, auth_provider)


@pytest.fixture
def mock_github_auth_provider_failure() -> AuthProviderProtocol:
    """Create a mock GitHub authentication provider that fails."""
    auth_provider = MagicMock(spec_set=GitHubAuthProvider)
    auth_provider.configure_mock(name="GitHub")
    auth_provider.get_credentials.return_value = {}

    # Create a failed auth result.
    auth_result = MagicMock(spec=AuthResult)
    auth_result.success = False
    auth_result.token = None
    auth_result.message = "Authentication failed"
    auth_result.error = "No GitHub token provided"

    auth_provider.authenticate.return_value = auth_result
    return cast(AuthProviderProtocol, auth_provider)


@pytest.fixture
def mock_github_config_provider() -> ConfigProviderProtocol:
    """Create a mock GitHub configuration provider."""
    config_provider = MagicMock(spec_set=GitHubConfigProvider)
    config_provider.configure_mock(name="GitHub")
    config_provider.get_default_config.return_value = {
        "token": "test_token",
        "api_url": "https://api.github.com",
        "timeout_seconds": 30,
        "max_retries": 3,
        "retry_delay": 1.0,
    }

    # Create a successful config result.
    config_result = MagicMock()
    config_result.success = True
    config_result.content = {
        "token": "test_token",
        "api_url": "https://api.github.com",
        "timeout_seconds": 30,
        "max_retries": 3,
        "retry_delay": 1.0,
    }
    config_result.error = None

    config_provider.load_config.return_value = config_result
    return cast(ConfigProviderProtocol, config_provider)


# ------------------------------
# Real Provider Fixtures
# ------------------------------


@pytest.fixture
def github_auth_provider(
    github_credentials_file: Path, mock_http_client: MagicMock
) -> GitHubAuthProvider:
    """Create a real GitHub authentication provider with a mock HTTP client."""
    return GitHubAuthProvider(
        credentials_file=str(github_credentials_file),
        http_client=mock_http_client,
    )


@pytest.fixture
def github_config_provider() -> GitHubConfigProvider:
    """Create a real GitHub configuration provider."""
    return GitHubConfigProvider()


# ------------------------------
# GitHub Client Fixture
# ------------------------------


@pytest.fixture
def mock_github_client() -> MagicMock:
    """Create a mock GitHub client."""
    client = MagicMock(spec=GitHubClient)

    # Set up common return values.
    user = GitHubUser(
        username="test_user",
        url="https://github.com/test_user",
        name="Test User",
        email="test@example.com",
        avatar_url="https://github.com/test_user.png",
    )

    owner = GitHubUser(
        username="test_owner",
        url="https://github.com/test_owner",
        name="Test Owner",
        avatar_url="https://github.com/test_owner.png",
    )

    repo = GitHubRepo(
        name="test-repo",
        full_name="test_owner/test-repo",
        url="https://github.com/test_owner/test-repo",
        clone_url="https://github.com/test_owner/test-repo.git",
        default_branch="main",
        description="Test repository",
        fork=False,
        forks_count=10,
        stargazers_count=100,
        owner=owner,
    )

    pr = PullRequest(
        number=123,
        title="Test PR",
        url="https://github.com/test_owner/test-repo/pull/123",
        author=user,
        status=PullRequestStatus.OPEN,
        body="Test PR body",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        base_repo="test_owner/test-repo",
        head_repo="test_user/test-repo",
        base_branch="main",
        head_branch="feature",
    )

    # Set up the client methods with the expected return values.
    client.get_user.return_value = user
    client.get_repo.return_value = repo
    client.star_repo.return_value = True
    client.unstar_repo.return_value = True
    client.is_repo_starred.return_value = True
    client.fork_repo.return_value = repo
    client.create_pull_request.return_value = pr
    client.list_pull_requests.return_value = [pr]
    client.get_pull_request.return_value = pr
    client.check_repository_exists.return_value = True
    client.get_repository_file_content.return_value = ("file content", "abc123")
    client.update_repository_file.return_value = True

    return client


# ------------------------------
# Integration Service Fixtures
# ------------------------------


@pytest.fixture
def github_service(
    mock_github_auth_provider: AuthProviderProtocol,
    mock_github_config_provider: ConfigProviderProtocol,
    mock_github_client: MagicMock,
) -> GitHubIntegration:
    """Create a GitHub integration service with mocked dependencies."""
    service = GitHubIntegration(
        auth_provider=mock_github_auth_provider,
        config_provider=mock_github_config_provider,
    )
    service.client = mock_github_client
    service._initialized = True
    service.config = {
        "token": "test_token",
        "api_url": "https://api.github.com",
        "timeout_seconds": 30,
        "max_retries": 3,
        "retry_delay": 1.0,
    }
    return service


@pytest.fixture
def github_service_uninitialized(
    mock_github_auth_provider: AuthProviderProtocol,
    mock_github_config_provider: ConfigProviderProtocol,
) -> GitHubIntegration:
    """Create an uninitialized GitHub integration service."""
    service = GitHubIntegration(
        auth_provider=mock_github_auth_provider,
        config_provider=mock_github_config_provider,
    )
    service._initialized = False
    service.config = None
    service.client = None
    return service


# ------------------------------
# Additional Request-Related Fixtures
# ------------------------------


@pytest.fixture
def mock_requests_session() -> MagicMock:
    """Create a mock requests session."""
    session = MagicMock(spec=requests.Session)
    session.headers = {}
    return session


@pytest.fixture
def mock_response() -> MagicMock:
    """Create a mock API response."""
    response = MagicMock(spec=requests.Response)
    response.raise_for_status.return_value = None
    response.status_code = 200
    response.headers = {"X-RateLimit-Remaining": "100"}
    return response


@pytest.fixture
def mock_rate_limited_response() -> MagicMock:
    """Create a mock API response with rate limit exceeded."""
    response = MagicMock(spec=requests.Response)
    response.status_code = 429
    response.headers = {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": str(int(time.time()) + 60),
    }
    http_error = requests.exceptions.HTTPError(response=response)
    http_error.response = response
    response.raise_for_status.side_effect = http_error
    return response


@pytest.fixture
def patch_requests_get():
    """Patch requests.get for testing."""
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "login": "test_user",
            "html_url": "https://github.com/test_user",
            "name": "Test User",
            "email": "test@example.com",
            "avatar_url": "https://github.com/test_user.png",
        }
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def patch_make_request():
    """Patch the make_request function for testing."""
    with patch(
        "quack_core.integrations.github.api.api.make_request"
    ) as mock_make_request:
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_make_request.return_value = mock_response
        yield mock_make_request


@pytest.fixture
def patch_make_request_rate_limited():
    """Patch the make_request function to simulate rate limiting."""
    with patch(
        "quack_core.integrations.github.api.api.make_request"
    ) as mock_make_request:
        mock_make_request.side_effect = QuackQuotaExceededError(
            message="GitHub API rate limit exceeded", service="GitHub", resource="/test"
        )
        yield mock_make_request
