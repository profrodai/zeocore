# QuackCore GitHub Integration Documentation

## Overview

The `quack_core.integrations.github` module provides a robust, Pythonic interface to the GitHub API, designed specifically for QuackCore applications. It allows you to interact with GitHub repositories, manage pull requests, handle issues, and includes specialized features for teaching workflows like managing assignments and grading.

## Installation and Setup

### Prerequisites

- Python 3.10+
- QuackCore package
- GitHub Personal Access Token (PAT)

### Installation

```bash
# If you've installed QuackCore, you already have access to the GitHub integration
pip install quack-core
```

### Obtaining a GitHub Token

1. Log into your GitHub account
2. Go to Settings > Developer settings > Personal access tokens
3. Click "Generate new token" and select the required permissions:
   - `repo` scope for repository access
   - `user` scope for user information
   - `workflow` scope if you need workflow-related functionality

### Configuring the Integration

There are two primary ways to configure the GitHub integration:

#### Method 1: Using Environment Variables

```bash
# Set the GitHub token as an environment variable
export GITHUB_TOKEN="your_github_token_here"

# Then, in your code
from quack_core.integrations.core import registry
github = registry.get_integration("GitHub")
github.initialize()  # Will use the token from environment variable
```

#### Method 2: Using Configuration Files

Create a YAML configuration file (e.g., `quack_config.yaml`):

```yaml
github:
  token: "your_github_token_here"  # Optional if you use GITHUB_TOKEN env var
  api_url: "https://api.github.com"  # Default GitHub API URL
  timeout_seconds: 30
  max_retries: 3
  retry_delay: 1.0
  teaching:
    assignment_branch_prefix: "assignment-"
    default_base_branch: "main"
    pr_title_template: "[SUBMISSION] {title}"
```

Then, in your code:

```python
import os
from quack_core.integrations.core import registry
from quack_core.config import load_config

# Set the path to your config file
os.environ["QUACK_CONFIG"] = "path/to/quack_config.yaml"

# Get and initialize the GitHub integration
github = registry.get_integration("GitHub")
github.initialize()
```

## Basic Usage Examples

### Getting the Integration

```python
from quack_core.integrations.core import registry

# Get the GitHub integration from the registry
github = registry.get_integration("GitHub")

# Initialize the integration
init_result = github.initialize()
if not init_result.success:
    print(f"Failed to initialize GitHub integration: {init_result.error}")
    exit(1)
```

### Working with Repositories

```python
# Get repository information
repo_result = github.get_repo("username/repo")
if repo_result.success:
    repo = repo_result.content
    print(f"Repository: {repo.full_name}")
    print(f"Description: {repo.description}")
    print(f"Stars: {repo.stargazers_count}")
    print(f"Forks: {repo.forks_count}")
else:
    print(f"Error: {repo_result.error}")

# Star a repository
star_result = github.star_repo("username/repo")
if star_result.success:
    print("Repository starred successfully!")

# Fork a repository
fork_result = github.fork_repo("username/repo")
if fork_result.success:
    forked_repo = fork_result.content
    print(f"Repository forked to: {forked_repo.full_name}")
```

### Working with Pull Requests

```python
# Create a pull request
pr_result = github.create_pull_request(
    base_repo="original-owner/repo",
    head="your-username:feature-branch",
    title="Add new feature",
    body="This pull request adds a new feature",
    base_branch="main"
)

if pr_result.success:
    pr = pr_result.content
    print(f"Pull request #{pr.number} created: {pr.url}")

# List pull requests
prs_result = github.list_pull_requests(
    repo="username/repo",
    state="open"  # Can be 'open', 'closed', or 'all'
)

if prs_result.success:
    prs = prs_result.content
    print(f"Found {len(prs)} open pull requests:")
    for pr in prs:
        print(f"  #{pr.number}: {pr.title} by {pr.author.username}")
```

### Working with Issues

```python
# Create an issue
issue_result = github.create_issue(
    repo="username/repo",
    title="Bug in feature X",
    body="When using feature X, I encountered...",
    labels=["bug", "priority-high"]
)

if issue_result.success:
    issue = issue_result.content
    print(f"Issue created: {issue['html_url']}")

# Add a comment to an issue
comment_result = github.add_issue_comment(
    repo="username/repo",
    issue_number=123,
    body="I've investigated this issue and found that..."
)

if comment_result.success:
    comment = comment_result.content
    print(f"Comment added: {comment['html_url']}")
```

