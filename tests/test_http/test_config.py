"""
Tests for HTTP adapter configuration.
"""

import pytest
from pydantic import ValidationError
from zeo_core.adapters.http.config import HttpAdapterConfig


def test_default_config() -> None:
    """Test default configuration values."""
    config = HttpAdapterConfig()

    assert config.host == "0.0.0.0"  # noqa: S104 -- asserting the class's own documented default, no real uvicorn bind occurs in this test
    assert config.port == 8080
    assert config.cors_origins == []
    assert config.auth_token is None
    assert config.hmac_secret is None
    assert config.public_base_url is None
    assert config.job_ttl_seconds == 3600
    assert config.max_workers == 4
    assert config.request_timeout_seconds == 900


def test_custom_config() -> None:
    """Test custom configuration values."""
    config = HttpAdapterConfig(
        host="127.0.0.1",
        port=9000,
        cors_origins=["http://localhost:3000"],
        auth_token="secret",  # noqa: S106 -- test fixture, fake credential value, not a real secret
        hmac_secret="hmac-secret",  # noqa: S106 -- test fixture, fake credential value, not a real secret
        public_base_url="https://api.example.com",
        job_ttl_seconds=1800,
        max_workers=8,
        request_timeout_seconds=600,
    )

    assert config.host == "127.0.0.1"
    assert config.port == 9000
    assert config.cors_origins == ["http://localhost:3000"]
    assert config.auth_token == "secret"  # noqa: S105 -- test fixture, fake credential value, not a real secret
    assert config.hmac_secret == "hmac-secret"  # noqa: S105 -- test fixture, fake credential value, not a real secret
    assert str(config.public_base_url) == "https://api.example.com/"
    assert config.job_ttl_seconds == 1800
    assert config.max_workers == 8
    assert config.request_timeout_seconds == 600


def test_invalid_url() -> None:
    """Test validation of invalid URL."""
    with pytest.raises(ValidationError):
        HttpAdapterConfig(public_base_url="not-a-valid-url")


def test_config_serialization() -> None:
    """Test config can be serialized/deserialized."""
    config = HttpAdapterConfig(auth_token="test", max_workers=2)  # noqa: S106 -- test fixture, fake credential value, not a real secret

    # Test model_dump
    data = config.model_dump()
    assert data["auth_token"] == "test"  # noqa: S105 -- test fixture, fake credential value, not a real secret
    assert data["max_workers"] == 2

    # Test reconstruction
    config2 = HttpAdapterConfig(**data)
    assert config2.auth_token == "test"  # noqa: S105 -- test fixture, fake credential value, not a real secret
    assert config2.max_workers == 2
