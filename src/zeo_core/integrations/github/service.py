"""GitHub core integration service for zeo_core."""

from zeo_core.core.logging import LOG_LEVELS, LogLevel, get_logger
from zeo_core.integrations.core import (
    AuthProviderProtocol,
    BaseIntegrationService,
    ConfigProviderProtocol,
    IntegrationResult,
)

from .auth import GitHubAuthProvider
from .client import GitHubClient
from .config import GitHubConfigProvider
from .models import GitHubRepo, GitHubUser, PullRequest
from .protocols import GitHubIntegrationProtocol

logger = get_logger(__name__)


class GitHubIntegration(BaseIntegrationService, GitHubIntegrationProtocol):
    """GitHub integration for zeo_core."""

    def __init__(
        self,
        config_provider: ConfigProviderProtocol | None = None,
        auth_provider: AuthProviderProtocol | None = None,
        config_path: str | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
    ) -> None:
        """Initialize the GitHub integration.

        Args:
            config_provider: Configuration provider
            auth_provider: Authentication provider
            config_path: Path to configuration file
            log_level: Logging level
        """
        # Create default providers if not provided
        if config_provider is None:
            config_provider = GitHubConfigProvider(log_level=log_level)

        if auth_provider is None:
            auth_provider = GitHubAuthProvider(log_level=log_level)

        super().__init__(
            config_provider=config_provider,
            auth_provider=None,
            config=None,
            config_path=config_path,
            log_level=log_level,
        )

        self.client: GitHubClient | None = None

    @property
    def name(self) -> str:
        """Name of the integration."""
        return "GitHub"

    @property
    def version(self) -> str:
        """Version of the integration."""
        return "1.0.0"

    def _ensure_initialized(self) -> IntegrationResult | None:
        """Ensure the integration is initialized.

        Returns:
            IntegrationResult error if not initialized, None if initialized
        """
        if not self._initialized:
            logger.error("GitHub integration is not initialized")
            not_initialized_msg = (
                "GitHub integration is not initialized. Call initialize() first."
            )
            return IntegrationResult.error_result(
                error=not_initialized_msg,
                message=not_initialized_msg,
            )
        return None

    def _check_config_available(self) -> IntegrationResult | None:
        """Check that configuration was loaded successfully.

        Returns:
            IntegrationResult error if configuration is unavailable, else None
        """
        try:
            # If self.config is None, return a specific error
            if self.config is None:
                return IntegrationResult.error_result(
                    error="GitHub configuration is not available",
                    message="GitHub configuration is not available",
                )
        except Exception as e:
            # If any exception occurs while accessing self.config
            logger.exception("Exception while accessing configuration")
            return IntegrationResult.error_result(
                error=f"Failed to initialize GitHub integration: {str(e)}",
                message=f"Failed to initialize GitHub integration: {str(e)}",
            )
        return None

    def _authenticate_with_config_token(self, token: str) -> IntegrationResult | None:
        """Authenticate the auth provider using a token found in config.

        Args:
            token: GitHub token read from configuration

        Returns:
            IntegrationResult error on failure, else None
        """
        logger.debug("Using GitHub token from configuration")
        # If we have a token from config, use it to authenticate the auth_provider
        if not self.auth_provider:
            return None

        try:
            auth_result = self.auth_provider.authenticate()
            if not auth_result.success:
                logger.warning(
                    "Failed to authenticate auth provider with token from "
                    f"config: {auth_result.error}"
                )
                error_msg = getattr(auth_result, "error", "Authentication failed")
                return IntegrationResult.error_result(
                    error=f"Failed to authenticate with GitHub: {error_msg}",
                    message=f"Failed to authenticate with GitHub: {error_msg}",
                )
        except Exception as e:
            # Handle exceptions from authentication
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to initialize GitHub integration: {error_msg}",
                message=f"Failed to initialize GitHub integration: {error_msg}",
            )
        return None

    def _get_token_from_auth_provider(
        self,
    ) -> tuple[str | None, IntegrationResult | None]:
        """Obtain a GitHub token from the auth provider directly.

        Returns:
            Tuple of (token, error_result). error_result is None on success,
            in which case token may still be falsy if no provider is set.
        """
        if not self.auth_provider:
            return None, None

        try:
            logger.debug("Getting credentials from auth provider")
            auth_result = self.auth_provider.get_credentials()

            if isinstance(auth_result, dict):
                token = auth_result.get("token")
            else:
                token = getattr(auth_result, "token", None)

            # If still no token, try to authenticate
            if not token:
                logger.debug("No token from get_credentials, trying authenticate()")
                auth_result = self.auth_provider.authenticate()
                if auth_result.success:
                    credentials = self.auth_provider.get_credentials()
                    if isinstance(credentials, dict):
                        token = credentials.get("token")
                    else:
                        token = getattr(credentials, "token", None)
                if not token:
                    error_msg = getattr(auth_result, "error", "Authentication failed")
                    logger.error(f"Authentication failed: {error_msg}")
                    return None, IntegrationResult.error_result(
                        error=f"Failed to authenticate with GitHub: {error_msg}",
                        message=f"Failed to authenticate with GitHub: {error_msg}",
                    )
        except Exception as e:
            # Handle exceptions from authentication
            error_msg = str(e)
            return None, IntegrationResult.error_result(
                error=f"Failed to initialize GitHub integration: {error_msg}",
                message=f"Failed to initialize GitHub integration: {error_msg}",
            )
        return token, None

    def _resolve_auth_token(self) -> tuple[str | None, IntegrationResult | None]:
        """Resolve the GitHub token to use, from config or auth provider.

        Returns:
            Tuple of (token, error_result). error_result is None on success.
        """
        # self.config is always non-None here in practice: initialize()
        # calls _check_config_available() (which validates this exact
        # invariant) and returns early on failure before ever reaching
        # this method -- mypy cannot see that across the call boundary.
        # Explicit guard, not a behavior change.
        if self.config is None:
            return None, IntegrationResult.error_result(
                error="GitHub configuration is not available",
                message="GitHub configuration is not available",
            )

        # Get authentication token from config
        token = self.config.get("token")

        # If token is in config, use it for authentication
        if token:
            error_result = self._authenticate_with_config_token(token)
            if error_result:
                return None, error_result
            return token, None

        # No token in config, try to get it from auth provider
        return self._get_token_from_auth_provider()

    def _create_github_client(self, token: str) -> IntegrationResult:
        """Create the GitHub client and mark the integration initialized.

        Args:
            token: GitHub token to authenticate the client with

        Returns:
            Success result on success, error result on failure
        """
        try:
            # See _resolve_auth_token's own comment: self.config is always
            # non-None here in practice (initialize()'s own call order
            # guarantees it), mypy just can't see across the call
            # boundary. Explicit guard, not a behavior change.
            if self.config is None:
                return IntegrationResult.error_result(
                    error="GitHub configuration is not available",
                    message="GitHub configuration is not available",
                )
            self.client = GitHubClient(
                token=token,
                api_url=self.config.get("api_url", "https://api.github.com"),
                timeout=self.config.get("timeout_seconds", 30),
                max_retries=self.config.get("max_retries", 3),
                retry_delay=self.config.get("retry_delay", 1.0),
            )

            # Set initialized flag only after successful client creation
            self._initialized = True
            return IntegrationResult.success_result(
                message="GitHub integration initialized successfully"
            )
        except Exception as e:
            # Handle exceptions from client initialization
            error_msg = str(e)
            # Ensure _initialized is set to False in case of exception
            self._initialized = False
            return IntegrationResult.error_result(
                error=f"Failed to initialize GitHub client: {error_msg}",
                message=f"Failed to initialize GitHub client: {error_msg}",
            )

    def initialize(self) -> IntegrationResult:
        """Initialize the GitHub integration.

        Returns:
            Result of the initialization
        """
        try:
            # First, call the base initialization
            init_result = super().initialize()
            if not init_result.success:
                return init_result

            # Get configuration - this can now properly raise exceptions
            config_error = self._check_config_available()
            if config_error:
                return config_error

            token, auth_error = self._resolve_auth_token()
            if auth_error:
                return auth_error

            if not token:
                error_msg = (
                    "GitHub token is not configured and no auth provider is available"
                )
                return IntegrationResult.error_result(
                    error=error_msg, message=error_msg
                )

            # Initialize GitHub client
            return self._create_github_client(token)
        except Exception as e:
            # Catch-all for any unexpected exceptions
            logger.exception("Unexpected error in GitHub integration initialization")
            error_msg = str(e)
            # Ensure _initialized is set to False in case of exception
            self._initialized = False
            return IntegrationResult.error_result(
                error=f"Failed to initialize GitHub integration: {error_msg}",
                message=f"Failed to initialize GitHub integration: {error_msg}",
            )

    def is_available(self) -> bool:
        """Check if the GitHub integration is available.

        Returns:
            True if available, False otherwise
        """
        return self._initialized and self.client is not None

    # User and Repository Methods

    def get_current_user(self) -> IntegrationResult[GitHubUser]:
        """Get the authenticated user.

        Returns:
            Result with GitHubUser
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        # self.client is always set together with _initialized=True in
        # _create_github_client -- this can never actually be None here,
        # but mypy cannot narrow self.client across the _ensure_initialized
        # call boundary (confirmed: a helper method's own internal None
        # check does not propagate narrowing to the caller). Explicit
        # guard, not a behavior change.
        if self.client is None:
            return IntegrationResult.error_result(
                error="GitHub client is not initialized",
                message="GitHub client is not initialized",
            )

        try:
            user = self.client.get_user()
            return IntegrationResult.success_result(
                content=user, message=f"Successfully retrieved user {user.username}"
            )
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to get user: {error_msg}",
                message=f"Failed to get user: {error_msg}",
            )

    def get_repo(self, full_name: str) -> IntegrationResult[GitHubRepo]:
        """Get a GitHub repository.

        Args:
            full_name: Full repository name (owner/repo)

        Returns:
            Result with GitHubRepo
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        # See get_current_user's own comment: self.client is always set
        # together with _initialized=True, mypy just can't see across the
        # helper call boundary. Explicit guard, not a behavior change.
        if self.client is None:
            return IntegrationResult.error_result(
                error="GitHub client is not initialized",
                message="GitHub client is not initialized",
            )

        try:
            repo = self.client.get_repo(full_name)
            return IntegrationResult.success_result(
                content=repo,
                message=f"Successfully retrieved repository {repo.full_name}",
            )
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to get repository: {error_msg}",
                message=f"Failed to get repository: {error_msg}",
            )

    def star_repo(self, full_name: str) -> IntegrationResult[bool]:
        """Star a GitHub repository.

        Args:
            full_name: Full repository name (owner/repo)

        Returns:
            Result with True if successful
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        # See get_current_user's own comment: self.client is always set
        # together with _initialized=True, mypy just can't see across the
        # helper call boundary. Explicit guard, not a behavior change.
        if self.client is None:
            return IntegrationResult.error_result(
                error="GitHub client is not initialized",
                message="GitHub client is not initialized",
            )

        try:
            self.client.star_repo(full_name)
            return IntegrationResult.success_result(
                content=True, message=f"Successfully starred repository {full_name}"
            )
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to star repository: {error_msg}",
                message=f"Failed to star repository: {error_msg}",
            )

    def fork_repo(self, full_name: str) -> IntegrationResult[GitHubRepo]:
        """Fork a GitHub repository.

        Args:
            full_name: Full repository name (owner/repo)

        Returns:
            Result with GitHubRepo for the fork
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        # See get_current_user's own comment: self.client is always set
        # together with _initialized=True, mypy just can't see across the
        # helper call boundary. Explicit guard, not a behavior change.
        if self.client is None:
            return IntegrationResult.error_result(
                error="GitHub client is not initialized",
                message="GitHub client is not initialized",
            )

        try:
            fork = self.client.fork_repo(full_name)
            return IntegrationResult.success_result(
                content=fork,
                message=(
                    f"Successfully forked repository {full_name} to {fork.full_name}"
                ),
            )
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to fork repository: {error_msg}",
                message=f"Failed to fork repository: {error_msg}",
            )

    # Pull Request Methods

    def create_pull_request(
        self,
        base_repo: str,
        head: str,
        title: str,
        body: str | None = None,
        base_branch: str = "main",
    ) -> IntegrationResult[PullRequest]:
        """Create a pull request.

        Args:
            base_repo: Full name of the base repository (owner/repo)
            head: Head reference in the format "username:branch"
            title: Pull request title
            body: Pull request body
            base_branch: Base branch to merge into

        Returns:
            Result with PullRequest
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        # See get_current_user's own comment: self.client is always set
        # together with _initialized=True, mypy just can't see across the
        # helper call boundary. Explicit guard, not a behavior change.
        if self.client is None:
            return IntegrationResult.error_result(
                error="GitHub client is not initialized",
                message="GitHub client is not initialized",
            )

        try:
            pr = self.client.create_pull_request(
                base_repo=base_repo,
                head=head,
                title=title,
                body=body,
                base_branch=base_branch,
            )
            return IntegrationResult.success_result(
                content=pr, message=f"Successfully created pull request #{pr.number}"
            )
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to create pull request: {error_msg}",
                message=f"Failed to create pull request: {error_msg}",
            )

    def list_pull_requests(
        self, repo: str, state: str = "open", author: str | None = None
    ) -> IntegrationResult[list[PullRequest]]:
        """List pull requests for a repository.

        Args:
            repo: Full repository name (owner/repo)
            state: Pull request state (open, closed, all)
            author: Filter by author username

        Returns:
            Result with list of PullRequest objects
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        # See get_current_user's own comment: self.client is always set
        # together with _initialized=True, mypy just can't see across the
        # helper call boundary. Explicit guard, not a behavior change.
        if self.client is None:
            return IntegrationResult.error_result(
                error="GitHub client is not initialized",
                message="GitHub client is not initialized",
            )

        try:
            # GitHubClient.list_pull_requests declares state as
            # Literal["open", "closed", "all"] (a real GitHub API
            # constraint); this service method's own signature stays the
            # wider `str` to match GitHubIntegrationProtocol (narrowing it
            # here would violate Liskov substitution against that protocol
            # -- confirmed live via mypy's own [override] error when
            # attempted). No new validation added here -- an invalid
            # string was already passed through to the real API
            # unvalidated before this round touched this file, and this
            # ignore keeps that pre-existing behavior byte-identical
            # rather than introduce a new rejection branch unilaterally.
            prs = self.client.list_pull_requests(
                repo=repo,
                state=state,  # type: ignore[arg-type]
                author=author,
            )
            return IntegrationResult.success_result(
                content=prs,
                message=f"Successfully retrieved {len(prs)} pull requests for {repo}",
            )
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to list pull requests: {error_msg}",
                message=f"Failed to list pull requests: {error_msg}",
            )

    def get_pull_request(
        self, repo: str, number: int
    ) -> IntegrationResult[PullRequest]:
        """Get a specific pull request.

        Args:
            repo: Full repository name (owner/repo)
            number: Pull request number

        Returns:
            Result with PullRequest object
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
        # See get_current_user's own comment: self.client is always set
        # together with _initialized=True, mypy just can't see across the
        # helper call boundary. Explicit guard, not a behavior change.
        if self.client is None:
            return IntegrationResult.error_result(
                error="GitHub client is not initialized",
                message="GitHub client is not initialized",
            )

        try:
            pr = self.client.get_pull_request(repo, number)
            return IntegrationResult.success_result(
                content=pr,
                message=f"Successfully retrieved pull request #{number} from {repo}",
            )
        except Exception as e:
            error_msg = str(e)
            return IntegrationResult.error_result(
                error=f"Failed to get pull request: {error_msg}",
                message=f"Failed to get pull request: {error_msg}",
            )
