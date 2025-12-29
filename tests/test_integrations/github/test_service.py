# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/github/test_service.py
# role: tests
# neighbors: __init__.py, conftest.py, test_api.py, test_auth.py, test_client.py, test_config.py (+5 more)
# exports: TestGitHubIntegration, mock_auth_provider, mock_config_provider, github_service
# git_branch: refactor/toolkitWorkflow
# git_commit: 07a259e
# === QV-LLM:END ===

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, create_autospec, patch

import pytest

from quack_core.integrations.core import (
    AuthProviderProtocol,
    AuthResult,
    ConfigProviderProtocol,
    IntegrationResult,
)
from quack_core.integrations.github.auth import GitHubAuthProvider
from quack_core.integrations.github.config import GitHubConfigProvider
from quack_core.integrations.github.models import GitHubRepo, GitHubUser, PullRequest
from quack_core.integrations.github.service import GitHubIntegration


@pytest.fixture
def mock_auth_provider():
    """Create a mock authentication provider."""
    auth_provider = cast(
        GitHubAuthProvider, create_autospec(GitHubAuthProvider, instance=True)
    )
    return auth_provider


@pytest.fixture
def mock_config_provider():
    """Create a mock configuration provider."""
    config_provider = cast(
        GitHubConfigProvider, create_autospec(GitHubConfigProvider, instance=True)
    )
    config_provider.get_default_config.return_value = {
        "token": "test_token",
        "api_url": "https://api.github.com",
        "timeout_seconds": 30,
        "max_retries": 3,
        "retry_delay": 1.0,
    }
    return config_provider


@pytest.fixture
def github_service(mock_auth_provider, mock_config_provider):
    """Create a GitHub integration service with mocked dependencies."""
    return GitHubIntegration(
        auth_provider=mock_auth_provider,
        config_provider=mock_config_provider,
    )