## Core Components and Architecture

The GitHub integration follows a modular architecture:

### Main Components

1. **GitHubIntegration**: The main integration class that implements the GitHub integration protocol.

2. **GitHubClient**: Client for interacting with the GitHub API, serving as a facade for operations.

3. **GitHubAuthProvider**: Handles authentication with GitHub using personal access tokens.

4. **GitHubConfigProvider**: Manages configuration for the GitHub integration.

5. **GitHubTeachingAdapter**: Specialized adapter for teaching workflows (assignments, grading).

6. **Operations Modules**: Domain-specific operations organized in separate modules:
   - `repositories.py`: Repository operations (get, star, fork)
   - `pull_requests.py`: Pull request operations (create, list, get)
   - `issues.py`: Issue operations (create, list, get, comment)
   - `users.py`: User operations (get user information)

7. **Models**: Data models defined using Pydantic:
   - `GitHubRepo`: Repository information
   - `GitHubUser`: User information
   - `PullRequest`: Pull request information
   - `GradeResult`: Grading result information

### Understanding the Result Pattern

All operations return an `IntegrationResult` object, which has:

- `success`: Boolean indicating if the operation was successful
- `content`: The result data (when successful)
- `error`: Error message (when unsuccessful)
- `message`: Optional additional information

Example of handling results:

```python
result = github.get_repo("username/repo")
if result.success:
    # Work with result.content
    repo = result.content
    print(f"Repository: {repo.full_name}")
else:
    # Handle error
    print(f"Error: {result.error}")
```

## Common Workflows

### Repository Management

#### Getting Repository Information

```python
repo_result = github.get_repo("username/repo")
if repo_result.success:
    repo = repo_result.content
    print(f"Repository: {repo.full_name}")
    print(f"Description: {repo.description}")
    print(f"Default branch: {repo.default_branch}")
    print(f"Owner: {repo.owner.username}")
```

#### Starring and Unstarring Repositories

```python
# Star a repository
star_result = github.star_repo("username/repo")
if star_result.success:
    print("Repository starred successfully!")

# Check if a repository is starred
is_starred = github.client.is_repo_starred("username/repo")
print(f"Repository is starred: {is_starred}")

# Unstar a repository
unstar_result = github.client.unstar_repo("username/repo")
if unstar_result:
    print("Repository unstarred successfully!")
```

#### Forking a Repository

```python
fork_result = github.fork_repo("username/repo")
if fork_result.success:
    forked_repo = fork_result.content
    print(f"Repository forked to: {forked_repo.full_name}")
    print(f"Clone URL: {forked_repo.clone_url}")
```

#### Working with Repository Files

```python
# Get file content
content_result = github.client.get_repository_file_content(
    repo="username/repo",
    path="GET-STARTED.md"
)

if isinstance(content_result, tuple) and len(content_result) == 2:
    content, sha = content_result
    print("README Content:")
    print(content)
    
    # Update the file
    update_result = github.client.update_repository_file(
        repo="username/repo",
        path="GET-STARTED.md",
        content=content + "\n\nUpdated by QuackCore!",
        message="Update README",
        sha=sha
    )
    
    if update_result:
        print("README updated successfully!")
```

### Pull Request Workflows

#### Creating a Pull Request

```python
pr_result = github.create_pull_request(
    base_repo="original-owner/repo",
    head="your-username:feature-branch",
    title="Add new feature",
    body="This pull request adds a new feature",
    base_branch="main"
)

if pr_result.success:
    pr = pr_result.content
    print(f"Pull request #{pr.number} created: {pr.url}")
```

#### Listing Pull Requests

```python
# List all open pull requests
prs_result = github.list_pull_requests(
    repo="username/repo",
    state="open"  # Can be 'open', 'closed', or 'all'
)

if prs_result.success:
    prs = prs_result.content
    print(f"Found {len(prs)} open pull requests:")
    for pr in prs:
        print(f"  #{pr.number}: {pr.title} by {pr.author.username}")
        
# Filter pull requests by author
author_prs_result = github.list_pull_requests(
    repo="username/repo",
    state="all",
    author="specific-username"
)

if author_prs_result.success:
    author_prs = author_prs_result.content
    print(f"Found {len(author_prs)} pull requests by specific-username")
```

