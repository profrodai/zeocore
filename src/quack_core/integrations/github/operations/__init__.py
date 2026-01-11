# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/github/operations/__init__.py
# module: quack_core.integrations.github.operations.__init__
# role: module
# neighbors: issues.py, pull_requests.py, repositories.py, users.py
# exports: get_repo, star_repo, unstar_repo, is_repo_starred, fork_repo, check_repository_exists, get_repository_file_content, update_repository_file (+9 more)
# git_branch: feat/9-make-setup-work
# git_commit: 8234fdcd
# === QV-LLM:END ===

"""GitHub API _ops."""

from .issues import add_issue_comment, create_issue, get_issue, list_issues
from .pull_requests import (
    create_pull_request,
    get_pull_request,
    get_pull_request_files,
    list_pull_requests,
)
from .repositories import (
    check_repository_exists,
    fork_repo,
    get_repo,
    get_repository_file_content,
    is_repo_starred,
    star_repo,
    unstar_repo,
    update_repository_file,
)
from .users import get_user

__all__ = [
    # Repository _ops
    "get_repo",
    "star_repo",
    "unstar_repo",
    "is_repo_starred",
    "fork_repo",
    "check_repository_exists",
    "get_repository_file_content",
    "update_repository_file",
    # User _ops
    "get_user",
    # Pull request _ops
    "create_pull_request",
    "list_pull_requests",
    "get_pull_request",
    "get_pull_request_files",
    # Issue _ops
    "create_issue",
    "list_issues",
    "get_issue",
    "add_issue_comment",
]
