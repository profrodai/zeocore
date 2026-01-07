# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/core/test_results.py
# role: tests
# neighbors: __init__.py, test_get_service.py, test_protocol_inheritance.py, test_protocols.py, test_registry.py, test_registry_discovery.py
# exports: TestIntegrationResult, TestAuthResult, TestConfigResult
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

"""
Tests for the integration result classes.
"""

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from quack_core.integrations.core.results import (
    AuthResult,
    ConfigResult,
    IntegrationResult,
)


class TestIntegrationResult:
    """Tests for the IntegrationResult class."""

    def test_basic_result(self) -> None:
        """Test creating a basic success result."""
        result = IntegrationResult(success=True, message="Operation succeeded")

        assert result.success is True
        assert result.message == "Operation succeeded"
        assert result.error is None
        assert result.content is None

    def test_error_result(self) -> None:
        """Test creating a basic error result."""
        result = IntegrationResult(
            success=False, error="Operation failed", message="Additional info"
        )

        assert result.success is False
        assert result.message == "Additional info"
        assert result.error == "Operation failed"
        assert result.content is None

    def test_result_with_content(self) -> None:
        """Test creating a result with content."""
        content = {"key": "value"}
        result = IntegrationResult[dict](
            success=True, message="Operation succeeded", content=content
        )

        assert result.success is True
        assert result.content == content

    def test_success_result_factory(self) -> None:
        """Test the success_result factory method."""
        content = "test content"
        result = IntegrationResult.success_result(content, "Success message")

        assert result.success is True
        assert result.message == "Success message"
        assert result.content == content
        assert result.error is None

        # Test without optional parameters
        result = IntegrationResult.success_result()
        assert result.success is True
        assert result.content is None
        assert result.message is None
        assert result.error is None

    def test_error_result_factory(self) -> None:
        """Test the error_result factory method."""
        result = IntegrationResult.error_result("Error message", "Additional info")

        assert result.success is False
        assert result.message == "Additional info"
        assert result.error == "Error message"
        assert result.content is None

        # Test without optional parameters
        result = IntegrationResult.error_result("Error message")
        assert result.success is False
        assert result.error == "Error message"
        assert result.message is None
        assert result.content is None

    @given(
        success=st.booleans(),
        message=st.one_of(st.none(), st.text()),
        error=st.one_of(st.none(), st.text()),
        content=st.one_of(
            st.none(), st.integers(), st.text(), st.dictionaries(st.text(), st.text())
        ),
    )
    def test_integration_result_properties(
        self, success: bool, message: str | None, error: str | None, content: Any
    ) -> None:
        """Test IntegrationResult properties with hypothesis generated values."""
        if not success and error is None:
            error = "Default error"  # Ensure error is not None for failed results

        if success and error is not None:
            # Skip invalid combinations: success=True with error
            return

        result = IntegrationResult(
            success=success, message=message, error=error, content=content
        )

        assert result.success is success
        assert result.message == message
        assert result.error == error
        assert result.content == content