#### Getting a Specific Pull Request

```python
pr_result = github.get_pull_request(
    repo="username/repo",
    number=123
)

if pr_result.success:
    pr = pr_result.content
    print(f"Pull request #{pr.number}: {pr.title}")
    print(f"Status: {pr.status}")
    print(f"Author: {pr.author.username}")
    print(f"Created: {pr.created_at}")
    if pr.merged_at:
        print(f"Merged: {pr.merged_at}")
```

#### Merging a Pull Request

```python
merge_result = github.client.merge_pull_request(
    repo="username/repo",
    pull_number=123,
    commit_title="Merge pull request #123",
    commit_message="This merges the feature branch",
    merge_method="squash"  # Can be 'merge', 'squash', or 'rebase'
)

if merge_result:
    print("Pull request merged successfully!")
```

### Issue Management

#### Creating an Issue

```python
issue_result = github.create_issue(
    repo="username/repo",
    title="Bug in feature X",
    body="When using feature X, I encountered...",
    labels=["bug", "priority-high"],
    assignees=["username"]
)

if issue_result.success:
    issue = issue_result.content
    print(f"Issue created: {issue['html_url']}")
```

#### Listing Issues

```python
issues_result = github.list_issues(
    repo="username/repo",
    state="open",  # Can be 'open', 'closed', or 'all'
    labels="bug",  # Comma-separated list of labels
    sort="created",  # Can be 'created', 'updated', 'comments'
    direction="desc"  # Can be 'asc' or 'desc'
)

if issues_result.success:
    issues = issues_result.content
    print(f"Found {len(issues)} open issues with 'bug' label:")
    for issue in issues:
        print(f"  #{issue['number']}: {issue['title']}")
```

#### Getting a Specific Issue

```python
issue_result = github.get_issue(
    repo="username/repo",
    issue_number=123
)

if issue_result.success:
    issue = issue_result.content
    print(f"Issue #{issue['number']}: {issue['title']}")
    print(f"State: {issue['state']}")
    print(f"Created by: {issue['user']['login']}")
    print(f"Body: {issue['body']}")
```

#### Adding a Comment to an Issue

```python
comment_result = github.add_issue_comment(
    repo="username/repo",
    issue_number=123,
    body="I've investigated this issue and found that..."
)

if comment_result.success:
    comment = comment_result.content
    print(f"Comment added: {comment['html_url']}")
```

## Teaching Features

The GitHub integration includes specialized features for teaching and education workflows.

### Assignment Submission Workflow

#### Step 1: Ensure Repository is Forked

```python
fork_result = github.ensure_forked("course-org/assignment-repo")
if fork_result.success:
    forked_repo = fork_result.content
    print(f"Assignment repository forked to: {forked_repo}")
else:
    print(f"Error: {fork_result.error}")
```

#### Step 2: Create and Push Assignment Branch

This step would typically be done outside of the integration, using git:

```bash
git clone https://github.com/student-username/assignment-repo.git
cd assignment-repo
git checkout -b assignment-solution
# Make changes to complete the assignment
git add .
git commit -m "Complete assignment"
git push origin assignment-solution
```

#### Step 3: Submit Assignment as Pull Request

```python
submission_result = github.submit_assignment(
    forked_repo="student-username/assignment-repo",
    base_repo="course-org/assignment-repo",
    branch="assignment-solution",
    title="Assignment 1 Solution",
    body="This is my solution for Assignment 1."
)

if submission_result.success:
    pr_url = submission_result.content
    print(f"Assignment submitted: {pr_url}")
else:
    print(f"Error submitting assignment: {submission_result.error}")
```

### Grading Assignments

#### Getting Student Submissions

```python
submission_result = github.get_latest_submission(
    repo="course-org/assignment-repo",
    student="student-username"
)

if submission_result.success:
    pr = submission_result.content
    print(f"Found submission: PR #{pr.number} - {pr.title}")
else:
    print(f"No submission found: {submission_result.error}")
```

#### Grading a Submission

