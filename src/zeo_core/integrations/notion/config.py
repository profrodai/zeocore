"""Configuration provider for Notion integration."""

import os
from typing import Any

from pydantic import BaseModel, Field

from zeo_core.core.logging import LOG_LEVELS, LogLevel, get_logger
from zeo_core.integrations.core import BaseConfigProvider, ConfigResult

logger = get_logger(__name__)


class NotionConfig(BaseModel):
    """Typed view of Notion configuration.

    Kept for backward compatibility with callers that imported this model
    from the pre-existing stub (`notion/config.py`, 7 lines, no service
    behind it) -- NotionConfigProvider below is the config shape actually
    consumed by NotionIntegration, following GitHubConfigProvider's pattern
    (integration-token auth, not OAuth, matching Notion's own auth model).
    """

    api_key: str | None = Field(default=None, description="Notion integration token")
    database_ids: dict[str, str] = Field(
        default_factory=dict, description="Mapping of database names to IDs"
    )


class NotionConfigProvider(BaseConfigProvider):
    """Configuration provider for Notion integration."""

    def __init__(
        self,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
    ) -> None:
        """Initialize the Notion configuration provider.

        Args:
            log_level: Logging level
        """
        super().__init__(log_level=log_level)

    @property
    def name(self) -> str:
        """Name of the configuration provider."""
        return "Notion"

    def get_default_config(self) -> dict[str, Any]:
        """Get default Notion configuration."""
        return {
            "token": "",  # Default to empty, should be set in env or config
            "timeout_ms": 60_000,
            "max_retries": 3,
            "database_ids": {},
        }

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate Notion configuration."""
        has_token = False

        if "token" in config and config["token"]:
            has_token = True
        elif os.environ.get("NOTION_TOKEN"):
            has_token = True

        if not has_token:
            logger.error(
                "Notion token not found in config or NOTION_TOKEN environment variable."
            )
            return False

        return True

    @staticmethod
    def _lookup_dotted_or_direct_key(
        config_data: dict[str, Any], key: str
    ) -> Any | None:  # noqa: ANN401 -- genuinely dynamic: resolves an arbitrary-depth nested config value of unknown shape (str/int/bool/dict/list); matches GitHubConfigProvider's own identical helper
        """
        Resolve a single candidate key against config_data, handling both a
        dotted path (e.g. "integrations.notion") and a direct key. Mirrors
        GitHubConfigProvider._lookup_dotted_or_direct_key exactly (same
        C901-avoidance reason, same behavior).
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

    def _find_notion_config_section(
        self, config_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Look for the Notion config section under the direct/dotted candidate
        keys, then under the "integrations" section as a fallback. Mirrors
        GitHubConfigProvider._find_github_config_section.
        """
        for key in ["notion", "Notion", "integrations.notion", "integrations.Notion"]:
            found = self._lookup_dotted_or_direct_key(config_data, key)
            if found is not None:
                logger.debug(f"Found Notion config using key: {key}")
                found_section: dict[str, Any] = found
                return found_section

        if "integrations" in config_data and isinstance(
            config_data["integrations"], dict
        ):
            for key in ["notion", "Notion"]:
                if key in config_data["integrations"]:
                    logger.debug(
                        f"Found Notion config in integrations section with key: {key}"
                    )
                    integrations_section: dict[str, Any] = config_data["integrations"][
                        key
                    ]
                    return integrations_section

        return None

    def _extract_config(self, config_data: dict[str, Any]) -> dict[str, Any]:
        """Extract Notion-specific configuration from the full config."""
        if config_data is None:
            logger.debug("No config data provided, using defaults")
            default_config = self.get_default_config()
            env_token = os.environ.get("NOTION_TOKEN")
            if env_token:
                default_config["token"] = env_token
                logger.debug("Added token from environment to default config")
            return default_config

        extracted_config = self._find_notion_config_section(config_data)

        if extracted_config is not None and (not extracted_config.get("token")):
            env_token = os.environ.get("NOTION_TOKEN")
            if env_token:
                logger.debug("Adding token from environment to extracted config")
                extracted_config["token"] = env_token
            return extracted_config

        if extracted_config is None and os.environ.get("NOTION_TOKEN"):
            logger.debug("Creating config with token from environment")
            default_config = self.get_default_config()
            default_config["token"] = os.environ.get("NOTION_TOKEN", "")
            return default_config

        if extracted_config is not None:
            return extracted_config

        logger.debug("Falling back to default config extraction")
        return super()._extract_config(config_data)

    def load_config(self, config_path: str | None = None) -> ConfigResult:
        """Load configuration from a file."""
        result = super().load_config(config_path)

        if not result.success or not result.content:
            logger.warning(f"Couldn't load config from {config_path}: {result.error}")
            default_config = self.get_default_config()

            env_token = os.environ.get("NOTION_TOKEN")
            if env_token:
                default_config["token"] = env_token
                logger.debug(
                    "Using Notion token from environment variable in default config"
                )

            return ConfigResult.success_result(
                message="Using default Notion configuration",
                content=default_config,
                config_path=config_path,
            )

        if result.content and "token" in result.content:
            if not result.content["token"]:
                env_token = os.environ.get("NOTION_TOKEN")
                if env_token:
                    result.content["token"] = env_token
                    logger.debug("Using Notion token from environment variable")
        elif result.content:
            env_token = os.environ.get("NOTION_TOKEN")
            if env_token:
                result.content["token"] = env_token
                logger.debug("Added Notion token from environment variable to config")

        return result
