# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/mail/test_mail_service.py
# === QV-LLM:END ===

"""
Tests for Google Mail service.

This module tests the main service class for Google Mail integration,
ensuring proper initialization and operation.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from quack_core.core.errors import QuackIntegrationError
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.google.mail.service import GoogleMailService
from tests.test_integrations.google.mail.mocks import (
    create_error_gmail_service,
    create_mock_gmail_service,
)


class TestInitializeConfigRealPathHitsBugC:
    """BUG C, found quackverse-coverage-90 round 4 (SOW-5), fixed round 5
    (SOW-6) per RULING-238 -- name kept per append-don't-revert (CLAUDE.md
    s5) so the history of what this test used to prove stays legible.

    Was: google/mail/service.py:194 called
    `paths.resolve_project_path(self.storage_path)` where `paths` was the
    raw `quack_core.core.paths.service` MODULE (imported at line 12) rather
    than a `PathService` instance -- `resolve_project_path` is an INSTANCE
    method (core/paths/service.py:64), not a module-level function. Every
    real call raised `AttributeError`, silently caught by
    `_initialize_config()`'s own broad `except Exception` and swallowed to
    `None` -- so `GoogleMailService.initialize()` always failed for any real
    (non-mocked) caller. google/config.py:330-342 already carried a comment
    flagging the identical `PathService` instance-vs-module trap.

    Fixed (RULING-238): `_initialize_config` now instantiates
    `PathService()` and calls the instance method, then explicitly unwraps
    the returned `PathResult` (checking `.success`, reading `.path`) instead
    of the broken `paths.resolve_project_path(...)` module call *and* the
    equally-broken `str(storage_path_obj)` on the un-unwrapped result object
    (a second, dependent bug -- `PathResult` is a pydantic model, so
    stringifying it directly produces the model's repr, e.g.
    "success=True path='/tmp/foo' error=None", not the path itself;
    confirmed live pre-fix during this round's own investigation).

    This test now asserts REAL SUCCESS: a resolved path, `self.storage_path`
    set to that real resolved string (not a `None`, not a `PathResult` repr
    string, not a swallowed exception), matching RULING-238 s1(2)'s explicit
    proof requirement.
    """

    def test_initialize_config_real_storage_path_hits_bug_c(self) -> None:
        # A path INSIDE the repo sandbox, not tmp_path: core/fs's
        # allow_absolute=False sandbox invariant (Master-ratified R-2,
        # core/fs/SERVICE-CONTRACT.md s4) correctly refuses to create a
        # directory outside the project base dir -- that is separate,
        # already-correct behavior, not part of Bug C. Using a relative
        # in-sandbox scratch dir isolates the assertion to what RULING-238
        # actually fixed: resolve_project_path's instance-vs-module call
        # and the PathResult-unwrap, not the sandbox boundary.
        rel_storage = "test_scratch_mail_storage_bug_c"
        storage_dir = Path.cwd() / rel_storage
        if storage_dir.exists():
            storage_dir.rmdir()
        service = GoogleMailService(
            client_secrets_file="secrets.json",
            credentials_file="creds.json",
            storage_path=rel_storage,
        )

        try:
            result = service._initialize_config()

            # Real success: the broad except never fires, config comes
            # back populated (not swallowed to None).
            assert result is not None
            assert result["client_secrets_file"] == "secrets.json"
            assert result["credentials_file"] == "creds.json"

            # The resolved storage_path is the REAL path string -- not a
            # PathResult repr, not the original unresolved relative input,
            # and it actually round-trips to an existing directory
            # (proving resolve_project_path's return value was correctly
            # unwrapped before being handed to fs.create_directory).
            assert service.storage_path == str(storage_dir)
            assert "PathResult" not in service.storage_path
            assert "success=" not in service.storage_path
            assert os.path.isdir(service.storage_path)
        finally:
            if storage_dir.exists():
                storage_dir.rmdir()


class TestGoogleMailService:
    """Tests for the GoogleMailService class."""

    def test_init(self) -> None:
        """Test initializing the mail service."""
        # Test with explicit parameters
        service = GoogleMailService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
            storage_path="/path/to/storage",
            include_subject=True,
            include_sender=True,
        )

        assert service.name == "GoogleMail"
        assert service.custom_config["client_secrets_file"] == "/path/to/secrets.json"
        assert service.custom_config["credentials_file"] == "/path/to/credentials.json"
        assert service.custom_config["storage_path"] == "/path/to/storage"
        assert service.custom_config["include_subject"] is True
        assert service.custom_config["include_sender"] is True
        assert service._initialized is False

        # Test with minimal parameters
        service = GoogleMailService()
        assert service.custom_config == {}
        assert service.storage_path is None

        # Test with custom OAuth scopes
        custom_scopes = ["https://www.googleapis.com/auth/gmail.modify"]
        service = GoogleMailService(oauth_scope=custom_scopes)
        assert service.oauth_scope == custom_scopes

    @patch("quack_core.integrations.google.config.GoogleConfigProvider.load_config")
    def test_initialize_config(self, mock_load_config: MagicMock) -> None:
        """Test initializing the service configuration."""
        # Instead of mocking file _ops, mock the _initialize_config method itself
        # and check that it gets the right inputs and generates the right outputs

        # Test with explicit parameters
        service = GoogleMailService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
            storage_path="/path/to/storage",
        )

        # Create a custom _initialize_config method to override the real one
        def mock_initialize_config(self: GoogleMailService) -> dict[str, object]:
            config = {
                "client_secrets_file": self.custom_config.get("client_secrets_file"),
                "credentials_file": self.custom_config.get("credentials_file"),
                "storage_path": self.custom_config.get("storage_path"),
            }
            # Simulate the resolver behavior
            self.storage_path = "/resolved/path/to/storage"
            return config

        # Replace the service method with our mocked version
        with patch.object(
            GoogleMailService, "_initialize_config", mock_initialize_config
        ):
            # Call the method under test
            config = service._initialize_config()

            # Verify the results
            assert config["client_secrets_file"] == "/path/to/secrets.json"
            assert config["credentials_file"] == "/path/to/credentials.json"
            assert service.storage_path == "/resolved/path/to/storage"

        # Test with config from file
        mock_load_config.return_value = MagicMock()
        mock_load_config.return_value.success = True
        mock_load_config.return_value.content = {
            "client_secrets_file": "/config/secrets.json",
            "credentials_file": "/config/credentials.json",
            "storage_path": "/config/storage",
            "gmail_labels": ["INBOX"],
            "gmail_days_back": 14,
        }

        service = GoogleMailService(config_path="/path/to/config.yaml")

        # Create a custom _initialize_config method for this test case
        def mock_initialize_with_config(self: GoogleMailService) -> dict[str, object]:
            # Get config values from the mock
            config = mock_load_config.return_value.content
            # Simulate the resolver behavior
            self.storage_path = "/resolved/config/storage"
            return config

        # Replace the service method with our mocked version
        with patch.object(
            GoogleMailService, "_initialize_config", mock_initialize_with_config
        ):
            # Call the method under test
            config = service._initialize_config()

            # Verify the results
            assert config["client_secrets_file"] == "/config/secrets.json"
            assert config["credentials_file"] == "/config/credentials.json"
            assert service.storage_path == "/resolved/config/storage"

        # Test with filesystem error that should be logged but not fail
        service = GoogleMailService(config_path="/path/to/config.yaml")

        # Create a custom _initialize_config method that logs a warning
        def mock_initialize_with_warning(self: GoogleMailService) -> dict[str, object]:
            # Get config values from the mock
            config = mock_load_config.return_value.content
            # Simulate the resolver behavior
            self.storage_path = "/resolved/config/storage"
            # Log a warning (we'll patch the logger to verify this)
            self.logger.warning("Could not create storage directory: Permission denied")
            return config

        # Replace the service method with our mocked version
        with (
            patch.object(
                GoogleMailService, "_initialize_config", mock_initialize_with_warning
            ),
            patch.object(service.logger, "warning") as mock_warn,
        ):
            # Call the method under test
            config = service._initialize_config()

            # Verify the results
            assert config is not None
            mock_warn.assert_called_once()
            assert service.storage_path == "/resolved/config/storage"

        # Test without storage path
        service = GoogleMailService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        mock_load_config.return_value.content = {}

        # Replace the method with one that raises an exception
        def mock_initialize_with_error(self: GoogleMailService) -> dict[str, object]:
            raise QuackIntegrationError("Storage path is required")

        with patch.object(
            GoogleMailService, "_initialize_config", mock_initialize_with_error
        ):
            with pytest.raises(QuackIntegrationError):
                service._initialize_config()

    @patch(
        "quack_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch("quack_core.integrations.google.auth.GoogleAuthProvider.get_credentials")
    @patch(
        "quack_core.integrations.google.mail.operations.auth.initialize_gmail_service"
    )
    @patch("quack_core.integrations.core.base.BaseIntegrationService.initialize")
    def test_initialize(
        self,
        mock_base_init: MagicMock,
        mock_init_gmail: MagicMock,
        mock_get_credentials: MagicMock,
        mock_verify: MagicMock,
    ) -> None:
        """Test initializing the mail service."""
        # Mock base class initialization to succeed and file verification to pass
        mock_base_init.return_value = IntegrationResult.success_result()
        mock_verify.return_value = None  # Indicate successful verification

        # Mock the storage path
        service = GoogleMailService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
            storage_path="/path/to/storage",
        )

        # Mock the auth provider and credentials
        mock_credentials = MagicMock()
        mock_get_credentials.return_value = mock_credentials

        # Use our mock Gmail service
        mock_gmail_service = create_mock_gmail_service()
        mock_init_gmail.return_value = mock_gmail_service

        # Patch the _initialize_config method
        with patch.object(service, "_initialize_config") as mock_init_config:
            mock_init_config.return_value = {
                "client_secrets_file": "/path/to/secrets.json",
                "credentials_file": "/path/to/credentials.json",
                "storage_path": "/path/to/storage",
            }

            # Test successful initialization
            result = service.initialize()
            assert result.success is True
            assert service._initialized is True
            assert service.gmail_service is mock_gmail_service

            mock_get_credentials.assert_called_once()
            mock_init_gmail.assert_called_once_with(mock_credentials)

        # Test config initialization failure
        with patch.object(service, "_initialize_config") as mock_init_config:
            mock_init_config.return_value = None

            result = service.initialize()
            assert result.success is False
            assert "Failed to initialize configuration" in result.error
            assert service._initialized is False

        # Test authentication error
        with patch.object(service, "_initialize_config") as mock_init_config:
            mock_init_config.return_value = {
                "client_secrets_file": "/path/to/secrets.json",
                "credentials_file": "/path/to/credentials.json",
                "storage_path": "/path/to/storage",
            }
            mock_get_credentials.side_effect = Exception("Auth error")

            result = service.initialize()
            assert result.success is False
            assert "Failed to initialize Google Mail service" in result.error
            assert service._initialized is False

        # Test API error
        with patch.object(service, "_initialize_config") as mock_init_config:
            mock_init_config.return_value = {
                "client_secrets_file": "/path/to/secrets.json",
                "credentials_file": "/path/to/credentials.json",
                "storage_path": "/path/to/storage",
            }
            mock_get_credentials.side_effect = None
            mock_init_gmail.side_effect = Exception("API error")

            result = service.initialize()
            assert result.success is False
            assert "Failed to initialize Google Mail service" in result.error
            assert service._initialized is False

    def test_list_emails(self) -> None:
        """Test listing emails."""
        service = GoogleMailService(storage_path="/path/to/storage")
        service._initialized = True
        service.gmail_service = create_mock_gmail_service()
        service.config = {
            "gmail_days_back": 10,
            "gmail_labels": ["INBOX", "IMPORTANT"],
            "gmail_user_id": "test@example.com",
        }

        # Mock the email _ops module
        with patch(
            "quack_core.integrations.google.mail.operations.email.list_emails"
        ) as mock_list:
            mock_list.return_value = IntegrationResult.success_result(
                content=[{"id": "msg1"}, {"id": "msg2"}]
            )

            with patch(
                "quack_core.integrations.google.mail.operations.email.build_query"
            ) as mock_build:
                mock_build.return_value = "after:2021/01/01 label:INBOX label:IMPORTANT"

                # Test with default query
                result = service.list_emails()
                assert result.success is True
                assert len(result.content) == 2
                assert result.content[0]["id"] == "msg1"

                mock_build.assert_called_once_with(10, ["INBOX", "IMPORTANT"])
                mock_list.assert_called_once_with(
                    service.gmail_service,
                    "test@example.com",
                    "after:2021/01/01 label:INBOX label:IMPORTANT",
                    service.logger,
                )

            # Test with custom query
            mock_list.reset_mock()
            result = service.list_emails(query="subject:Test")
            assert result.success is True
            mock_list.assert_called_once_with(
                service.gmail_service,
                "test@example.com",
                "subject:Test",
                service.logger,
            )

        # Test with error
        service.gmail_service = create_error_gmail_service()
        with patch(
            "quack_core.integrations.google.mail.operations.email.list_emails"
        ) as mock_list:
            mock_list.side_effect = Exception("API error")

            result = service.list_emails()
            assert result.success is False
            assert "Failed to list emails" in result.error

        # Test not initialized
        service._initialized = False
        with patch.object(service, "_ensure_initialized") as mock_ensure:
            mock_ensure.return_value = IntegrationResult(
                success=False,
                error="Not initialized",
            )

            result = service.list_emails()
            assert result.success is False
            assert "Not initialized" in result.error

    def test_download_email(self) -> None:
        """Test downloading an email."""
        service = GoogleMailService(storage_path="/path/to/storage")
        service._initialized = True
        service.gmail_service = create_mock_gmail_service()
        service.config = {
            "gmail_user_id": "test@example.com",
            "include_subject": True,
            "include_sender": False,
            "max_retries": 3,
            "initial_delay": 0.5,
            "max_delay": 5.0,
        }

        # Mock the email _ops module
        with patch(
            "quack_core.integrations.google.mail.operations.email.download_email"
        ) as mock_download:
            mock_download.return_value = IntegrationResult.success_result(
                content="/path/to/storage/email.html"
            )

            # Test downloading
            result = service.download_email("msg1")
            assert result.success is True
            assert result.content == "/path/to/storage/email.html"

            mock_download.assert_called_once_with(
                service.gmail_service,
                "test@example.com",
                "msg1",
                "/path/to/storage",
                True,  # include_subject from config
                False,  # include_sender from config
                3,  # max_retries from config
                0.5,  # initial_delay from config
                5.0,  # max_delay from config
                service.logger,
            )

        # Test with error
        service.gmail_service = create_error_gmail_service()
        with patch(
            "quack_core.integrations.google.mail.operations.email.download_email"
        ) as mock_download:
            mock_download.side_effect = Exception("API error")

            result = service.download_email("msg1")
            assert result.success is False
            assert "Failed to download email msg1" in result.error

        # Test not initialized
        service._initialized = False
        with patch.object(service, "_ensure_initialized") as mock_ensure:
            mock_ensure.return_value = IntegrationResult(
                success=False,
                error="Not initialized",
            )

            result = service.download_email("msg1")
            assert result.success is False
            assert "Not initialized" in result.error


class TestGoogleMailServiceCoverageGaps:
    """Additional tests for GoogleMailService covering branches not exercised
    by the pre-existing test classes above: trivial properties, the various
    `_initialize_config` failure/warning paths (mocking the `paths.PathService`
    and `fs` boundaries per RULING-235 rather than the quack_core function
    under test), the "service/storage_path is None" guard branches in
    `list_emails`/`download_email`, the numeric/list coercion helper edge
    cases, and `validate_config`.
    """

    def test_version_property(self) -> None:
        service = GoogleMailService()
        assert service.version == "1.0.0"

    def test_initialize_early_return_when_base_init_fails(self) -> None:
        """Covers service.py:117 -- initialize() returns immediately when
        BaseIntegrationService.initialize() itself reports failure, without
        ever touching config/auth/gmail_service."""
        service = GoogleMailService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
            storage_path="/path/to/storage",
        )
        base_failure: IntegrationResult = IntegrationResult.error_result(
            "base init failed"
        )
        with patch(
            "quack_core.integrations.core.base.BaseIntegrationService.initialize",
            return_value=base_failure,
        ):
            result = service.initialize()
            assert result is base_failure
            assert result.success is False

    def test_initialize_config_load_from_file_failure(self) -> None:
        """Covers service.py:175-180 -- config_provider.load_config() failing
        (or returning empty content) raises QuackIntegrationError, which is
        re-raised as-is by the `except QuackIntegrationError: raise` clause
        (line 218-219) rather than being swallowed by the broader
        `except Exception` branch below it."""
        service = GoogleMailService(config_path="/path/to/config.yaml")
        with patch.object(
            service.config_provider, "load_config"
        ) as mock_load_config:
            mock_load_config.return_value = MagicMock(success=False, content=None)
            with pytest.raises(
                QuackIntegrationError, match="Failed to load configuration"
            ):
                service._initialize_config()

    def test_initialize_config_storage_path_from_config_dict(self) -> None:
        """Covers service.py:184-186 -- when self.storage_path is not set via
        constructor, it's pulled from the loaded config dict's 'storage_path'
        key (only if it's a str)."""
        service = GoogleMailService(config_path="/path/to/config.yaml")
        assert service.storage_path is None

        with patch.object(
            service.config_provider, "load_config"
        ) as mock_load_config:
            mock_load_config.return_value = MagicMock(
                success=True,
                content={
                    "client_secrets_file": "/secrets.json",
                    "credentials_file": "/creds.json",
                    "storage_path": "/config/storage",
                },
            )
            with (
                patch(
                    "quack_core.integrations.google.mail.service.paths.PathService"
                ) as mock_path_service_cls,
                patch(
                    "quack_core.integrations.google.mail.service.fs.create_directory"
                ) as mock_create_dir,
            ):
                mock_path_service = MagicMock()
                mock_path_service.resolve_project_path.return_value = MagicMock(
                    success=True, path="/resolved/config/storage", error=None
                )
                mock_path_service_cls.return_value = mock_path_service
                mock_create_dir.return_value = MagicMock(success=True, error=None)

                result = service._initialize_config()

                assert result is not None
                assert service.storage_path == "/resolved/config/storage"
                mock_path_service.resolve_project_path.assert_called_once_with(
                    "/config/storage"
                )

    def test_initialize_config_no_storage_path_raises(self) -> None:
        """Covers service.py:189 -- if storage_path is still unset after
        checking both constructor param and config dict, a
        QuackIntegrationError is raised (and caught/re-raised, so
        _initialize_config surfaces it -- but the caller `initialize()`
        catches broad Exception, so we call _initialize_config directly)."""
        service = GoogleMailService(config_path="/path/to/config.yaml")
        with patch.object(
            service.config_provider, "load_config"
        ) as mock_load_config:
            mock_load_config.return_value = MagicMock(
                success=True,
                content={
                    "client_secrets_file": "/secrets.json",
                    "credentials_file": "/creds.json",
                    # no storage_path key at all
                },
            )
            with pytest.raises(QuackIntegrationError, match="Storage path"):
                service._initialize_config()

    def test_initialize_config_resolve_project_path_failure(self) -> None:
        """Covers service.py:202 -- resolve_project_path() returning a
        failed PathResult raises QuackIntegrationError with the resolver's
        error message embedded."""
        service = GoogleMailService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
            storage_path="/bad/storage/path",
        )
        with patch(
            "quack_core.integrations.google.mail.service.paths.PathService"
        ) as mock_path_service_cls:
            mock_path_service = MagicMock()
            mock_path_service.resolve_project_path.return_value = MagicMock(
                success=False, path=None, error="resolution boom"
            )
            mock_path_service_cls.return_value = mock_path_service

            with pytest.raises(QuackIntegrationError, match="resolution boom"):
                service._initialize_config()

    def test_initialize_config_create_directory_warning(self) -> None:
        """Covers service.py:210 -- fs.create_directory() failing logs a
        warning but does NOT raise; _initialize_config still succeeds."""
        service = GoogleMailService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
            storage_path="/some/storage/path",
        )
        with (
            patch(
                "quack_core.integrations.google.mail.service.paths.PathService"
            ) as mock_path_service_cls,
            patch(
                "quack_core.integrations.google.mail.service.fs.create_directory"
            ) as mock_create_dir,
            patch.object(service.logger, "warning") as mock_warn,
        ):
            mock_path_service = MagicMock()
            mock_path_service.resolve_project_path.return_value = MagicMock(
                success=True, path="/some/storage/path", error=None
            )
            mock_path_service_cls.return_value = mock_path_service
            mock_create_dir.return_value = MagicMock(
                success=False, error="permission denied"
            )

            result = service._initialize_config()

            assert result is not None
            mock_warn.assert_called_once()
            assert "Could not create storage directory" in mock_warn.call_args[0][0]

    def test_initialize_config_unexpected_exception_returns_none(self) -> None:
        """Covers service.py:220-222 -- a non-QuackIntegrationError exception
        raised anywhere in the try block is logged and swallowed to None
        (rather than propagating), distinct from the QuackIntegrationError
        re-raise path covered by the other tests above."""
        service = GoogleMailService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
            storage_path="/some/storage/path",
        )
        with (
            patch(
                "quack_core.integrations.google.mail.service.paths.PathService"
            ) as mock_path_service_cls,
            patch.object(service.logger, "error") as mock_error,
        ):
            mock_path_service_cls.side_effect = RuntimeError("unexpected boom")

            result = service._initialize_config()

            assert result is None
            mock_error.assert_called_once()

    def test_list_emails_gmail_service_none(self) -> None:
        """Covers service.py:252 -- list_emails() with gmail_service unset
        returns an error result rather than raising AttributeError."""
        service = GoogleMailService(storage_path="/path/to/storage")
        service._initialized = True
        service.gmail_service = None
        service.config = {}

        result = service.list_emails(query="subject:Test")
        assert result.success is False
        assert result.error is not None
        assert "Gmail service is not initialized" in result.error

    def test_download_email_gmail_service_or_storage_path_none(self) -> None:
        """Covers service.py:302 -- download_email() with either
        gmail_service or storage_path unset returns an error result."""
        service = GoogleMailService(storage_path="/path/to/storage")
        service._initialized = True
        service.gmail_service = None
        service.storage_path = "/path/to/storage"
        service.config = {}

        result = service.download_email("msg1")
        assert result.success is False
        assert result.error is not None
        assert "Gmail service or storage path not initialized" in result.error

        service.gmail_service = create_mock_gmail_service()
        service.storage_path = None
        result = service.download_email("msg1")
        assert result.success is False
        assert result.error is not None
        assert "Gmail service or storage path not initialized" in result.error

    def test_validate_and_convert_config_gmail_labels(self) -> None:
        """Covers service.py:351-354 -- gmail_labels is converted via
        _convert_to_string_list when present in self.config."""
        service = GoogleMailService()
        service.config = {"gmail_labels": ["INBOX", 123, None]}
        service._validate_and_convert_config()
        assert service.config["gmail_labels"] == ["INBOX", "123"]

    def test_safe_cast_int_exception_path(self) -> None:
        """Covers service.py:369-374 -- non-int, non-castable values fall
        through to the default via the caught ValueError/TypeError."""
        service = GoogleMailService()
        assert service._safe_cast_int("not-a-number", 42) == 42
        assert service._safe_cast_int(None, 7) == 7
        assert service._safe_cast_int("10", 0) == 10
        assert service._safe_cast_int(5, 0) == 5

    def test_safe_cast_float_exception_path(self) -> None:
        """Covers service.py:389-396 -- float casting: passthrough for
        float/int, exception fallback to default for uncastable values."""
        service = GoogleMailService()
        assert service._safe_cast_float(3.5, 0.0) == 3.5
        assert service._safe_cast_float(3, 0.0) == 3.0
        assert service._safe_cast_float("not-a-float", 1.5) == 1.5
        assert service._safe_cast_float(None, 2.5) == 2.5
        assert service._safe_cast_float("2.75", 0.0) == 2.75

    def test_convert_to_string_list_variants(self) -> None:
        """Covers service.py:409, 414-417 -- None returns None, a list
        converts each item to str dropping Nones, a non-list Iterable
        (e.g. a tuple) converts similarly, and a bare str/bytes/other
        non-iterable falls through to None."""
        service = GoogleMailService()
        assert service._convert_to_string_list(None) is None
        assert service._convert_to_string_list(["a", 1, None]) == ["a", "1"]
        assert service._convert_to_string_list(("x", "y")) == ["x", "y"]
        assert service._convert_to_string_list(42) is None

    def test_validate_config(self) -> None:
        """Covers service.py:429-437 -- validate_config delegates to the
        pydantic GmailServiceConfig model, returning (True, []) on success
        and (False, [message]) when validation raises."""
        service = GoogleMailService()

        valid, errors = service.validate_config(
            {
                "client_secrets_file": "/secrets.json",
                "credentials_file": "/creds.json",
                "storage_path": "/storage",
            }
        )
        assert valid is True
        assert errors == []

        valid, errors = service.validate_config({})
        assert valid is False
        assert len(errors) == 1
        assert "Configuration validation failed" in errors[0]
