"""
Configuration management for Google integrations.

This module provides configuration validation and loading for
Google service integrations, with shared settings for authentication
and service-specific configurations.
"""

import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from zeo_core.config.loader import _normalize_path
from zeo_core.integrations.core.base import BaseConfigProvider
from zeo_core.integrations.google.credential_paths import (
    resolve_client_secret_path,
    resolve_credentials_path,
)


class GoogleBaseConfig(BaseModel):
    """Base configuration model for Google services."""

    client_secrets_file: str = Field(
        ..., description="Path to Google API client secrets file"
    )
    credentials_file: str = Field(
        ..., description="Path where credentials should be stored"
    )

    @field_validator("client_secrets_file")
    @classmethod
    def validate_client_secrets_file(cls, v: str) -> str:
        """Validate that the client secrets path is not empty."""
        if not v or not v.strip():
            raise ValueError("Client secrets file path cannot be empty")
        return v

    @field_validator("credentials_file")
    @classmethod
    def validate_credentials_file(cls, v: str) -> str:
        """Validate that the credentials path is not empty."""
        if not v or not v.strip():
            raise ValueError("Credentials file path cannot be empty")
        return v


class GoogleDriveConfig(GoogleBaseConfig):
    """Configuration model for Google Drive integration."""

    shared_folder_id: str | None = Field(
        None, description="ID of the shared folder for uploads"
    )
    team_drive_id: str | None = Field(
        None, description="Team Drive ID for shared access"
    )
    default_share_access: str = Field(
        "reader", description="Default access level for shared files"
    )
    public_sharing: bool = Field(
        True, description="Whether to enable public sharing of files"
    )


class GoogleMailConfig(GoogleBaseConfig):
    """Configuration model for Google Mail integration."""

    gmail_labels: list[str] = Field(
        default_factory=list, description="Labels to filter emails"
    )
    gmail_days_back: int = Field(
        default=7, description="Number of days to look back for emails"
    )
    gmail_user_id: str = Field(default="me", description="User ID to use for Gmail API")


class GoogleCalendarConfig(GoogleBaseConfig):
    """Configuration model for Google Calendar integration."""

    calendar_id: str = Field(
        default="primary", description="Default calendar ID to operate against"
    )
    max_results: int = Field(
        default=250, description="Default page size for event list queries"
    )
    time_zone: str | None = Field(
        default=None,
        description="Default IANA time zone for events created without one",
    )


class GoogleDocsConfig(GoogleBaseConfig):
    """Configuration model for Google Docs integration."""

    document_id: str | None = Field(
        default=None,
        description="Default document ID to operate against, if any",
    )


class GoogleSheetsConfig(GoogleBaseConfig):
    """Configuration model for Google Sheets integration."""

    spreadsheet_id: str | None = Field(
        default=None,
        description="Default spreadsheet ID to operate against, if any",
    )


class GoogleSlidesConfig(GoogleBaseConfig):
    """Configuration model for Google Slides integration."""

    presentation_id: str | None = Field(
        default=None,
        description="Default presentation ID to operate against, if any",
    )