class TestAuthResult:
    """Tests for the AuthResult class."""

    def test_basic_auth_result(self) -> None:
        """Test creating a basic authentication result."""
        result = AuthResult(success=True, message="Authentication succeeded")

        assert result.success is True
        assert result.message == "Authentication succeeded"
        assert result.error is None
        assert result.token is None
        assert result.expiry is None
        assert result.credentials_path is None
        assert result.content is None

    def test_complete_auth_result(self) -> None:
        """Test creating a complete authentication result."""
        token = "test_token"
        expiry = 1234567890
        credentials_path = "/path/to/credentials"
        content = {"user_id": "test_user"}

        result = AuthResult(
            success=True,
            message="Authentication succeeded",
            token=token,
            expiry=expiry,
            credentials_path=credentials_path,
            content=content,
        )

        assert result.success is True
        assert result.token == token
        assert result.expiry == expiry
        assert result.credentials_path == credentials_path
        assert result.content == content

    def test_auth_success_result_factory(self) -> None:
        """Test the success_result factory method for AuthResult."""
        token = "test_token"
        expiry = 1234567890
        credentials_path = "/path/to/credentials"
        content = {"user_id": "test_user"}

        result = AuthResult.success_result(
            message="Success",
            token=token,
            expiry=expiry,
            credentials_path=credentials_path,
            content=content,
        )

        assert result.success is True
        assert result.message == "Success"
        assert result.token == token
        assert result.expiry == expiry
        assert result.credentials_path == credentials_path
        assert result.content == content
        assert result.error is None

        # Test with minimal parameters
        result = AuthResult.success_result()
        assert result.success is True
        assert result.token is None
        assert result.expiry is None
        assert result.credentials_path is None
        assert result.content is None

    def test_auth_error_result_factory(self) -> None:
        """Test the error_result factory method for AuthResult."""
        result = AuthResult.error_result("Auth failed", "Additional info")

        assert result.success is False
        assert result.message == "Additional info"
        assert result.error == "Auth failed"
        assert result.token is None
        assert result.expiry is None
        assert result.credentials_path is None
        assert result.content is None

        # Test with minimal parameters
        result = AuthResult.error_result("Auth failed")
        assert result.success is False
        assert result.error == "Auth failed"
        assert result.message is None

    @given(
        token=st.one_of(st.none(), st.text()),
        expiry=st.one_of(st.none(), st.integers()),
        credentials_path=st.one_of(st.none(), st.text()),
        content=st.one_of(st.none(), st.dictionaries(st.text(), st.text())),
    )
    def test_auth_result_properties(
        self,
        token: str | None,
        expiry: int | None,
        credentials_path: str | None,
        content: dict | None,
    ) -> None:
        """Test AuthResult properties with hypothesis generated values."""
        result = AuthResult(
            success=True,
            token=token,
            expiry=expiry,
            credentials_path=credentials_path,
            content=content,
        )

        assert result.token == token
        assert result.expiry == expiry
        assert result.credentials_path == credentials_path
        assert result.content == content


class TestConfigResult:
    """Tests for the ConfigResult class."""

    def test_basic_config_result(self) -> None:
        """Test creating a basic configuration result."""
        result = ConfigResult(success=True, message="Config loaded")

        assert result.success is True
        assert result.message == "Config loaded"
        assert result.error is None
        assert result.content is None
        assert result.config_path is None
        assert result.validation_errors is None

    def test_complete_config_result(self) -> None:
        """Test creating a complete configuration result."""
        content = {"setting": "value"}
        config_path = "/path/to/config.yaml"
        validation_errors = ["Invalid setting"]

        result = ConfigResult(
            success=False,
            message="Config invalid",
            error="Validation failed",
            content=content,
            config_path=config_path,
            validation_errors=validation_errors,
        )

        assert result.success is False
        assert result.message == "Config invalid"
        assert result.error == "Validation failed"
        assert result.content == content
        assert result.config_path == config_path
        assert result.validation_errors == validation_errors

    def test_config_success_result_factory(self) -> None:
        """Test the success_result factory method for ConfigResult."""
        content = {"setting": "value"}
        config_path = "/path/to/config.yaml"

        result = ConfigResult.success_result(
            content=content, message="Success", config_path=config_path
        )

        assert result.success is True
        assert result.message == "Success"
        assert result.content == content
        assert result.config_path == config_path
        assert result.error is None
        assert result.validation_errors is None

        # Test with minimal parameters
        result = ConfigResult.success_result()
        assert result.success is True
        assert result.content is None
        assert result.config_path is None

    def test_config_error_result_factory(self) -> None:
        """Test the error_result factory method for ConfigResult."""
        validation_errors = ["Invalid setting"]

        result = ConfigResult.error_result(
            "Config error", "Additional info", validation_errors
        )

        assert result.success is False
        assert result.message == "Additional info"
        assert result.error == "Config error"
        assert result.content is None
        assert result.validation_errors == validation_errors

        # Test with minimal parameters
        result = ConfigResult.error_result("Config error")
        assert result.success is False
        assert result.error == "Config error"
        assert result.message is None
        assert result.validation_errors is None

    @given(
        config_path=st.one_of(st.none(), st.text()),
        validation_errors=st.one_of(st.none(), st.lists(st.text())),
    )
    def test_config_result_properties(
        self, config_path: str | None, validation_errors: list[str] | None
    ) -> None:
        """Test ConfigResult properties with hypothesis generated values."""
        result = ConfigResult(
            success=True,
            config_path=config_path,
            validation_errors=validation_errors,
        )

        assert result.config_path == config_path
        assert result.validation_errors == validation_errors

    def test_invalid_validation_errors(self) -> None:
        """Test validation error when providing non-list validation errors."""
        # This will raise a validation error since validation_errors should be a list
        with pytest.raises(ValidationError):
            ConfigResult(success=True, validation_errors="not a list")  # type: ignore