```python
# Define grading criteria
grading_criteria = {
    "passing_threshold": 0.7,  # 70% to pass
    "required_files": {
        "points": 50,
        "files": ["GET-STARTED.md", "solution.py", "test_solution.py"]
    },
    "required_changes": {
        "points": 30,
        "changes": [
            {
                "file": "solution.py",
                "min_additions": 20,
                "description": "Implement the required solution functions"
            },
            {
                "file": "test_solution.py",
                "min_additions": 15,
                "description": "Implement tests for your solution"
            }
        ]
    },
    "prohibited_patterns": {
        "points": 20,
        "patterns": [
            {
                "pattern": r"import os\s*;",
                "description": "Using semicolons in Python is discouraged"
            },
            {
                "pattern": r"print\(['\"]DEBUG",
                "description": "Remove debug print statements"
            }
        ]
    }
}

# Grade the submission
grade_result = github.grade_submission(pr, grading_criteria)

if grade_result.success:
    grade = grade_result.content
    print(f"Score: {grade.score * 100:.1f}%")
    print(f"Passed: {grade.passed}")
    print("\nFeedback:")
    print(grade.comments)
else:
    print(f"Error grading submission: {grade_result.error}")
```

#### Providing Feedback via PR Review

```python
# Add a review to the pull request
review_result = github.client.add_pull_request_review(
    repo="course-org/assignment-repo",
    pull_number=pr.number,
    body=grade.comments,
    event="COMMENT"  # Can be 'APPROVE', 'REQUEST_CHANGES', or 'COMMENT'
)

if review_result:
    print("Feedback submitted as PR review")
```

## Advanced Usage

### Working with Multiple Integrations

You can use the GitHub integration alongside other QuackCore integrations:

```python
from quack_core.integrations.core import registry

# Get GitHub integration
github = registry.get_integration("GitHub")
github.initialize()

# Get another integration (e.g., Google Drive)
drive = registry.get_integration("GoogleDrive")
drive.initialize()

# Use them together
repo_result = github.get_repo("username/docs-repo")
if repo_result.success:
    repo = repo_result.content
    
    # Download README from GitHub
    readme_content, _ = github.client.get_repository_file_content(
        repo=repo.full_name,
        path="GET-STARTED.md"
    )
    
    # Upload to Google Drive
    drive.upload_file_content(
        content=readme_content,
        filename="GitHub-GET-STARTED.md",
        mime_type="text/markdown"
    )
```

### Custom Configuration

You can create a custom-configured integration:

```python
from quack_core.integrations.github import (
    GitHubIntegration,
    GitHubAuthProvider,
    GitHubConfigProvider
)

# Create custom providers
auth_provider = GitHubAuthProvider(
    credentials_file="~/.my_app/github_credentials.json"
)

config_provider = GitHubConfigProvider()

# Create the integration with custom providers
github = GitHubIntegration(
    auth_provider=auth_provider,
    config_provider=config_provider,
    config_path="./my_config.yaml"
)

# Initialize
init_result = github.initialize()
if init_result.success:
    # Use the custom-configured integration
    github.get_repo("username/repo")
```

### Handling Rate Limiting

The GitHub API has rate limits. The integration handles basic retries, but for intensive operations:

```python
import time

def paginated_fetch_all_repos(github, username):
    """Fetch all repositories with pagination and rate limit handling."""
    page = 1
    all_repos = []
    
    while True:
        try:
            # This is a hypothetical method - you might need to implement similar logic
            repos_result = github.list_user_repositories(
                username=username,
                page=page,
                per_page=100
            )
            
            if not repos_result.success:
                print(f"Error: {repos_result.error}")
                break
                
            repos = repos_result.content
            if not repos:
                break  # No more repos
                
            all_repos.extend(repos)
            page += 1
            
            # Add delay to avoid hitting rate limits
            time.sleep(1)
            
        except Exception as e:
            if "rate limit exceeded" in str(e).lower():
                print("Rate limit hit. Waiting 60 seconds...")
                time.sleep(60)
                continue
            raise
            
    return all_repos
```

## Best Practices

### Error Handling

Always check the `success` attribute of results before accessing `content`:

```python
# Good practice
result = github.get_repo("username/repo")
if result.success:
    repo = result.content
    # Work with repo
else:
    # Handle error
    print(f"Error: {result.error}")
    
# Avoid this pattern (can cause AttributeError)
result = github.get_repo("username/repo")
repo = result.content  # Might fail if result.success is False
```

