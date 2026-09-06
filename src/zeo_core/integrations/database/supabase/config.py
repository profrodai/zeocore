"""Secret-safe Supabase integration configuration."""

from __future__ import annotations

import os
from typing import Any

from zeo_core.core.logging import LOG_LEVELS, LogLevel
from zeo_core.integrations.core import BaseConfigProvider, ConfigResult

from .validation import require_identifier, require_project_url


class SupabaseConfigProvider(BaseConfigProvider):
    """Load non-secret settings while keys remain environment-owned."""

    def __init__(self, log_level: int = LOG_LEVELS[LogLevel.INFO]) -> None:
        super().__init__(log_level=log_level)

    @property
    def name(self) -> str:
        return "Supabase"

    def get_default_config(self) -> dict[str, Any]:
        return {
            "schema": "public",
            "timeout_seconds": 30,
            "max_rows": 1_000,
            "max_object_bytes": 10_000_000,
            "allow_local_http": False,
            "allow_privileged_key": False,
            "persist_session": False,
            "auto_refresh_token": False,
        }

    def validate_config(self, config: dict[str, Any]) -> bool:
        try:
            require_project_url(
                os.environ.get("SUPABASE_URL", ""),
                allow_local_http=config.get("allow_local_http") is True,
            )
            require_identifier(str(config.get("schema", "public")), label="schema")
        except ValueError:
            return False
        timeout = config.get("timeout_seconds", 30)
        max_rows = config.get("max_rows", 1_000)
        max_bytes = config.get("max_object_bytes", 10_000_000)
        key_present = bool(
            os.environ.get("SUPABASE_PUBLISHABLE_KEY")
            or os.environ.get("SUPABASE_KEY")
            or (
                config.get("allow_privileged_key") is True
                and os.environ.get("SUPABASE_SECRET_KEY")
            )
        )
        return (
            isinstance(timeout, (int, float))
            and not isinstance(timeout, bool)
            and timeout > 0
            and isinstance(max_rows, int)
            and not isinstance(max_rows, bool)
            and 1 <= max_rows <= 10_000
            and isinstance(max_bytes, int)
            and not isinstance(max_bytes, bool)
            and 1 <= max_bytes <= 100_000_000
            and key_present
        )

    def _extract_config(self, config_data: dict[str, Any]) -> dict[str, Any]:
        config = self.get_default_config()
        section = config_data.get("supabase", {})
        if isinstance(section, dict):
            forbidden = {"key", "secret_key", "service_role_key", "access_token"}
            config.update({k: v for k, v in section.items() if k not in forbidden})
        return config

    def load_config(self, config_path: str | None = None) -> ConfigResult:
        try:
            result = super().load_config(config_path)
        except Exception:
            result = ConfigResult.success_result(
                content=self.get_default_config(),
                message="Using default Supabase configuration",
                config_path=config_path,
            )
        if not result.success or result.content is None:
            return result
        content = dict(result.content)
        for name in ("key", "secret_key", "service_role_key", "access_token"):
            content.pop(name, None)
        if not self.validate_config(content):
            return ConfigResult.error_result(
                "Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY, "
                "and provide valid bounded settings"
            )
        content["credential_source"] = (
            "SUPABASE_SECRET_KEY"
            if content.get("allow_privileged_key") is True
            and os.environ.get("SUPABASE_SECRET_KEY")
            else "SUPABASE_PUBLISHABLE_KEY"
        )
        return ConfigResult.success_result(
            content=content,
            message=result.message,
            config_path=result.config_path,
        )