class TestGitHubIntegration:
    """Tests for GitHubIntegration."""

    def test_init_with_default_providers(self):
        """Test initialization with default providers."""
        service = GitHubIntegration()

        assert service.name == "GitHub"
        assert service.version == "1.0.0"
        # We no longer auto-create an auth_provider, but we do get a default config_provider
        assert service.auth_provider is None
        assert isinstance(service.config_provider, GitHubConfigProvider)
        assert service.client is None
        assert not service._initialized

    def test_initialize_success(
        self, github_service, mock_auth_provider, mock_config_provider
    ):
        """Test successful initialization."""
        # Mock configuration with token.
        mock_config_provider.load_config.return_value = MagicMock(
            success=True,
            content={"token": "test_token", "api_url": "https://api.github.com"},
        )
        github_service.config = {
            "token": "test_token",
            "api_url": "https://api.github.com",
            "timeout_seconds": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
        }
        github_service.auth_provider = mock_auth_provider

        # Mock auth provider to return token.
        mock_auth_provider.get_credentials.return_value = {"token": "test_token"}

        with patch(
            "quack_core.integrations.github.service.GitHubClient"
        ) as mock_client_class:
            result = github_service.initialize()

            assert result.success is True
            assert "GitHub integration initialized successfully" in result.message
            assert github_service._initialized is True

            cast(MagicMock, mock_client_class).assert_called_once_with(
                token="test_token",
                api_url="https://api.github.com",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

    def test_initialize_with_base_error(self, github_service):
        """Test initialization when base initialization fails."""
        with patch(
            "quack_core.integrations.core.BaseIntegrationService.initialize"
        ) as mock_base_init:
            mock_base_init.return_value = IntegrationResult.error_result(
                error="Base initialization failed",
                message="Base initialization failed",
            )

            result = github_service.initialize()

            assert result.success is False
            assert "Base initialization failed" in result.error
            assert github_service._initialized is False

    def test_initialize_no_config(self, github_service):
        """Test initialization with no configuration."""
        with patch(
            "quack_core.integrations.core.BaseIntegrationService.initialize"
        ) as mock_base_init:
            mock_base_init.return_value = IntegrationResult.success_result()
            github_service.config = None

            result = github_service.initialize()

            assert result.success is False
            assert "GitHub configuration is not available" in result.error
            assert github_service._initialized is False

    def test_initialize_with_auth_provider_credentials(
        self, github_service, mock_auth_provider
    ):
        """Test initialization using auth provider credentials."""
        with patch(
            "quack_core.integrations.core.BaseIntegrationService.initialize"
        ) as mock_base_init:
            mock_base_init.return_value = IntegrationResult.success_result()

            # Set config without token.
            github_service.config = {"api_url": "https://api.github.com"}
            github_service.auth_provider = mock_auth_provider

            # Mock auth provider to return token.
            mock_auth_provider.get_credentials.return_value = {"token": "auth_token"}

            with patch(
                "quack_core.integrations.github.service.GitHubClient"
            ) as mock_client_class:
                result = github_service.initialize()

                assert result.success is True
                assert github_service._initialized is True

                assert cast(MagicMock, mock_client_class).call_count == 1
                _, kwargs = mock_client_class.call_args
                assert kwargs.get("token") == "auth_token"

    def test_initialize_with_authenticate(self, github_service, mock_auth_provider):
        """Test initialization by authenticating."""
        with patch(
            "quack_core.integrations.core.BaseIntegrationService.initialize"
        ) as mock_base_init:
            mock_base_init.return_value = IntegrationResult.success_result()

            github_service.config = {"api_url": "https://api.github.com"}
            github_service.auth_provider = mock_auth_provider

            # Simulate that get_credentials returns no token.
            mock_auth_provider.get_credentials.return_value = {"token": None}
            mock_auth_provider.authenticate.return_value = AuthResult.success_result(
                token="auth_token", message="Successfully authenticated"
            )

            with patch(
                "quack_core.integrations.github.service.GitHubClient"
            ) as mock_client_class:
                result = github_service.initialize()

                assert result.success is True
                assert github_service._initialized is True

                assert cast(MagicMock, mock_auth_provider.authenticate).call_count == 1
                assert cast(MagicMock, mock_client_class).call_count == 1
                _, kwargs = mock_client_class.call_args
                assert kwargs.get("token") == "auth_token"

    def test_initialize_auth_failure(self, github_service, mock_auth_provider):
        """Test initialization with authentication failure."""
        with patch(
            "quack_core.integrations.core.BaseIntegrationService.initialize"
        ) as mock_base_init:
            mock_base_init.return_value = IntegrationResult.success_result()

            github_service.config = {"api_url": "https://api.github.com"}
            github_service.auth_provider = mock_auth_provider

            # Simulate auth provider returns no token and then fails to authenticate.
            mock_auth_provider.get_credentials.return_value = {"token": None}
            mock_auth_provider.authenticate.return_value = AuthResult.error_result(
                error="Authentication failed", message="Invalid token"
            )

            result = github_service.initialize()

            assert result.success is False
            assert "Failed to authenticate with GitHub" in result.error
            assert "Authentication failed" in result.message
            assert github_service._initialized is False

    def test_initialize_no_token_no_auth(self, github_service):
        """Test initialization with no token and no auth provider."""
        with patch(
            "quack_core.integrations.core.BaseIntegrationService.initialize"
        ) as mock_base_init:
            mock_base_init.return_value = IntegrationResult.success_result()

            github_service.config = {"api_url": "https://api.github.com"}
            github_service.auth_provider = None

            result = github_service.initialize()

            assert result.success is False
            assert (
                "GitHub token is not configured and no auth provider is available"
                in result.error
            )
            assert github_service._initialized is False

    def test_initialize_exception(self, github_service):
        """Test initialization with unexpected exception."""
        with patch(
            "quack_core.integrations.core.BaseIntegrationService.initialize"
        ) as mock_base_init:
            mock_base_init.return_value = IntegrationResult.success_result()

            with patch(
                "quack_core.integrations.github.service.GitHubClient"
            ) as mock_client_class:
                mock_client_class.side_effect = Exception("Unexpected error")

                github_service.config = {
                    "token": "test_token",
                    "api_url": "https://api.github.com",
                }
                github_service.auth_provider = github_service.auth_provider or MagicMock()
                github_service.auth_provider.get_credentials = MagicMock(
                    return_value={"token": "test_token"}
                )

                result = github_service.initialize()

                assert result.success is False
                assert "Unexpected error" in str(result.error)
                assert github_service._initialized is False

    def test_is_available(self, github_service):
        """Test is_available method."""
        github_service._initialized = False
        github_service.client = None
        assert not github_service.is_available()

        github_service._initialized = True
        github_service.client = None
        assert not github_service.is_available()

        github_service._initialized = True
        github_service.client = MagicMock()
        assert github_service.is_available()

    def test_get_current_user(self, github_service):
        """Test get_current_user method."""
        mock_client = MagicMock()
        github_service.client = mock_client
        github_service._initialized = True

        user = GitHubUser(
            username="test_user",
            url="https://github.com/test_user",
            name="Test User",
            email="test@example.com",
            avatar_url="https://github.com/test_user.png",
        )
        mock_client.get_user.return_value = user

        result = github_service.get_current_user()

        assert result.success is True
        assert result.content == user
        assert f"Successfully retrieved user {user.username}" in result.message
        # Cast the method to ensure the attribute is available.
        cast(MagicMock, mock_client.get_user).assert_called_once()

    def test_get_current_user_not_initialized(self, github_service):
        """Test get_current_user when not initialized."""
        github_service._initialized = False
        result = github_service.get_current_user()
        assert result.success is False
        assert "GitHub integration is not initialized" in result.message

    def test_get_current_user_exception(self, github_service):
        """Test get_current_user with exception."""
        mock_client = MagicMock()
        github_service.client = mock_client
        github_service._initialized = True
        mock_client.get_user.side_effect = Exception("API error")

        result = github_service.get_current_user()
        assert result.success is False
        assert "Failed to get user: API error" in result.error

    def test_get_repo(self, github_service):
        """Test get_repo method."""
        mock_client = MagicMock()
        github_service.client = mock_client
        github_service._initialized = True

        owner = GitHubUser(username="test_owner", url="https://github.com/test_owner")
        repo = GitHubRepo(
            name="test-repo",
            full_name="test_owner/test-repo",
            url="https://github.com/test_owner/test-repo",
            clone_url="https://github.com/test_owner/test-repo.git",
            owner=owner,
        )
        mock_client.get_repo.return_value = repo

        result = github_service.get_repo("test_owner/test-repo")
        assert result.success is True
        assert result.content == repo
        assert f"Successfully retrieved repository {repo.full_name}" in result.message
        cast(MagicMock, mock_client.get_repo).assert_called_once_with(
            "test_owner/test-repo"
        )

    def test_get_repo_not_initialized(self, github_service):
        """Test get_repo when not initialized."""
        github_service._initialized = False
        result = github_service.get_repo("test_owner/test-repo")
        assert result.success is False
        assert "GitHub integration is not initialized" in result.message

    def test_get_repo_exception(self, github_service):
        """Test get_repo with exception."""
        mock_client = MagicMock()
        github_service.client = mock_client
        github_service._initialized = True
        mock_client.get_repo.side_effect = Exception("API error")

        result = github_service.get_repo("test_owner/test-repo")
        assert result.success is False
        assert "Failed to get repository: API error" in result.error

    def test_star_repo(self, github_service):
        """Test star_repo method."""
        mock_client = MagicMock()
        github_service.client = mock_client
        github_service._initialized = True
        mock_client.star_repo.return_value = True

        result = github_service.star_repo("test_owner/test-repo")
        assert result.success is True
        assert result.content is True
        assert "Successfully starred repository test_owner/test-repo" in result.message
        cast(MagicMock, mock_client.star_repo).assert_called_once_with(
            "test_owner/test-repo"
        )

    def test_star_repo_not_initialized(self, github_service):
        """Test star_repo when not initialized."""
        github_service._initialized = False
        result = github_service.star_repo("test_owner/test-repo")
        assert result.success is False
        assert "GitHub integration is not initialized" in result.message

    def test_star_repo_exception(self, github_service):
        """Test star_repo with exception."""
        mock_client = MagicMock()
        github_service.client = mock_client
        github_service._initialized = True
        mock_client.star_repo.side_effect = Exception("API error")

        result = github_service.star_repo("test_owner/test-repo")
        assert result.success is False
        assert "Failed to star repository: API error" in result.error

    def test_fork_repo(self, github_service):
        """Test fork_repo method."""
        mock_client = MagicMock()
        github_service.client = mock_client
        github_service._initialized = True

        owner = GitHubUser(username="test_user", url="https://github.com/test_user")
        forked_repo = GitHubRepo(
            name="test-repo",
            full_name="test_user/test-repo",
            url="https://github.com/test_user/test-repo",
            clone_url="https://github.com/test_user/test-repo.git",
            fork=True,
            owner=owner,
        )
        mock_client.fork_repo.return_value = forked_repo

        result = github_service.fork_repo("test_owner/test-repo")
        assert result.success is True
        assert result.content == forked_repo
        assert (
            f"Successfully forked repository test_owner/test-repo to {forked_repo.full_name}"
            in result.message
        )
        cast(MagicMock, mock_client.fork_repo).assert_called_once_with(
            "test_owner/test-repo"
        )

    def test_fork_repo_not_initialized(self, github_service):
        """Test fork_repo when not initialized."""
        github_service._initialized = False
        result = github_service.fork_repo("test_owner/test-repo")
        assert result.success is False
        assert "GitHub integration is not initialized" in result.message

    def test_fork_repo_exception(self, github_service):
        """Test fork_repo with exception."""
        mock_client = MagicMock()
        github_service.client = mock_client
        github_service._initialized = True
        mock_client.fork_repo.side_effect = Exception("API error")

        result = github_service.fork_repo("test_owner/test-repo")
        assert result.success is False
        assert "Failed to fork repository: API error" in result.error

    def test_create_pull_request(self, github_service):
        """Test create_pull_request method."""
        mock_client = MagicMock()
        github_service.client = mock_client
        github_service._initialized = True

        author = GitHubUser(username="test_user", url="https://github.com/test_user")
        pr = PullRequest(
            number=123,
            title="Test PR",
            url="https://github.com/test_owner/test-repo/pull/123",
            author=author,
            status="open",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            base_repo="test_owner/test-repo",
            head_repo="test_user/test-repo",
            base_branch="main",
            head_branch="feature",
        )
        mock_client.create_pull_request.return_value = pr

        result = github_service.create_pull_request(
            base_repo="test_owner/test-repo",
            head="test_user:feature",
            title="Test PR",
            body="Test body",
            base_branch="main",
        )
        assert result.success is True
        assert result.content == pr
        assert "Successfully created pull request" in result.message
        cast(MagicMock, mock_client.create_pull_request).assert_called_once_with(
            base_repo="test_owner/test-repo",
            head="test_user:feature",
            title="Test PR",
            body="Test body",
            base_branch="main",
        )

    def test_create_pull_request_not_initialized(self, github_service):
        """Test create_pull_request when not initialized."""
        github_service._initialized = False
        result = github_service.create_pull_request(
            base_repo="test_owner/test-repo", head="test_user:feature", title="Test PR"
        )
        assert result.success is False
        assert "GitHub integration is not initialized" in result.message

    def test_create_pull_request_exception(self, github_service):
        """Test create_pull_request with exception."""
        mock_client = MagicMock()
        github_service.client = mock_client
        github_service._initialized = True
        mock_client.create_pull_request.side_effect = Exception("API error")

        result = github_service.create_pull_request(
            base_repo="test_owner/test-repo", head="test_user:feature", title="Test PR"
        )
        assert result.success is False
        assert "Failed to create pull request: API error" in result.error

    def test_list_pull_requests(self, github_service):
        """Test list_pull_requests method."""
        mock_client = MagicMock()
        github_service.client = mock_client
        github_service._initialized = True

        author = GitHubUser(username="test_user", url="https://github.com/test_user")
        pr1 = PullRequest(
            number=123,
            title="Test PR 1",
            url="https://github.com/test_owner/test-repo/pull/123",
            author=author,
            status="open",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            base_repo="test_owner/test-repo",
            head_repo="test_user/test-repo",
            base_branch="main",
            head_branch="feature1",
        )
        pr2 = PullRequest(
            number=124,
            title="Test PR 2",
            url="https://github.com/test_owner/test-repo/pull/124",
            author=author,
            status="open",
            created_at="2023-01-02T00:00:00Z",
            updated_at="2023-01-02T00:00:00Z",
            base_repo="test_owner/test-repo",
            head_repo="test_user/test-repo",
            base_branch="main",
            head_branch="feature2",
        )
        mock_client.list_pull_requests.return_value = [pr1, pr2]

        result = github_service.list_pull_requests(
            repo="test_owner/test-repo", state="open", author="test_user"
        )
        assert result.success is True
        assert len(result.content) == 2
        assert result.content[0] == pr1
        assert result.content[1] == pr2
        assert (
            "Successfully retrieved 2 pull requests for test_owner/test-repo"
            in result.message
        )
        cast(MagicMock, mock_client.list_pull_requests).assert_called_once_with(
            repo="test_owner/test-repo", state="open", author="test_user"
        )

    def test_list_pull_requests_not_initialized(self, github_service):
        """Test list_pull_requests when not initialized."""
        github_service._initialized = False
        result = github_service.list_pull_requests(repo="test_owner/test-repo")
        assert result.success is False
        assert "GitHub integration is not initialized" in result.message

    def test_list_pull_requests_exception(self, github_service):
        """Test list_pull_requests with exception."""
        mock_client = MagicMock()
        github_service.client = mock_client
        github_service._initialized = True
        mock_client.list_pull_requests.side_effect = Exception("API error")

        result = github_service.list_pull_requests(repo="test_owner/test-repo")
        assert result.success is False
        assert "Failed to list pull requests: API error" in result.error

    def test_get_pull_request(self, github_service):
        """Test get_pull_request method."""
        mock_client = MagicMock()
        github_service.client = mock_client
        github_service._initialized = True

        author = GitHubUser(username="test_user", url="https://github.com/test_user")
        pr = PullRequest(
            number=123,
            title="Test PR",
            url="https://github.com/test_owner/test-repo/pull/123",
            author=author,
            status="open",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            base_repo="test_owner/test-repo",
            head_repo="test_user/test-repo",
            base_branch="main",
            head_branch="feature",
        )
        mock_client.get_pull_request.return_value = pr

        result = github_service.get_pull_request(
            repo="test_owner/test-repo", number=123
        )
        assert result.success is True
        assert result.content == pr
        assert (
            "Successfully retrieved pull request #123 from test_owner/test-repo"
            in result.message
        )
        cast(MagicMock, mock_client.get_pull_request).assert_called_once_with(
            "test_owner/test-repo", 123
        )

    def test_get_pull_request_not_initialized(self, github_service):
        """Test get_pull_request when not initialized."""
        github_service._initialized = False
        result = github_service.get_pull_request(
            repo="test_owner/test-repo", number=123
        )
        assert result.success is False
        assert "GitHub integration is not initialized" in result.message

    def test_get_pull_request_exception(self, github_service):
        """Test get_pull_request with exception."""
        mock_client = MagicMock()
        github_service.client = mock_client
        github_service._initialized = True
        mock_client.get_pull_request.side_effect = Exception("API error")

        result = github_service.get_pull_request(
            repo="test_owner/test-repo", number=123
        )
        assert result.success is False
        assert "Failed to get pull request: API error" in result.error

    @staticmethod
    def setup_mock_auth_provider(auth_success=True):
        """Set up a mock auth provider for tests."""
        from quack_core.integrations.github.auth import GitHubAuthProvider

        mock_auth = MagicMock(spec=GitHubAuthProvider)
        auth_result = MagicMock()
        auth_result.success = auth_success
        auth_result.token = "mock_token" if auth_success else None
        auth_result.error = None if auth_success else "Authentication failed"
        mock_auth.authenticate.return_value = auth_result
        mock_auth.get_credentials.return_value = (
            {"token": "mock_token"} if auth_success else {}
        )
        return mock_auth

    @staticmethod
    def setup_mock_config_provider(with_token=True):
        """Set up a mock config provider for tests."""
        from quack_core.integrations.github.config import GitHubConfigProvider

        mock_config = MagicMock(spec=GitHubConfigProvider)
        config_result = MagicMock()
        config_result.success = True
        config_result.content = {
            "token": "mock_token" if with_token else "",
            "api_url": "https://api.github.com",
            "timeout_seconds": 30,
            "max_retries": 3,
        }
        mock_config.load_config.return_value = config_result
        # Inject a dynamic 'get_config' method.
        mock_config.get_config = MagicMock(return_value=config_result.content)
        return mock_config

    def test_initialize_handles_exceptions(self):
        """Test that initialize properly handles exceptions."""
        mock_auth = MagicMock()
        mock_auth.authenticate.side_effect = Exception("Unexpected auth error")

        mock_config = MagicMock()
        mock_config.load_config.return_value = MagicMock(
            success=True, content={"token": "test_token", "api_url": "https://api.github.com"}
        )
        mock_config.get_config = MagicMock(return_value={"token": "test_token", "api_url": "https://api.github.com"})

        service = GitHubIntegration()
        service.auth_provider = cast(AuthProviderProtocol, mock_auth)
        service.config_provider = cast(ConfigProviderProtocol, mock_config)

        with patch(
            "quack_core.integrations.core.BaseIntegrationService.initialize"
        ) as mock_base_init:
            mock_base_init.return_value = IntegrationResult.success_result()

            service.config = {
                "token": "test_token",
                "api_url": "https://api.github.com",
            }
            service._initialized = False

            result = service.initialize()

            assert result.success is False
            assert "Failed to initialize GitHub integration" in result.error
            assert "Unexpected auth error" in result.error
            assert service._initialized is False
