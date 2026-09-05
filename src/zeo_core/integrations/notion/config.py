"""Secret-safe configuration for the Notion integration."""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field, SecretStr

from zeo_core.core.logging import LOG_LEVELS, LogLevel
from zeo_core.integrations.core import BaseConfigProvider, ConfigResult


class NotionConfig(BaseModel):
    """Compatibility model; credential values redact in every normal rendering."""

    api_key: SecretStr | None = Field(
        default=None, description="Deprecated; prefer NOTION_TOKEN"
    )
    database_ids: dict[str, str] = Field(default_factory=dict)


class NotionConfigProvider(BaseConfigProvider):
    """Load non-secret settings; credential material stays in the environment."""

    def __init__(self, log_level: int = LOG_LEVELS[LogLevel.INFO]) -> None:
        super().__init__(log_level=log_level)

    @property
    def name(self) -> str:
        return "Notion"

    def get_default_config(self) -> dict[str, Any]:
        return {
            "timeout_ms": 60_000,
            "max_retries": 3,
            "database_ids": {},
            "credential_source": "NOTION_TOKEN",
        }

    def validate_config(self, config: dict[str, Any]) -> bool:
        timeout = config.get("timeout_ms", 60_000)
        retries = config.get("max_retries", 3)
        return (
            isinstance(timeout, int)
            and not isinstance(timeout, bool)
            and timeout > 0
            and isinstance(retries, int)
            and not isinstance(retries, bool)
            and retries >= 0
            and bool(os.environ.get("NOTION_TOKEN"))
        )

    def _find_section(self, data: dict[str, Any]) -> dict[str, Any]:
        for key in ("notion", "Notion"):
            value = data.get(key)
            if isinstance(value, dict):
                return value
        integrations = data.get("integrations")
        if isinstance(integrations, dict):
            for key in ("notion", "Notion"):
                value = integrations.get(key)
                if isinstance(value, dict):
                    return value
        return {}

    def _extract_config(self, config_data: dict[str, Any]) -> dict[str, Any]:
        """Merge settings and discard legacy secret-bearing keys."""
        config = self.get_default_config()
        section = self._find_section(config_data or {})
        config.update({key: value for key, value in section.items() if key != "token"})
        return config

    def load_config(self, config_path: str | None = None) -> ConfigResult:
        """Load optional settings; a missing file is valid when env auth exists."""
        try:
            result = super().load_config(config_path)
        except Exception:
            result = ConfigResult.success_result(
                content=self.get_default_config(),
                message="Using default Notion configuration",
                config_path=config_path,
            )
        if not result.success or result.content is None:
            return result
        content = dict(result.content)
        content.pop("token", None)
        content["credential_source"] = "NOTION_TOKEN"
        if not self.validate_config(content):
            return ConfigResult.error_result(
                "Set NOTION_TOKEN and provide positive timeout_ms and max_retries"
            )
        return ConfigResult.success_result(
            content=content,
            message=result.message,
            config_path=result.config_path,
        )
