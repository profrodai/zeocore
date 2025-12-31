# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/core/results.py
# module: quack_core.integrations.core.results
# role: module
# neighbors: __init__.py, protocols.py, registry.py, base.py
# exports: IntegrationResult, AuthResult, ConfigResult, IntegrationLoadReport
# git_branch: refactor/toolkitWorkflow
# git_commit: 5d876e8
# === QV-LLM:END ===

"""
Result models for integration operations.

This module provides standardized result classes for various integration
operations, enhancing error handling and return values.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")  # Generic type for result content


class IntegrationResult(BaseModel, Generic[T]):
    """Base result for integration operations."""

    success: bool = Field(
        default=True,
        description="Whether the operation was successful",
    )

    message: str | None = Field(
        default=None,
        description="Additional message about the operation",
    )

    error: str | None = Field(
        default=None,
        description="Error message if operation failed",
    )

    content: T | None = Field(
        default=None,
        description="Result content if operation was successful",
    )

    @classmethod
    def success_result(
        cls, content: T | None = None, message: str | None = None
    ) -> "IntegrationResult[T]":
        return cls(
            success=True,
            content=content,
            message=message,
            error=None,
        )

    @classmethod
    def error_result(
        cls, error: str, message: str | None = None
    ) -> "IntegrationResult[T]":
        return cls(
            success=False,
            content=None,
            message=message,
            error=error,
        )


class AuthResult(BaseModel):
    """Result for authentication operations."""

    success: bool = Field(
        default=True,
        description="Whether the authentication was successful",
    )

    message: str | None = Field(
        default=None,
        description="Additional message about the authentication",
    )

    error: str | None = Field(
        default=None,
        description="Error message if authentication failed",
    )

    token: str | None = Field(
        default=None,
        description="Authentication token if available",
    )

    expiry: int | None = Field(
        default=None,
        description="Token expiry timestamp",
    )

    credentials_path: str | None = Field(
        default=None,
        description="Path where credentials are stored",
    )

    content: dict | None = Field(
        default=None,
        description="Additional authentication content or metadata",
    )

    @field_validator("token")
    @classmethod
    def _validate_token(cls, v: Any) -> str | None:
        """
        Validate that token is a string if provided.
        Ensures strict serialization and prevents object leakage (e.g. Mocks).
        """
        if v is not None:
            return str(v)
        return None

    @classmethod
    def success_result(
        cls,
        message: str | None = None,
        token: str | None = None,
        expiry: int | None = None,
        credentials_path: str | None = None,
        content: dict | None = None,
    ) -> "AuthResult":
        return cls(
            success=True,
            message=message,
            error=None,
            token=token,
            expiry=expiry,
            credentials_path=credentials_path,
            content=content,
        )

    @classmethod
    def error_result(
        cls,
        error: str,
        message: str | None = None,
    ) -> "AuthResult":
        return cls(
            success=False,
            message=message,
            error=error,
            token=None,
            expiry=None,
            credentials_path=None,
            content=None,
        )


class ConfigResult(IntegrationResult[dict]):
    """Result for configuration operations."""

    config_path: str | None = Field(
        default=None,
        description="Path to the configuration file",
    )

    validation_errors: list[str] | None = Field(
        default=None,
        description="Validation errors if any",
    )

    @classmethod
    def success_result(
        cls,
        content: dict | None = None,
        message: str | None = None,
        config_path: str | None = None,
    ) -> "ConfigResult":
        return cls(
            success=True,
            content=content,
            message=message,
            error=None,
            config_path=config_path,
        )

    @classmethod
    def error_result(
        cls,
        error: str,
        message: str | None = None,
        validation_errors: list[str] | None = None,
    ) -> "ConfigResult":
        return cls(
            success=False,
            content=None,
            message=message,
            error=error,
            validation_errors=validation_errors,
        )


class IntegrationLoadReport(BaseModel):
    """
    Report detailing the results of an explicit integration load operation.
    """

    success: bool = Field(
        ..., description="Overall success status of the load operation"
    )

    loaded: list[str] = Field(
        default_factory=list, description="IDs of successfully loaded integrations"
    )

    skipped: list[str] = Field(
        default_factory=list,
        description="IDs of requested but not found/loaded integrations",
    )

    warnings: list[str] = Field(
        default_factory=list, description="Warning messages encountered during loading"
    )

    errors: list[str] = Field(
        default_factory=list, description="Error messages encountered during loading"
    )
