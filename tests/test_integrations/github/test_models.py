# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/github/test_models.py
# role: tests
# neighbors: __init__.py, conftest.py, test_api.py, test_auth.py, test_client.py, test_config.py (+5 more)
# exports: TestGitHubModels
# git_branch: refactor/toolkitWorkflow
# git_commit: 234aec0
# === QV-LLM:END ===

"""Tests for GitHub models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from quack_core.integrations.github.models import (
    GitHubRepo,
    GitHubUser,
    PullRequest,
    PullRequestStatus,
)


class TestGitHubModels:
    """Tests for GitHub models."""

    def test_pull_request_status_enum(self):
        """Test PullRequestStatus enum."""
        assert PullRequestStatus.OPEN == "open"
        assert PullRequestStatus.CLOSED == "closed"
        assert PullRequestStatus.MERGED == "merged"

        # Test enum values
        assert list(PullRequestStatus) == [
            PullRequestStatus.OPEN,
            PullRequestStatus.CLOSED,
            PullRequestStatus.MERGED,
        ]

    def test_github_user_model(self):
        """Test GitHubUser model."""
        # Test valid model
        user = GitHubUser(
            username="test-user",
            url="https://github.com/test-user",
            name="Test User",
            email="test@example.com",
            avatar_url="https://github.com/test-user.png",
        )

        assert user.username == "test-user"
        assert str(user.url) == "https://github.com/test-user"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert str(user.avatar_url) == "https://github.com/test-user.png"

        # Test with minimal required fields
        user = GitHubUser(username="test-user", url="https://github.com/test-user")

        assert user.username == "test-user"
        assert str(user.url) == "https://github.com/test-user"
        assert user.name is None
        assert user.email is None
        assert user.avatar_url is None

        # Test with invalid URL
        with pytest.raises(ValidationError):
            GitHubUser(username="test-user", url="invalid-url")

    def test_github_repo_model(self):
        """Test GitHubRepo model."""
        # Create owner
        owner = GitHubUser(username="test-owner", url="https://github.com/test-owner")

        # Test valid model
        repo = GitHubRepo(
            name="test-repo",
            full_name="test-owner/test-repo",
            url="https://github.com/test-owner/test-repo",
            clone_url="https://github.com/test-owner/test-repo.git",
            default_branch="main",
            description="Test repository",
            fork=False,
            forks_count=10,
            stargazers_count=100,
            owner=owner,
        )

        assert repo.name == "test-repo"
        assert repo.full_name == "test-owner/test-repo"
        assert str(repo.url) == "https://github.com/test-owner/test-repo"
        assert str(repo.clone_url) == "https://github.com/test-owner/test-repo.git"
        assert repo.default_branch == "main"
        assert repo.description == "Test repository"
        assert repo.fork is False
        assert repo.forks_count == 10
        assert repo.stargazers_count == 100
        assert repo.owner == owner

        # Test with minimal required fields
        repo = GitHubRepo(
            name="test-repo",
            full_name="test-owner/test-repo",
            url="https://github.com/test-owner/test-repo",
            clone_url="https://github.com/test-owner/test-repo.git",
            owner=owner,
        )

        assert repo.name == "test-repo"
        assert repo.full_name == "test-owner/test-repo"
        assert str(repo.url) == "https://github.com/test-owner/test-repo"
        assert str(repo.clone_url) == "https://github.com/test-owner/test-repo.git"
        assert repo.default_branch == "main"  # Default value
        assert repo.description is None
        assert repo.fork is False  # Default value
        assert repo.forks_count == 0  # Default value
        assert repo.stargazers_count == 0  # Default value
        assert repo.owner == owner

        # Test with invalid URL
        with pytest.raises(ValidationError):
            GitHubRepo(
                name="test-repo",
                full_name="test-owner/test-repo",
                url="invalid-url",
                clone_url="https://github.com/test-owner/test-repo.git",
                owner=owner,
            )

    def test_pull_request_model(self):
        """Test PullRequest model."""
        # Create author
        author = GitHubUser(username="test-user", url="https://github.com/test-user")

        # Test valid model
        created_at = datetime.now()
        updated_at = datetime.now()
        merged_at = datetime.now()

        pr = PullRequest(
            number=123,
            title="Test PR",
            url="https://github.com/test-owner/test-repo/pull/123",
            author=author,
            status=PullRequestStatus.OPEN,
            body="This is a test PR",
            created_at=created_at,
            updated_at=updated_at,
            merged_at=merged_at,
            base_repo="test-owner/test-repo",
            head_repo="test-user/test-repo",
            base_branch="main",
            head_branch="feature",
        )

        assert pr.number == 123
        assert pr.title == "Test PR"
        assert str(pr.url) == "https://github.com/test-owner/test-repo/pull/123"
        assert pr.author == author
        assert pr.status == PullRequestStatus.OPEN
        assert pr.body == "This is a test PR"
        assert pr.created_at == created_at
        assert pr.updated_at == updated_at
        assert pr.merged_at == merged_at
        assert pr.base_repo == "test-owner/test-repo"
        assert pr.head_repo == "test-user/test-repo"
        assert pr.base_branch == "main"
        assert pr.head_branch == "feature"

        # Test with minimal required fields
        pr = PullRequest(
            number=123,
            title="Test PR",
            url="https://github.com/test-owner/test-repo/pull/123",
            author=author,
            status=PullRequestStatus.OPEN,
            created_at=created_at,
            updated_at=updated_at,
            base_repo="test-owner/test-repo",
            head_repo="test-user/test-repo",
            base_branch="main",
            head_branch="feature",
        )

        assert pr.number == 123
        assert pr.title == "Test PR"
        assert str(pr.url) == "https://github.com/test-owner/test-repo/pull/123"
        assert pr.author == author
        assert pr.status == PullRequestStatus.OPEN
        assert pr.body is None
        assert pr.created_at == created_at
        assert pr.updated_at == updated_at
        assert pr.merged_at is None
        assert pr.base_repo == "test-owner/test-repo"
        assert pr.head_repo == "test-user/test-repo"
        assert pr.base_branch == "main"
        assert pr.head_branch == "feature"

        # Test with invalid URL
        with pytest.raises(ValidationError):
            PullRequest(
                number=123,
                title="Test PR",
                url="invalid-url",
                author=author,
                status=PullRequestStatus.OPEN,
                created_at=created_at,
                updated_at=updated_at,
                base_repo="test-owner/test-repo",
                head_repo="test-user/test-repo",
                base_branch="main",
                head_branch="feature",
            )

    def test_url_string_equality(self):
        """Test that URL objects and strings can be correctly compared."""
        from datetime import datetime

        from quack_core.integrations.github.models import (
            GitHubRepo,
            GitHubUser,
            PullRequest,
            PullRequestStatus,
        )

        # Test GitHubUser URL equality
        user = GitHubUser(
            username="test-user",
            url="https://github.com/test-user",
            name="Test User",
            email="test@example.com",
            avatar_url="https://github.com/test-user.png",
        )
        assert str(user.url) == "https://github.com/test-user"

        # Test GitHubRepo URL equality
        owner = GitHubUser(username="test-owner", url="https://github.com/test-owner")
        repo = GitHubRepo(
            name="test-repo",
            full_name="test-owner/test-repo",
            url="https://github.com/test-owner/test-repo",
            clone_url="https://github.com/test-owner/test-repo.git",
            default_branch="main",
            description="Test repository",
            owner=owner,
        )
        assert str(repo.url) == "https://github.com/test-owner/test-repo"

        # Test PullRequest URL equality
        now = datetime.now()
        pr = PullRequest(
            number=123,
            title="Test PR",
            url="https://github.com/test-owner/test-repo/pull/123",
            author=user,
            status=PullRequestStatus.OPEN,
            body="Test PR body",
            created_at=now,
            updated_at=now,
            base_repo="test-owner/test-repo",
            head_repo="test-user/test-repo",
            base_branch="main",
            head_branch="feature",
        )
        assert str(pr.url) == "https://github.com/test-owner/test-repo/pull/123"
