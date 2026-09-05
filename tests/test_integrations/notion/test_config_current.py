"""Secret-safe Notion configuration behavior."""

import os
from unittest.mock import patch

from pydantic import SecretStr

from zeo_core.integrations.notion.config import NotionConfig, NotionConfigProvider


def test_compatibility_model_redacts_api_key() -> None:
    canary = "ntn_LIVE_CANARY"
    config = NotionConfig(api_key=canary, database_ids={"tasks": "db-1"})

    assert isinstance(config.api_key, SecretStr)
    assert canary not in repr(config)
    assert canary not in str(config)
    assert canary not in config.model_dump_json()


def test_default_config_contains_no_secret_field() -> None:
    config = NotionConfigProvider().get_default_config()

    assert "token" not in config
    assert "api_key" not in config
    assert config["credential_source"] == "NOTION_TOKEN"


def test_nested_settings_load_but_legacy_token_is_discarded() -> None:
    provider = NotionConfigProvider()
    canary = "ntn_LIVE_CANARY"

    config = provider._extract_config(
        {
            "integrations": {
                "notion": {
                    "token": canary,
                    "timeout_ms": 12_000,
                    "max_retries": 5,
                }
            }
        }
    )

    assert config["timeout_ms"] == 12_000
    assert config["max_retries"] == 5
    assert canary not in repr(config)
    assert "token" not in config


def test_validate_requires_environment_credential_and_sane_bounds() -> None:
    provider = NotionConfigProvider()
    config = provider.get_default_config()

    with patch.dict(os.environ, {}, clear=True):
        assert provider.validate_config(config) is False
    with patch.dict(os.environ, {"NOTION_TOKEN": "test-only"}):
        assert provider.validate_config(config) is True
        assert provider.validate_config({**config, "timeout_ms": 0}) is False
        assert provider.validate_config({**config, "max_retries": -1}) is False


def test_missing_config_file_uses_defaults_without_copying_env_secret() -> None:
    provider = NotionConfigProvider()
    canary = "ntn_LIVE_CANARY"

    with patch.dict(os.environ, {"NOTION_TOKEN": canary}):
        result = provider.load_config("does-not-exist.yaml")

    assert result.success is True
    assert result.content is not None
    assert result.content["credential_source"] == "NOTION_TOKEN"
    assert canary not in repr(result)
    assert canary not in result.model_dump_json()