### Configuration Management

Store sensitive information like tokens in environment variables or secure credential stores:

```python
# In your deployment environment
export GITHUB_TOKEN="your_github_token_here"

# In your code
import os
from quack_core.integrations.core import registry

# Token will be automatically picked up from environment
github = registry.get_integration("GitHub")
github.initialize()
```

### Resource Cleanup

For long-running applications, consider adding cleanup steps:

```python
try:
    # Use the GitHub integration
    github.initialize()
    # Do your work...
finally:
    # Clean up any resources
    if hasattr(github, 'client') and github.client:
        github.client.session.close()
```

### Rate Limit Awareness

Be mindful of GitHub API rate limits, especially in batch operations:

```python
# For bulk _ops, add delay between requests
import time

repos = ["user/repo1", "user/repo2", "user/repo3", "user/repo4"]
for repo in repos:
    result = github.get_repo(repo)
    # Process result...
    
    # Add delay to avoid hitting rate limits
    time.sleep(1)
```

## Troubleshooting

### Common Issues and Solutions

#### Authentication Failures

**Issue**: `QuackAuthenticationError: GitHub API authentication failed`

**Solutions**:
1. Check if your token is valid and has the correct permissions
2. Ensure the token is being correctly loaded from config or environment
3. Verify the token hasn't expired (if using an OAuth token)

```python
# Debugging token issue
import os
print(f"Token set in environment: {'GITHUB_TOKEN' in os.environ}")

# Check token permissions by trying a simple operation
from quack_core.integrations.github import GitHubClient
client = GitHubClient(token=os.environ.get("GITHUB_TOKEN", ""))
try:
    user = client.get_user()
    print(f"Authentication working: {user.username}")
except Exception as e:
    print(f"Authentication error: {e}")
```

#### Rate Limiting

**Issue**: `QuackQuotaExceededError: GitHub API rate limit exceeded`

**Solutions**:
1. Implement backoff and retry logic
2. Reduce the frequency of API calls
3. Consider using conditional requests with ETags
4. For authenticated requests, use a token with higher rate limits

#### Missing Resources

**Issue**: `QuackApiError: GitHub API error: Not Found`

**Solutions**:
1. Check the repository or resource name for typos
2. Verify permissions (private repositories require specific token permissions)
3. Confirm the resource exists

```python
# Check if repository exists before _ops
if github.client.check_repository_exists("username/repo"):
    # Proceed with _ops
    pass
else:
    print("Repository does not exist or is not accessible")
```

#### Integration Not Found

**Issue**: `github = registry.get_integration("GitHub")` returns `None`

**Solutions**:
1. Ensure the integration is registered
2. Check for any import errors

```python
# Print available integrations
from quack_core.integrations.core import registry
print(f"Available integrations: {registry.list_integrations()}")

# Manually register the integration if needed
from quack_core.integrations.github import GitHubIntegration
integration = GitHubIntegration()
registry.register(integration)
```

### Enabling Debug Logging

For detailed logging information:

```python
import logging
from quack_core.core.logging import get_logger

# Set logging level to DEBUG for the GitHub integration
logger = get_logger("quack_core.integrations.github")
logger.setLevel(logging.DEBUG)

# Or set it for all QuackCore modules
quackcore_logger = get_logger("quack-core")
quackcore_logger.setLevel(logging.DEBUG)
```

## API Reference

### GitHubIntegration

The main integration class that provides access to GitHub functionality.

```python
github = registry.get_integration("GitHub")
```

Key methods:

| Method | Description |
|--------|-------------|
| `initialize()` | Initialize the integration |
| `get_current_user()` | Get the authenticated user |
| `get_repo(full_name)` | Get repository information |
| `star_repo(full_name)` | Star a repository |
| `fork_repo(full_name)` | Fork a repository |
| `create_pull_request(...)` | Create a pull request |
| `list_pull_requests(...)` | List pull requests for a repository |
| `get_pull_request(repo, number)` | Get a specific pull request |
| `ensure_starred(repo)` | Ensure a repository is starred |
| `ensure_forked(repo)` | Ensure a repository is forked |
| `submit_assignment(...)` | Submit an assignment as a pull request |
| `get_latest_submission(repo, student)` | Get the latest submission for a student |
| `grade_submission(pull_request, criteria)` | Grade a submission |

