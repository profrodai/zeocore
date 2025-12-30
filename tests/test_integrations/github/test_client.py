# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/github/test_client.py
# role: tests
# neighbors: __init__.py, conftest.py, test_api.py, test_auth.py, test_config.py, test_github_init.py (+5 more)
# exports: TestGitHubClient, github_client
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===

"""Tests for GitHub client."""

from unittest.mock import patch

import pytest
from quack_core.integrations.github.client import GitHubClient
from quack_core.integrations.github.models import GitHubRepo, GitHubUser, PullRequest


@pytest.fixture
def github_client():
    """Create a GitHub client for testing."""
    return GitHubClient(
        token="test_token",
        api_url="https://api.github.com",
        timeout=30,
        max_retries=3,
        retry_delay=1.0,
    )


class TestGitHubClient:
    """Tests for GitHubClient."""

    def test_init(self, github_client):
        """Test client initialization."""
        assert github_client.token == "test_token"
        assert github_client.api_url == "https://api.github.com"
        assert github_client.timeout == 30
        assert github_client.max_retries == 3
        assert github_client.retry_delay == 1.0
        assert github_client._current_user is None

        # Check session headers
        expected_headers = {
            "Authorization": "token test_token",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "QuackCore-GitHub-Integration",
        }
        for key, value in expected_headers.items():
            assert github_client.session.headers.get(key) == value

    def test_get_user_authenticated(self, github_client):
        """Test getting authenticated user."""
        # Mock get_user operation
        with patch("quack_core.integrations.github.client.get_user") as mock_get_user:
            user = GitHubUser(
                username="test_user",
                url="https://github.com/test_user",
                name="Test User",
                email="test@example.com",
                avatar_url="https://github.com/test_user.png",
            )
            mock_get_user.return_value = user

            # Call the method
            result = github_client.get_user()

            # Verify result
            assert result == user
            mock_get_user.assert_called_once_with(
                session=github_client.session,
                api_url="https://api.github.com",
                username=None,
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

            # Verify user is cached
            assert github_client._current_user == user

            # Call again to test caching
            mock_get_user.reset_mock()
            result = github_client.get_user()
            assert result == user
            mock_get_user.assert_not_called()

    def test_get_user_specific(self, github_client):
        """Test getting a specific user."""
        # Mock get_user operation
        with patch("quack_core.integrations.github.client.get_user") as mock_get_user:
            user = GitHubUser(
                username="other_user",
                url="https://github.com/other_user",
                name="Other User",
                email="other@example.com",
                avatar_url="https://github.com/other_user.png",
            )
            mock_get_user.return_value = user

            # Call the method
            result = github_client.get_user(username="other_user")

            # Verify result
            assert result == user
            mock_get_user.assert_called_once_with(
                session=github_client.session,
                api_url="https://api.github.com",
                username="other_user",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

            # Verify user is not cached
            assert github_client._current_user != user

    def test_get_repo(self, github_client):
        """Test getting a repository."""
        # Mock get_repo operation
        with patch("quack_core.integrations.github.client.get_repo") as mock_get_repo:
            owner = GitHubUser(
                username="test_owner", url="https://github.com/test_owner"
            )
            repo = GitHubRepo(
                name="test-repo",
                full_name="test_owner/test-repo",
                url="https://github.com/test_owner/test-repo",
                clone_url="https://github.com/test_owner/test-repo.git",
                owner=owner,
            )
            mock_get_repo.return_value = repo

            # Call the method
            result = github_client.get_repo("test_owner/test-repo")

            # Verify result
            assert result == repo
            mock_get_repo.assert_called_once_with(
                session=github_client.session,
                full_name="test_owner/test-repo",
                api_url="https://api.github.com",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

    def test_star_repo(self, github_client):
        """Test starring a repository."""
        # Mock star_repo operation
        with patch("quack_core.integrations.github.client.star_repo") as mock_star_repo:
            mock_star_repo.return_value = True

            # Call the method
            result = github_client.star_repo("test_owner/test-repo")

            # Verify result
            assert result is True
            mock_star_repo.assert_called_once_with(
                session=github_client.session,
                full_name="test_owner/test-repo",
                api_url="https://api.github.com",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

    def test_unstar_repo(self, github_client):
        """Test unstarring a repository."""
        # Mock unstar_repo operation
        with patch(
            "quack_core.integrations.github.client.unstar_repo"
        ) as mock_unstar_repo:
            mock_unstar_repo.return_value = True

            # Call the method
            result = github_client.unstar_repo("test_owner/test-repo")

            # Verify result
            assert result is True
            mock_unstar_repo.assert_called_once_with(
                session=github_client.session,
                full_name="test_owner/test-repo",
                api_url="https://api.github.com",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

    def test_is_repo_starred(self, github_client):
        """Test checking if a repository is starred."""
        # Mock is_repo_starred operation
        with patch(
            "quack_core.integrations.github.client.is_repo_starred"
        ) as mock_is_starred:
            mock_is_starred.return_value = True

            # Call the method
            result = github_client.is_repo_starred("test_owner/test-repo")

            # Verify result
            assert result is True
            mock_is_starred.assert_called_once_with(
                session=github_client.session,
                full_name="test_owner/test-repo",
                api_url="https://api.github.com",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

    def test_fork_repo(self, github_client):
        """Test forking a repository."""
        # Mock fork_repo operation
        with patch("quack_core.integrations.github.client.fork_repo") as mock_fork_repo:
            owner = GitHubUser(username="test_user", url="https://github.com/test_user")
            repo = GitHubRepo(
                name="test-repo",
                full_name="test_user/test-repo",
                url="https://github.com/test_user/test-repo",
                clone_url="https://github.com/test_user/test-repo.git",
                fork=True,
                owner=owner,
            )
            mock_fork_repo.return_value = repo

            # Call the method
            result = github_client.fork_repo(
                "test_owner/test-repo", organization="test-org"
            )

            # Verify result
            assert result == repo
            mock_fork_repo.assert_called_once_with(
                session=github_client.session,
                full_name="test_owner/test-repo",
                api_url="https://api.github.com",
                organization="test-org",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

    def test_create_pull_request(self, github_client):
        """Test creating a pull request."""
        # Mock create_pull_request operation
        with patch(
            "quack_core.integrations.github.client.create_pull_request"
        ) as mock_create_pr:
            author = GitHubUser(
                username="test_user", url="https://github.com/test_user"
            )
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
            mock_create_pr.return_value = pr

            # Call the method
            result = github_client.create_pull_request(
                base_repo="test_owner/test-repo",
                head="test_user:feature",
                title="Test PR",
                body="Test body",
                base_branch="main",
            )

            # Verify result
            assert result == pr
            mock_create_pr.assert_called_once_with(
                session=github_client.session,
                base_repo="test_owner/test-repo",
                head="test_user:feature",
                title="Test PR",
                api_url="https://api.github.com",
                body="Test body",
                base_branch="main",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

    def test_list_pull_requests(self, github_client):
        """Test listing pull requests."""
        # Mock list_pull_requests operation
        with patch(
            "quack_core.integrations.github.client.list_pull_requests"
        ) as mock_list_prs:
            author = GitHubUser(
                username="test_user", url="https://github.com/test_user"
            )
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
            mock_list_prs.return_value = [pr1, pr2]

            # Call the method
            result = github_client.list_pull_requests(
                repo="test_owner/test-repo", state="open", author="test_user"
            )

            # Verify result
            assert len(result) == 2
            assert result[0] == pr1
            assert result[1] == pr2
            mock_list_prs.assert_called_once_with(
                session=github_client.session,
                repo="test_owner/test-repo",
                api_url="https://api.github.com",
                state="open",
                author="test_user",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

    def test_get_pull_request(self, github_client):
        """Test getting a pull request."""
        # Mock get_pull_request operation
        with patch(
            "quack_core.integrations.github.client.get_pull_request"
        ) as mock_get_pr:
            author = GitHubUser(
                username="test_user", url="https://github.com/test_user"
            )
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
            mock_get_pr.return_value = pr

            # Call the method
            result = github_client.get_pull_request(
                repo="test_owner/test-repo", number=123
            )

            # Verify result
            assert result == pr
            mock_get_pr.assert_called_once_with(
                session=github_client.session,
                repo="test_owner/test-repo",
                number=123,
                api_url="https://api.github.com",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

    def test_check_repository_exists(self, github_client):
        """Test checking if a repository exists."""
        # Mock check_repository_exists operation
        with patch(
            "quack_core.integrations.github.client.check_repository_exists"
        ) as mock_check:
            mock_check.return_value = True

            # Call the method
            result = github_client.check_repository_exists("test_owner/test-repo")

            # Verify result
            assert result is True
            mock_check.assert_called_once_with(
                session=github_client.session,
                full_name="test_owner/test-repo",
                api_url="https://api.github.com",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

    def test_get_repository_file_content(self, github_client):
        """Test getting repository file content."""
        # Mock get_repository_file_content operation
        with patch(
            "quack_core.integrations.github.client.get_repository_file_content"
        ) as mock_get_content:
            mock_get_content.return_value = ("file content", "abc123")

            # Call the method
            content, sha = github_client.get_repository_file_content(
                repo="test_owner/test-repo", path="GET-STARTED.md", ref="main"
            )

            # Verify result
            assert content == "file content"
            assert sha == "abc123"
            mock_get_content.assert_called_once_with(
                session=github_client.session,
                repo="test_owner/test-repo",
                path="GET-STARTED.md",
                api_url="https://api.github.com",
                ref="main",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

    def test_update_repository_file(self, github_client):
        """Test updating repository file."""
        # Mock update_repository_file operation
        with patch(
            "quack_core.integrations.github.client.update_repository_file"
        ) as mock_update:
            mock_update.return_value = True

            # Call the method
            result = github_client.update_repository_file(
                repo="test_owner/test-repo",
                path="GET-STARTED.md",
                content="Updated content",
                message="Update README",
                sha="abc123",
                branch="main",
            )

            # Verify result
            assert result is True
            mock_update.assert_called_once_with(
                session=github_client.session,
                repo="test_owner/test-repo",
                path="GET-STARTED.md",
                content="Updated content",
                message="Update README",
                sha="abc123",
                api_url="https://api.github.com",
                branch="main",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

    def test_create_issue(self, github_client):
        """Test creating an issue."""
        # Mock create_issue operation
        with patch("quack_core.integrations.github.client.create_issue") as mock_create:
            mock_create.return_value = {"number": 42, "title": "Test Issue"}

            # Call the method
            result = github_client.create_issue(
                repo="test_owner/test-repo",
                title="Test Issue",
                body="Issue description",
                labels=["bug", "help wanted"],
                assignees=["test_user"],
            )

            # Verify result
            assert result == {"number": 42, "title": "Test Issue"}
            mock_create.assert_called_once_with(
                session=github_client.session,
                repo="test_owner/test-repo",
                title="Test Issue",
                api_url="https://api.github.com",
                body="Issue description",
                labels=["bug", "help wanted"],
                assignees=["test_user"],
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

    def test_list_issues(self, github_client):
        """Test listing issues."""
        # Mock list_issues operation
        with patch("quack_core.integrations.github.client.list_issues") as mock_list:
            mock_list.return_value = [
                {"number": 42, "title": "Test Issue 1"},
                {"number": 43, "title": "Test Issue 2"},
            ]

            # Call the method
            result = github_client.list_issues(
                repo="test_owner/test-repo",
                state="open",
                labels="bug",
                sort="created",
                direction="desc",
            )

            # Verify result
            assert len(result) == 2
            assert result[0]["number"] == 42
            assert result[1]["number"] == 43
            mock_list.assert_called_once_with(
                session=github_client.session,
                repo="test_owner/test-repo",
                api_url="https://api.github.com",
                state="open",
                labels="bug",
                sort="created",
                direction="desc",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

    def test_get_issue(self, github_client):
        """Test getting an issue."""
        # Mock get_issue operation
        with patch("quack_core.integrations.github.client.get_issue") as mock_get:
            mock_get.return_value = {"number": 42, "title": "Test Issue"}

            # Call the method
            result = github_client.get_issue(
                repo="test_owner/test-repo", issue_number=42
            )

            # Verify result
            assert result == {"number": 42, "title": "Test Issue"}
            mock_get.assert_called_once_with(
                session=github_client.session,
                repo="test_owner/test-repo",
                issue_number=42,
                api_url="https://api.github.com",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

    def test_add_issue_comment(self, github_client):
        """Test adding a comment to an issue."""
        # Mock add_issue_comment operation
        with patch(
            "quack_core.integrations.github.client.add_issue_comment"
        ) as mock_add:
            mock_add.return_value = {"id": 123, "body": "Test comment"}

            # Call the method
            result = github_client.add_issue_comment(
                repo="test_owner/test-repo", issue_number=42, body="Test comment"
            )

            # Verify result
            assert result == {"id": 123, "body": "Test comment"}
            mock_add.assert_called_once_with(
                session=github_client.session,
                repo="test_owner/test-repo",
                issue_number=42,
                body="Test comment",
                api_url="https://api.github.com",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )

    def test_get_pull_request_files(self, github_client):
        """Test getting files from a pull request."""
        # Mock get_pull_request_files operation
        with patch(
            "quack_core.integrations.github.client.get_pull_request_files"
        ) as mock_get:
            mock_get.return_value = [
                {
                    "filename": "GET-STARTED.md",
                    "status": "modified",
                    "additions": 10,
                    "deletions": 2,
                },
                {
                    "filename": "src/main.py",
                    "status": "added",
                    "additions": 50,
                    "deletions": 0,
                },
            ]

            # Call the method
            result = github_client.get_pull_request_files(
                repo="test_owner/test-repo", pull_number=123
            )

            # Verify result
            assert len(result) == 2
            assert result[0]["filename"] == "GET-STARTED.md"
            assert result[1]["filename"] == "src/main.py"
            mock_get.assert_called_once_with(
                session=github_client.session,
                repo="test_owner/test-repo",
                pull_number=123,
                api_url="https://api.github.com",
                timeout=30,
                max_retries=3,
                retry_delay=1.0,
            )
