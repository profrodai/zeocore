# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/mail/service.py
# module: quack_core.integrations.google.mail.service
# role: service
# neighbors: __init__.py, protocols.py, config.py
# exports: GoogleMailService
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
# === QV-LLM:END ===

import logging
from collections.abc import Iterable, Mapping, Sequence
from types import NoneType
from typing import cast

from quack_core.integrations.core.base import BaseIntegrationService
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.google.auth import GoogleAuthProvider
from quack_core.integrations.google.config import GoogleConfigProvider
from quack_core.integrations.google.mail.config import GmailServiceConfig
from quack_core.integrations.google.mail.operations import auth, email
from quack_core.integrations.google.mail.protocols import (
    GmailService,
    GoogleCredentials,
)
from quack_core.lib.errors import QuackIntegrationError
from quack_core.lib.fs import service as fs
from quack_core.lib.paths import service as paths


class GoogleMailService(BaseIntegrationService):
    """Integration service for Google Mail (Gmail)."""

    def __init__(
        self,
        client_secrets_file: str | None = None,
        credentials_file: str | None = None,
        config_path: str | None = None,
        storage_path: str | None = None,
        oauth_scope: list[str] | Sequence[str] | None = None,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        include_subject: bool = False,
        include_sender: bool = False,
        log_level: int = logging.INFO,
    ) -> None:
        """
        Initialize the Google Mail integration service.

        Args:
            client_secrets_file: Path to the client secrets file.
            credentials_file: Path to the credentials file.
            config_path: Path to the configuration file.
            storage_path: Path where downloaded emails will be stored.
            oauth_scope: OAuth scopes for the Gmail API.
            max_retries: Maximum number of retries for API calls.
            initial_delay: Initial delay in seconds before the first retry.
            max_delay: Maximum delay in seconds before any retry.
            include_subject: Whether to include the email subject in the output HTML.
            include_sender: Whether to include the sender in the output HTML.
            log_level: Logging level.
        """
        config_provider = GoogleConfigProvider("mail", log_level)
        super().__init__(
            config_provider=config_provider,
            auth_provider=None,
            config=None,
            config_path=config_path,
            log_level=log_level)

        # If explicit parameters are provided, override configuration from file.
        self.custom_config: dict[str, object] = {}
        if client_secrets_file and credentials_file:
            self.custom_config = {
                "client_secrets_file": client_secrets_file,
                "credentials_file": credentials_file,
                "storage_path": storage_path,
                "oauth_scope": oauth_scope,
                "max_retries": max_retries,
                "initial_delay": initial_delay,
                "max_delay": max_delay,
                "include_subject": include_subject,
                "include_sender": include_sender,
            }

        self.storage_path: str | None = storage_path
        self.oauth_scope: list[str] = (
            list(oauth_scope)
            if oauth_scope is not None
            else ["https://www.googleapis.com/auth/gmail.readonly"]
        )
        self.max_retries: int = max_retries
        self.initial_delay: float = initial_delay
        self.max_delay: float = max_delay
        self.include_subject: bool = include_subject
        self.include_sender: bool = include_sender

        self.auth_provider: GoogleAuthProvider | None = None
        self.gmail_service: GmailService | None = None
        self.config: dict[str, object] = {}

    @property
    def name(self) -> str:
        """Get the name of the integration."""
        return "GoogleMail"

    @property
    def version(self) -> str:
        """Get the version of the integration."""
        return "1.0.0"

    def initialize(self) -> IntegrationResult[NoneType]:
        """
        Initialize the Google Mail service.

        Returns:
            IntegrationResult indicating success or failure.
        """
        init_result: IntegrationResult[NoneType] = super().initialize()
        if not init_result.success:
            return init_result

        try:
            config: dict[str, object] | None = self._initialize_config()
            if config is None:
                self._initialized = False
                return IntegrationResult.error_result(
                    "Failed to initialize configuration"
                )

            # Create auth provider with proper type casting
            client_secrets_file: str = str(config["client_secrets_file"])
            credentials_file_value: object = config.get("credentials_file")
            credentials_file: str | None = (
                str(credentials_file_value)
                if credentials_file_value is not None
                else None
            )

            self.auth_provider = GoogleAuthProvider(
                client_secrets_file=client_secrets_file,
                credentials_file=credentials_file,
                scopes=self.oauth_scope,
                log_level=self.log_level,
            )

            # Authenticate and build the Gmail API service
            credentials = self.auth_provider.get_credentials()
            self.gmail_service = auth.initialize_gmail_service(
                cast(GoogleCredentials, credentials)
            )

            self._initialized = True
            return IntegrationResult.success_result(
                message="Google Mail service initialized successfully"
            )
        except Exception as e:
            self._initialized = False
            self.logger.error(f"Failed to initialize Google Mail service: {e}")
            return IntegrationResult.error_result(
                f"Failed to initialize Google Mail service: {e}"
            )

    def _initialize_config(self) -> dict[str, object] | None:
        """
        Initialize configuration from parameters or config file.

        Returns:
            The initialized configuration or None if failed.

        Raises:
            QuackIntegrationError: If configuration
            initialization fails in expected ways.
        """
        try:
            if self.custom_config:
                self.config = self.custom_config
            else:
                config_result = self.config_provider.load_config(self.config_path)
                if not config_result.success or not config_result.content:
                    raise QuackIntegrationError(
                        "Failed to load configuration from file", {}
                    )
                self.config = config_result.content

            # Ensure storage_path is defined and exists
            if not self.storage_path:
                storage_path_value: object = self.config.get("storage_path")
                if isinstance(storage_path_value, str):
                    self.storage_path = storage_path_value

            if not self.storage_path:
                raise QuackIntegrationError(
                    "Storage path not specified in configuration", {}
                )

            # Resolve the storage path
            storage_path_obj = paths.resolve_project_path(self.storage_path)
            self.storage_path = str(storage_path_obj)

            create_result = fs.create_directory(storage_path_obj, exist_ok=True)
            if not create_result.success:
                self.logger.warning(
                    f"Could not create storage directory: {create_result.error}. "
                    f"This is expected in test environments."
                )

            # Validate and convert configuration values
            self._validate_and_convert_config()
            return self.config
        except QuackIntegrationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize configuration: {e}")
            return None

    def list_emails(self, query: str | None = None) -> IntegrationResult[list[Mapping]]:
        """
        List emails matching the provided query.

        Args:
            query: Gmail search query string. If not provided, a default query is built
                   using the configured parameters.

        Returns:
            IntegrationResult containing a list of email message dicts.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            if query is None:
                days_back_value: object = self.config.get("gmail_days_back", 7)
                days_back: int = self._safe_cast_int(days_back_value, 7)

                labels_value: object = self.config.get("gmail_labels", [])
                labels: list[str] | None = self._convert_to_string_list(labels_value)

                query = email.build_query(days_back, labels)

            user_id_value: object = self.config.get("gmail_user_id", "me")
            user_id: str = str(user_id_value) if user_id_value is not None else "me"

            if self.gmail_service is None:
                return IntegrationResult.error_result(
                    "Gmail service is not initialized"
                )

            return email.list_emails(self.gmail_service, user_id, query, self.logger)
        except Exception as e:
            self.logger.error(f"Failed to list emails: {e}")
            return IntegrationResult.error_result(f"Failed to list emails: {e}")

    def download_email(self, msg_id: str) -> IntegrationResult[str]:
        """
        Download a Gmail message and save it as an HTML file.

        Args:
            msg_id: The Gmail message ID.

        Returns:
            IntegrationResult containing the file path of the downloaded email.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            user_id_value: object = self.config.get("gmail_user_id", "me")
            user_id: str = str(user_id_value) if user_id_value is not None else "me"

            include_subject_value: object = self.config.get(
                "include_subject", self.include_subject
            )
            include_subject: bool = bool(include_subject_value)

            include_sender_value: object = self.config.get(
                "include_sender", self.include_sender
            )
            include_sender: bool = bool(include_sender_value)

            max_retries_value: object = self.config.get("max_retries", self.max_retries)
            max_retries: int = self._safe_cast_int(max_retries_value, self.max_retries)

            initial_delay_value: object = self.config.get(
                "initial_delay", self.initial_delay
            )
            initial_delay: float = self._safe_cast_float(
                initial_delay_value, self.initial_delay
            )

            max_delay_value: object = self.config.get("max_delay", self.max_delay)
            max_delay: float = self._safe_cast_float(max_delay_value, self.max_delay)

            if self.gmail_service is None or self.storage_path is None:
                return IntegrationResult.error_result(
                    "Gmail service or storage path not initialized"
                )

            return email.download_email(
                self.gmail_service,
                user_id,
                msg_id,
                self.storage_path,
                include_subject,
                include_sender,
                max_retries,
                initial_delay,
                max_delay,
                self.logger,
            )
        except Exception as e:
            self.logger.error(f"Failed to download email {msg_id}: {e}")
            return IntegrationResult.error_result(
                f"Failed to download email {msg_id}: {e}"
            )

    def _validate_and_convert_config(self) -> None:
        """
        Validate configuration values and convert them to the appropriate types.

        This method converts known configuration fields to the expected types.
        """
        # Convert required string fields.
        for key in ("client_secrets_file", "credentials_file"):
            if key in self.config and self.config[key] is not None:
                self.config[key] = str(self.config[key])

        # Convert integer fields.
        for key in ("max_retries", "gmail_days_back"):
            if key in self.config:
                self.config[key] = self._safe_cast_int(self.config[key], 0)

        # Convert float fields.
        for key in ("initial_delay", "max_delay"):
            if key in self.config:
                self.config[key] = self._safe_cast_float(self.config[key], 0.0)

        # Convert boolean fields.
        for key in ("include_subject", "include_sender"):
            if key in self.config:
                self.config[key] = bool(self.config[key])

        # Convert list fields.
        if "gmail_labels" in self.config:
            self.config["gmail_labels"] = self._convert_to_string_list(
                self.config["gmail_labels"]
            )

    def _safe_cast_int(self, value: object, default: int) -> int:
        """
        Safely cast a value to int, returning a default if the cast fails.

        Args:
            value: Value to cast to int.
            default: Default value to return if casting fails.

        Returns:
            The value as an int, or the default if casting fails.
        """
        if isinstance(value, int):
            return value
        try:
            if value is not None:
                return int(value)  # type: ignore
        except (ValueError, TypeError):
            pass
        return default

    def _safe_cast_float(self, value: object, default: float) -> float:
        """
        Safely cast a value to float, returning a default if the cast fails.

        Args:
            value: Value to cast to float.
            default: Default value to return if casting fails.

        Returns:
            The value as a float, or the default if casting fails.
        """
        if isinstance(value, float):
            return value
        if isinstance(value, int):
            return float(value)
        try:
            if value is not None:
                return float(value)  # type: ignore
        except (ValueError, TypeError):
            pass
        return default

    def _convert_to_string_list(self, value: object) -> list[str] | None:
        """
        Convert a value to a list of strings if possible.

        Args:
            value: Value to convert to a list of strings.

        Returns:
            A list of strings, or None if the conversion fails.
        """
        if value is None:
            return None

        if isinstance(value, list):
            return [str(item) for item in value if item is not None]

        if isinstance(value, Iterable) and not isinstance(value, str | bytes):
            return [str(item) for item in value if item is not None]

        return None

    def validate_config(self, config: dict[str, object]) -> tuple[bool, list[str]]:
        """
        Validate the service configuration.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            Tuple of (is_valid, list of error messages).
        """
        errors: list[str] = []

        try:
            # Use pydantic model for validation.
            GmailServiceConfig(**config)
            return True, []
        except Exception as e:
            errors.append(f"Configuration validation failed: {e}")
            return False, errors