### GitHubClient

Client for direct interaction with the GitHub API.

```python
client = github.client
```

Key methods:

| Method | Description |
|--------|-------------|
| `get_user(username=None)` | Get user information |
| `get_repo(full_name)` | Get repository information |
| `star_repo(full_name)` | Star a repository |
| `unstar_repo(full_name)` | Unstar a repository |
| `is_repo_starred(full_name)` | Check if a repository is starred |
| `fork_repo(full_name, organization=None)` | Fork a repository |
| `create_pull_request(...)` | Create a pull request |
| `list_pull_requests(...)` | List pull requests |
| `get_pull_request(repo, number)` | Get a specific pull request |
| `merge_pull_request(...)` | Merge a pull request |
| `get_pull_request_files(...)` | Get files changed in a pull request |
| `add_pull_request_review(...)` | Add a review to a pull request |
| `create_issue(...)` | Create an issue |
| `list_issues(...)` | List issues |
| `get_issue(repo, issue_number)` | Get a specific issue |
| `add_issue_comment(...)` | Add a comment to an issue |
| `check_repository_exists(full_name)` | Check if a repository exists |
| `get_repository_file_content(...)` | Get file content from a repository |
| `update_repository_file(...)` | Update a file in a repository |

### GitHubTeachingAdapter

Adapter for teaching-specific functionality.

```python
teaching_adapter = github.teaching_adapter
```

Key methods:

| Method | Description |
|--------|-------------|
| `ensure_starred(repo)` | Ensure a repository is starred |
| `ensure_forked(repo)` | Ensure a repository is forked |
| `submit_assignment(...)` | Submit an assignment as a pull request |
| `get_latest_submission(repo, student)` | Get the latest submission for a student |

### GitHubGrader

Utility for grading assignment submissions.

```python
grader = github.grader
```

Key methods:

| Method | Description |
|--------|-------------|
| `grade_submission(pull_request, criteria)` | Grade a submission based on criteria |
| `compare_file_versions(...)` | Compare different versions of a file |

### Models

#### GitHubRepo

Represents a GitHub repository.

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Repository name without owner |
| `full_name` | `str` | Full repository name with owner (owner/repo) |
| `url` | `HttpUrl` | Repository URL |
| `clone_url` | `HttpUrl` | Git clone URL |
| `default_branch` | `str` | Default branch name |
| `description` | `str` | Repository description |
| `fork` | `bool` | Whether this repo is a fork |
| `forks_count` | `int` | Number of forks |
| `stargazers_count` | `int` | Number of stars |
| `owner` | `GitHubUser` | Repository owner |

#### GitHubUser

Represents a GitHub user.

| Attribute | Type | Description |
|-----------|------|-------------|
| `username` | `str` | GitHub username |
| `url` | `HttpUrl` | GitHub profile URL |
| `name` | `str` | User's full name (if available) |
| `email` | `str` | User's email (if available) |
| `avatar_url` | `HttpUrl` | URL to user's avatar |

#### PullRequest

Represents a GitHub pull request.

| Attribute | Type | Description |
|-----------|------|-------------|
| `number` | `int` | Pull request number |
| `title` | `str` | Pull request title |
| `url` | `HttpUrl` | Pull request URL |
| `author` | `GitHubUser` | Pull request author |
| `status` | `PullRequestStatus` | Status (OPEN, CLOSED, MERGED) |
| `body` | `str` | Pull request body |
| `created_at` | `datetime` | Creation date |
| `updated_at` | `datetime` | Last update date |
| `merged_at` | `datetime` | Merge date (if merged) |
| `base_repo` | `str` | Base repository name |
| `head_repo` | `str` | Head repository name |
| `base_branch` | `str` | Base branch name |
| `head_branch` | `str` | Head branch name |

#### GradeResult

Represents the result of grading a submission.

| Attribute | Type | Description |
|-----------|------|-------------|
| `score` | `float` | Score between 0.0 and 1.0 |
| `passed` | `bool` | Whether the submission passed |
| `comments` | `str` | Feedback comments |
| `details` | `dict` | Detailed grading information |