class GoogleConfigProvider(BaseConfigProvider):
    """Configuration provider for Google integrations."""

    ENV_PREFIX = "ZEO_GOOGLE_"
    DEFAULT_CONFIG_LOCATIONS = [
        "./config/google_config.yaml",
        "./config/zeo_config.yaml",
        "./zeo_config.yaml",
        "~/.zeo/config.yaml",
    ]

    def __init__(self, service: str = "drive", log_level: int = logging.INFO) -> None:
        """
        Initialize the Google configuration provider.

        Args:
            service: Google service name (e.g., 'drive', 'mail')
            log_level: Logging level
        """
        super().__init__(log_level)
        self.service = service.lower()
        self._config_models = {
            "drive": GoogleDriveConfig,
            "mail": GoogleMailConfig,
            "calendar": GoogleCalendarConfig,
            "docs": GoogleDocsConfig,
            "sheets": GoogleSheetsConfig,
            "slides": GoogleSlidesConfig,
        }

    @property
    def name(self) -> str:
        """Get the name of the configuration provider."""
        return f"Google{self.service.capitalize()}"

    def _apply_nested_integrations_google(
        self, config_data: dict[str, Any], result_config: dict[str, Any]
    ) -> bool:
        """
        Phase 1 of _extract_config: nested integrations.google structure
        (shared settings, then service-specific override). Extracted to keep
        _extract_config's own branch count under the C901 threshold;
        behavior/order unchanged from the original inline block. Returns
        True if this phase found and applied any config.
        """
        if (
            "integrations" not in config_data
            or "google" not in config_data["integrations"]
        ):
            return False

        base_google_config = config_data["integrations"]["google"]
        # Start with the shared Google configuration
        result_config.update(base_google_config)

        # Look for service-specific settings inside integrations.google.<service>
        service_specific = base_google_config.get(self.service, {})
        if service_specific and isinstance(service_specific, dict):
            # Override shared settings with service-specific ones
            result_config.update(service_specific)

        return True

    def _apply_direct_service_key(
        self, config_data: dict[str, Any], result_config: dict[str, Any]
    ) -> bool:
        """
        Phase 2 of _extract_config: direct google_<service> section.
        Extracted for the same C901 reason as
        _apply_nested_integrations_google.
        """
        service_key = f"google_{self.service}"
        if service_key not in config_data:
            return False
        result_config.update(config_data[service_key])
        return True

    def _apply_top_level_google_section(
        self, config_data: dict[str, Any], result_config: dict[str, Any]
    ) -> bool:
        """
        Phase 3 of _extract_config: top-level google section, plus its
        service-specific subkey. Extracted for the same C901 reason as
        _apply_nested_integrations_google.
        """
        if "google" not in config_data:
            return False

        google_config = config_data["google"]

        # Extract any shared Google settings not already in result_config
        for key, value in google_config.items():
            if key not in result_config and key != "mail" and key != "drive":
                result_config[key] = value

        # Look for service-specific subkey (e.g., google.drive or google.mail)
        if self.service in google_config:
            service_config = google_config[self.service]
            if isinstance(service_config, dict):
                # Override with service-specific settings
                result_config.update(service_config)

        return True

    def _extract_config(self, config_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract Google service configuration from the full config data.

        Handles both shared Google settings and service-specific configuration
        for services like Drive and Mail.

        Args:
            config_data: Full configuration data

        Returns:
            dict[str, Any]: Google service-specific configuration
        """
        result_config: dict[str, Any] = {}

        found_nested = self._apply_nested_integrations_google(
            config_data, result_config
        )
        found_direct = self._apply_direct_service_key(config_data, result_config)
        found_top_level = self._apply_top_level_google_section(
            config_data, result_config
        )
        found_config = found_nested or found_direct or found_top_level

        # If no configuration was found at all, return an empty dict
        # This matches the expectation in the test case
        if not found_config:
            return {}

        # Ensure we have the required fields, or use defaults
        if not self._ensure_required_fields(result_config):
            default_config = self.get_default_config()

            # Only add defaults for missing fields
            for key, value in default_config.items():
                if key not in result_config:
                    result_config[key] = value

        # Add service-specific defaults if needed
        self._add_service_specific_defaults(result_config)

        return result_config

    def _add_service_specific_defaults(self, config: dict[str, Any]) -> None:
        """
        Add service-specific default settings if they're missing.

        Args:
            config: Configuration dictionary to enhance
        """
        if self.service == "drive":
            defaults: dict[str, str | bool | int | list[str] | None] = {
                "shared_folder_id": None,
                "team_drive_id": None,
                "default_share_access": "reader",
                "public_sharing": True,
            }
        elif self.service == "mail":
            defaults = {
                "gmail_labels": [],
                "gmail_days_back": 7,
                "gmail_user_id": "me",
                "storage_path": "output/gmail",
                "include_subject": False,
                "include_sender": False,
            }
        elif self.service == "calendar":
            defaults = {
                "calendar_id": "primary",
                "max_results": 250,
                "time_zone": None,
            }
        elif self.service == "docs":
            defaults = {
                "document_id": None,
            }
        elif self.service == "sheets":
            defaults = {
                "spreadsheet_id": None,
            }
        elif self.service == "slides":
            defaults = {
                "presentation_id": None,
            }
        else:
            return

        # Only add defaults for missing keys
        for key, value in defaults.items():
            if key not in config:
                config[key] = value

    def _ensure_required_fields(self, config: dict[str, Any]) -> bool:
        """
        Ensure that the configuration has the required fields.

        Args:
            config: Configuration dictionary to check

        Returns:
            bool: True if the configuration has all required fields
        """
        required_fields = ["client_secrets_file", "credentials_file"]
        return all(field in config for field in required_fields)

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate Google service configuration using Pydantic models.

        Args:
            config: Configuration data to validate

        Returns:
            bool: True if configuration is valid
        """
        try:
            config_model = self._config_models.get(self.service, GoogleBaseConfig)

            # Call the constructor with **config to expand it as keyword arguments
            # This ensures the mock's side effect is triggered in tests
            config_model(**config)
            return True
        except ValidationError as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error during configuration validation: {e}")
            return False

    def get_default_config(self) -> dict[str, Any]:
        """
        Get default configuration values for Google services.

        The two file paths run through the RULING-407/408 one-shot credential
        migration (credential_paths.resolve_*): the pre-migration defaults
        (`config/google_*.json`) resolved CWD-relative, so authorizing from a
        fresh directory silently wrote a live OAuth token wherever the caller
        happened to be standing. The migrated defaults are OS-appropriate
        per-user paths (platformdirs); a pre-existing token at the OLD
        location is moved there explicitly (never silently -- a notice is
        printed) the first time this runs and nothing needs migrating on
        every call after. See credential_paths.py for the full contract,
        including the refuse-and-instruct behavior on ambiguity
        (CredentialMigrationAmbiguousError) when a differing credential exists at
        both locations.

        Returns:
            dict[str, Any]: Default configuration values

        Raises:
            CredentialMigrationAmbiguousError: a credential exists at BOTH the
                legacy and the new location with differing contents.
                RULING-408 ruled this must never be guessed at -- the caller
                is expected to resolve it by hand and is told both paths.
        """
        base_config = {
            "client_secrets_file": resolve_client_secret_path(),
            "credentials_file": resolve_credentials_path(),
        }

        if self.service == "drive":
            return {
                **base_config,
                "shared_folder_id": None,
                "team_drive_id": None,
                "default_share_access": "reader",
                "public_sharing": True,
            }
        elif self.service == "mail":
            return {
                **base_config,
                "gmail_labels": [],
                "gmail_days_back": 7,
                "gmail_user_id": "me",
            }
        elif self.service == "calendar":
            return {
                **base_config,
                "calendar_id": "primary",
                "max_results": 250,
                "time_zone": None,
            }
        elif self.service == "docs":
            return {
                **base_config,
                "document_id": None,
            }
        elif self.service == "sheets":
            return {
                **base_config,
                "spreadsheet_id": None,
            }
        elif self.service == "slides":
            return {
                **base_config,
                "presentation_id": None,
            }

        return base_config

    def resolve_config_paths(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Resolve relative paths in configuration to absolute paths.

        Args:
            config: Configuration with potentially relative paths

        Returns:
            dict[str, Any]: Configuration with resolved paths
        """
        from zeo_core.core.paths import service as paths_module

        # resolve_project_path is a PathService INSTANCE method, not a
        # module-level free function (the module never had free functions --
        # see the sibling test_paths chain's own conftest note, which
        # established this same fact for core/paths/_internal callers).
        path_service = paths_module.PathService()

        resolved_config = config.copy()

        # Resolve paths
        for key in ["client_secrets_file", "credentials_file"]:
            if key in resolved_config and resolved_config[key]:
                try:
                    result = path_service.resolve_project_path(resolved_config[key])
                    if isinstance(result, str):
                        # Some callers (e.g. mocked in tests) may return a
                        # bare string rather than a PathResult; accept both.
                        resolved_config[key] = result
                    elif getattr(result, "success", False):
                        resolved_config[key] = str(result.path)
                    else:
                        self.logger.warning(
                            f"Could not resolve path for {key}: "
                            f"{getattr(result, 'error', 'unknown error')}"
                        )
                except Exception as e:
                    self.logger.warning(f"Could not resolve path for {key}: {e}")

        return resolved_config


class GoogleConfig(BaseModel):
    """Configuration for Google integrations."""

    client_secrets_file: str | None = Field(
        default=None, description="Path to client secrets file for OAuth"
    )
    credentials_file: str | None = Field(
        default=None, description="Path to credentials file for OAuth"
    )
    shared_folder_id: str | None = Field(
        default=None, description="Google Drive shared folder ID"
    )
    gmail_labels: list[str] = Field(
        default_factory=list, description="Gmail labels to filter"
    )
    gmail_days_back: int = Field(
        default=1, description="Number of days back for Gmail queries"
    )

    @field_validator("client_secrets_file", "credentials_file", mode="before")
    @classmethod
    def normalize_google_paths(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _normalize_path(v)
