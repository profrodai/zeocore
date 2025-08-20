# quack-core/tests/test_integrations/github/test_protocols.py
"""Tests for GitHub integration protocols."""

from unittest.mock import MagicMock

from quackcore.integrations.core import IntegrationProtocol, IntegrationResult
from quackcore.integrations.github.models import GitHubRepo, GitHubUser, PullRequest
from quackcore.integrations.github.protocols import GitHubIntegrationProtocol
from quackcore.integrations.github.service import GitHubIntegration


class TestGitHubProtocols:
    """Tests for GitHub protocols."""

    def test_github_integration_protocol(self):
        """Test that GitHubIntegration implements the GitHubIntegrationProtocol."""
        # Create a GitHub integration instance.
        integration = GitHubIntegration()

        # Check that it implements the protocol.
        assert isinstance(integration, GitHubIntegrationProtocol)
        assert isinstance(integration, IntegrationProtocol)

        # Verify protocol methods exist.
        for method in (
            "get_current_user",
            "get_repo",
            "star_repo",
            "fork_repo",
            "create_pull_request",
            "list_pull_requests",
            "get_pull_request",
        ):
            assert hasattr(integration, method)

    def test_github_integration_protocol_method_signatures(self):
        """Test that GitHubIntegration methods have correct return type hints."""
        # Reference the unbound methods from the class so that __annotations__ are available.
        assert (
            GitHubIntegration.get_current_user.__annotations__["return"]
            == IntegrationResult[GitHubUser]
        )
        assert (
            GitHubIntegration.get_repo.__annotations__["return"]
            == IntegrationResult[GitHubRepo]
        )
        assert (
            GitHubIntegration.star_repo.__annotations__["return"]
            == IntegrationResult[bool]
        )
        assert (
            GitHubIntegration.fork_repo.__annotations__["return"]
            == IntegrationResult[GitHubRepo]
        )
        assert (
            GitHubIntegration.create_pull_request.__annotations__["return"]
            == IntegrationResult[PullRequest]
        )
        assert (
            GitHubIntegration.list_pull_requests.__annotations__["return"]
            == IntegrationResult[list[PullRequest]]
        )
        assert (
            GitHubIntegration.get_pull_request.__annotations__["return"]
            == IntegrationResult[PullRequest]
        )

    def test_protocol_runtime_checkable(self):
        """Test that GitHubIntegrationProtocol is runtime checkable."""
        # Create a mock object that implements the protocol methods.
        mock_impl = MagicMock(spec=GitHubIntegrationProtocol)

        # It should be considered an instance of the protocol.
        assert isinstance(mock_impl, GitHubIntegrationProtocol)

        # Create a mock that doesn't implement all methods.
        incomplete_mock = MagicMock()
        incomplete_mock.name = "GitHub"
        incomplete_mock.get_current_user = lambda: None

        # It should not be considered an instance of the protocol.
        assert not isinstance(incomplete_mock, GitHubIntegrationProtocol)
