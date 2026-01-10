# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_http/test_config.py
# role: tests
# neighbors: __init__.py, conftest.py, test_auth.py, test_integration.py, test_jobs.py, test_routes_jobs.py (+2 more)
# exports: test_default_config, test_custom_config, test_invalid_url, test_config_serialization
# git_branch: feat/9-make-setup-work
# git_commit: ccfbaeea
# === QV-LLM:END ===

"""
Tests for HTTP adapter configuration.
"""

import pytest
from pydantic import ValidationError
from quack_core.adapters.http.config import HttpAdapterConfig


def test_default_config():
    """Test default configuration values."""
    config = HttpAdapterConfig()

    assert config.host == "0.0.0.0"
    assert config.port == 8080
    assert config.cors_origins == []
    assert config.auth_token is None
    assert config.hmac_secret is None
    assert config.public_base_url is None
    assert config.job_ttl_seconds == 3600
    assert config.max_workers == 4
    assert config.request_timeout_seconds == 900


def test_custom_config():
    """Test custom configuration values."""
    config = HttpAdapterConfig(
        host="127.0.0.1",
        port=9000,
        cors_origins=["http://localhost:3000"],
        auth_token="secret",
        hmac_secret="hmac-secret",
        public_base_url="https://api.example.com",
        job_ttl_seconds=1800,
        max_workers=8,
        request_timeout_seconds=600
    )

    assert config.host == "127.0.0.1"
    assert config.port == 9000
    assert config.cors_origins == ["http://localhost:3000"]
    assert config.auth_token == "secret"
    assert config.hmac_secret == "hmac-secret"
    assert str(config.public_base_url) == "https://api.example.com/"
    assert config.job_ttl_seconds == 1800
    assert config.max_workers == 8
    assert config.request_timeout_seconds == 600


def test_invalid_url():
    """Test validation of invalid URL."""
    with pytest.raises(ValidationError):
        HttpAdapterConfig(public_base_url="not-a-valid-url")


def test_config_serialization():
    """Test config can be serialized/deserialized."""
    config = HttpAdapterConfig(
        auth_token="test",
        max_workers=2
    )

    # Test model_dump
    data = config.model_dump()
    assert data["auth_token"] == "test"
    assert data["max_workers"] == 2

    # Test reconstruction
    config2 = HttpAdapterConfig(**data)
    assert config2.auth_token == "test"
    assert config2.max_workers == 2
