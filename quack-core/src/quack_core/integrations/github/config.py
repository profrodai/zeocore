# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/github/config.py
# === QV-LLM:END ===

"""Configuration provider for GitHub integration."""

import os
from typing import Any

from quack_core.core.logging import get_logger
from quack_core.integrations.core import BaseConfigProvider, ConfigResult

logger = get_logger(__name__)


class GitHubConfigProvider(BaseConfigProvider):
    """Configuration provider for GitHub integration."""

    def __init__(
        self,
        log_level: int | str | None = None,
        # Added constructor with log_level parameter
    ) -> None:
        """Initialize the GitHub configuration provider.

        Args:
            log_level: Logging level
        """
        # Default to INFO level if None is provided
        super().__init__(log_level=log_level or "INFO")

    @property
    def name(self) -> str:
        """Name of the configuration provider."""
        return "GitHub"

    def get_default_config(self) -> dict[str, Any]:
        """Get default GitHub configuration."""
        return {
            "token": "",  # Default to empty, should be set in env or config
            "api_url": "https://api.github.com",
            "timeout_seconds": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
            "quackster": {
                "assignment_branch_prefix": "assignment-",
                "default_base_branch": "main",
                "pr_title_template": "[SUBMISSION] {title}",
                "pr_body_template": (
                    "This is a submission for the assignment: {assignment}"
                    "\n\nSubmitted by: {student}"
                ),
            },
        }

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate GitHub configuration."""
        # Check if token is available in config or environment variable
        has_token = False

        if "token" in config and config["token"]:
            has_token = True
        elif os.environ.get("GITHUB_TOKEN"):
            has_token = True

        if not has_token:
            logger.error(
                "GitHub token not found in config or GITHUB_TOKEN environment variable."
            )
            return False

        # Validate API URL format
        if "api_url" in config:
            api_url = config["api_url"]
            if not api_url.startswith(("http://", "https://")):
                logger.error(f"Invalid GitHub API URL format: {api_url}")
                return False

        return True

    @staticmethod
    def _lookup_dotted_or_direct_key(
        config_data: dict[str, Any], key: str
    ) -> Any | None:  # noqa: ANN401 -- genuinely dynamic: resolves an arbitrary-depth nested config value of unknown shape (str/int/bool/dict/list)
        """
        Resolve a single candidate key against config_data, handling both a
        dotted path (e.g. "integrations.github") and a direct key. Extracted
        from _extract_config to keep its own branch count under the C901
        threshold; behavior/order unchanged from the original inline loop.
        """
        if "." in key:
            parts = key.split(".")
            current: Any = config_data
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            return current
        if key in config_data:
            return config_data[key]
        return None

    def _find_github_config_section(
        self, config_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Look for the GitHub config section under the direct/dotted candidate
        keys, then under the "integrations" section as a fallback. Extracted
        from _extract_config for the same C901 reason as
        _lookup_dotted_or_direct_key.
        """
        for key in ["github", "GitHub", "integrations.github", "integrations.GitHub"]:
            found = self._lookup_dotted_or_direct_key(config_data, key)
            if found is not None:
                logger.debug(f"Found GitHub config using key: {key}")
                return found

        if "integrations" in config_data and isinstance(
            config_data["integrations"], dict
        ):
            for key in ["github", "GitHub"]:
                if key in config_data["integrations"]:
                    logger.debug(
                        f"Found GitHub config in integrations section with key: {key}"
                    )
                    return config_data["integrations"][key]

        return None

    def _extract_config(self, config_data: dict[str, Any]) -> dict[str, Any]:
        """Extract GitHub-specific configuration from the full config."""
        # If config_data is None, return a default config with env token if available
        if config_data is None:
            logger.debug("No config data provided, using defaults")
            default_config = self.get_default_config()
            env_token = os.environ.get("GITHUB_TOKEN")
            if env_token:
                default_config["token"] = env_token
                logger.debug("Added token from environment to default config")
            return default_config

        extracted_config = self._find_github_config_section(config_data)

        # If we found a config but it doesn't have a token, check environment
        if extracted_config is not None and (not extracted_config.get("token")):
            env_token = os.environ.get("GITHUB_TOKEN")
            if env_token:
                logger.debug("Adding token from environment to extracted config")
                extracted_config["token"] = env_token
            return extracted_config

        # If we still haven't found GitHub config, check for token in environment
        if extracted_config is None and os.environ.get("GITHUB_TOKEN"):
            # Create a minimal config with just the token from environment
            logger.debug("Creating config with token from environment")
            default_config = self.get_default_config()
            default_config["token"] = os.environ.get("GITHUB_TOKEN", "")
            return default_config

        # If we found something, return it
        if extracted_config is not None:
            return extracted_config

        # Fall back to default implementation
        logger.debug("Falling back to default config extraction")
        return super()._extract_config(config_data)

    def load_config(self, config_path: str | None = None) -> ConfigResult:
        """Load configuration from a file."""
        # First try loading from the QuackCore configuration system
        result = super().load_config(config_path)

        # Handle the case where config_path doesn't exist or has errors
        if not result.success or not result.content:
            logger.warning(f"Couldn't load config from {config_path}: {result.error}")
            # Create default config
            default_config = self.get_default_config()

            # Check for token in environment
            env_token = os.environ.get("GITHUB_TOKEN")
            if env_token:
                default_config["token"] = env_token
                logger.debug(
                    "Using GitHub token from environment variable in default config"
                )

            # Return success with default config
            return ConfigResult.success_result(
                message="Using default GitHub configuration",
                content=default_config,
                config_path=config_path,
            )

        # If successful but token is missing, try to get it from environment
        if result.content and "token" in result.content:
            # If token is empty, try to get from environment
            if not result.content["token"]:
                env_token = os.environ.get("GITHUB_TOKEN")
                if env_token:
                    result.content["token"] = env_token
                    logger.debug("Using GitHub token from environment variable")

        # If there's no token key at all, add it from environment if available
        elif result.content:
            env_token = os.environ.get("GITHUB_TOKEN")
            if env_token:
                result.content["token"] = env_token
                logger.debug("Added GitHub token from environment variable to config")

        return result
