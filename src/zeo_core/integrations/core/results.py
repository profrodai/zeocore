"""
Result models for integration _ops.

This module provides standardized result classes for various integration
_ops, enhancing error handling and return values.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_serializer

T = TypeVar("T")  # Generic type for result content


class IntegrationResult(BaseModel, Generic[T]):
    """Base result for integration _ops."""

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
    """Secret-safe authentication status and metadata.

    Credentials remain owned by the authentication provider and are never
    transported through this broadly serializable result object.
    """

    model_config = ConfigDict(extra="forbid")

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

    @field_serializer("message", "credentials_path", "content")
    def _redact_metadata(self, value: object) -> object:
        """Redact provider metadata on Pydantic serialization paths."""
        return None if value is None else "<redacted>"

    def __repr__(self) -> str:
        """Render status without disclosing provider metadata."""
        return (
            f"AuthResult(success={self.success!r}, message=<redacted>, "
            f"error={self.error!r}, expiry={self.expiry!r}, "
            "credentials_path=<redacted>, content=<redacted>)"
        )

    def __str__(self) -> str:
        """Render status without disclosing provider metadata."""
        return self.__repr__()

    @classmethod
    def success_result(
        cls,
        message: str | None = None,
        expiry: int | None = None,
        credentials_path: str | None = None,
        content: dict | None = None,
    ) -> "AuthResult":
        return cls(
            success=True,
            message=message,
            error=None,
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
            expiry=None,
            credentials_path=None,
            content=None,
        )


class ConfigResult(IntegrationResult[dict]):
    """Result for configuration _ops."""

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
