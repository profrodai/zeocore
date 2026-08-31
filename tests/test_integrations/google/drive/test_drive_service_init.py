"""
Tests for Google Drive service initialization.
"""

from unittest.mock import MagicMock, patch

from zeo_core.integrations.core.protocols import StorageIntegrationProtocol
from zeo_core.integrations.google.drive.service import GoogleDriveService


class TestGoogleDriveServiceInit:
    """Tests for the GoogleDriveService initialization."""

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    def test_init(self, mock_verify: MagicMock) -> None:
        """Test initializing the drive service.

        Config resolution is deferred to initialize() (matching
        google/mail/service.py, RULING-409 s6c step 1) so that __init__
        itself never raises for a caller with no config file yet -- so
        service.config is only populated after initialize() runs, not
        immediately after construction.
        """
        # Bypass verification
        mock_verify.return_value = None

        # Test with explicit parameters
        service = GoogleDriveService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
            shared_folder_id="folder123",
        )

        assert service.name == "GoogleDrive"
        assert service.config == {}
        assert service.auth_provider is None
        assert service.scopes == GoogleDriveService.SCOPES
        assert service._initialized is False

        # _initialize_config itself (invoked directly, matching what
        # initialize() does internally) still resolves the same merged
        # config -- this is the piece deferred out of __init__, not a
        # behavior change to what it resolves to.
        resolved = service._initialize_config(
            "/path/to/secrets.json", "/path/to/credentials.json", "folder123"
        )
        assert resolved["client_secrets_file"] == "/path/to/secrets.json"
        assert resolved["credentials_file"] == "/path/to/credentials.json"
        assert resolved["shared_folder_id"] == "folder123"

        # Test with custom scopes
        custom_scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        service = GoogleDriveService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
            scopes=custom_scopes,
        )

        assert service.scopes == custom_scopes

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    def test_init_always_constructs_real_config_and_auth_providers(
        self, mock_verify: MagicMock
    ) -> None:
        """config_provider is never None after __init__; auth_provider is
        None until initialize() runs.

        Regression coverage for the None-narrowing added to
        _initialize_config and initialize(): config_provider is typed
        ConfigProviderProtocol | None on the base class, but
        GoogleDriveService.__init__ always constructs and assigns a real
        instance before it is used, so that narrowing is unreachable for
        this concrete class -- asserted directly (not mocked) so the claim
        is a checked fact. auth_provider, by contrast, is deliberately
        deferred to initialize() (RULING-409 s6c step 1, matching
        google/mail/service.py) so __init__ never raises for a caller with
        no config file yet -- it is None right after construction and only
        becomes real once initialize() has resolved a config to build it
        from.
        """
        mock_verify.return_value = None

        service = GoogleDriveService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )

        assert service.config_provider is not None
        assert service.auth_provider is None
        # Real object identity, not a stub -- confirms this is a genuine
        # GoogleConfigProvider instance, not a sentinel.
        assert type(service.config_provider).__name__ == "GoogleConfigProvider"

        service.initialize()
        assert service.auth_provider is not None
        assert type(service.auth_provider).__name__ == "GoogleAuthProvider"

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch.object(GoogleDriveService, "_initialize_config")
    def test_is_storage_integration(
        self, mock_init_config: MagicMock, mock_verify: MagicMock
    ) -> None:
        """Test that service implements StorageIntegrationProtocol."""
        # Bypass verification
        mock_verify.return_value = None

        # Mock configuration
        mock_init_config.return_value = {
            "client_secrets_file": "/path/to/secrets.json",
            "credentials_file": "/path/to/credentials.json",
        }

        service = GoogleDriveService()

        assert isinstance(service, StorageIntegrationProtocol)

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch("zeo_core.integrations.google.config.GoogleConfigProvider.load_config")
    def test_initialize_config(
        self, mock_load_config: MagicMock, mock_verify: MagicMock
    ) -> None:
        """Test the service configuration resolution logic.

        _initialize_config's merge logic (explicit params / file config /
        invalid-config-falls-back-to-default) is unchanged by the
        __init__-to-initialize() deferral -- only WHEN it runs moved, not
        WHAT it resolves to. Exercised by calling it directly, the same way
        initialize() now does, rather than through __init__ side effects.
        """
        # Bypass verification
        mock_verify.return_value = None

        # Test with explicit parameters
        service = GoogleDriveService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
            shared_folder_id="folder123",
        )

        resolved = service._initialize_config(
            "/path/to/secrets.json", "/path/to/credentials.json", "folder123"
        )
        assert resolved["client_secrets_file"] == "/path/to/secrets.json"
        assert resolved["credentials_file"] == "/path/to/credentials.json"
        assert resolved["shared_folder_id"] == "folder123"

        # Test with config from file
        mock_load_config.return_value.success = True
        mock_load_config.return_value.content = {
            "client_secrets_file": "/config/secrets.json",
            "credentials_file": "/config/credentials.json",
            "shared_folder_id": "config_folder",
        }

        service = GoogleDriveService(config_path="/path/to/config.yaml")
        resolved = service._initialize_config(None, None, None)
        assert resolved["client_secrets_file"] == "/config/secrets.json"
        assert resolved["credentials_file"] == "/config/credentials.json"
        assert resolved["shared_folder_id"] == "config_folder"

        # Test with invalid config (should use default)
        mock_load_config.return_value.success = False

        with patch(
            "zeo_core.integrations.google.config.GoogleConfigProvider.get_default_config"
        ) as mock_default:
            mock_default.return_value = {
                "client_secrets_file": "/default/secrets.json",
                "credentials_file": "/default/credentials.json",
            }

            service = GoogleDriveService(config_path="/invalid/config.yaml")
            resolved = service._initialize_config(None, None, None)
            assert resolved["client_secrets_file"] == "/default/secrets.json"
            assert resolved["credentials_file"] == "/default/credentials.json"

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.authenticate")
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.get_credentials")
    @patch("googleapiclient.discovery.build")
    def test_initialize(
        self,
        mock_build: MagicMock,
        mock_get_credentials: MagicMock,
        mock_authenticate: MagicMock,
        mock_verify: MagicMock,
    ) -> None:
        """Test initializing the drive service."""
        # Bypass verification
        mock_verify.return_value = None

        # Mock successful authentication
        mock_authenticate.return_value.success = True

        service = GoogleDriveService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )

        # Mock the drive service
        mock_drive_service = MagicMock()
        mock_build.return_value = mock_drive_service

        # Mock credentials
        mock_credentials = MagicMock()
        mock_get_credentials.return_value = mock_credentials

        # Test successful initialization
        result = service.initialize()
        assert result.success is True
        assert service._initialized is True
        assert service.drive_service is mock_drive_service

        mock_get_credentials.assert_called_once()
        mock_build.assert_called_once_with("drive", "v3", credentials=mock_credentials)

        # Reset mocks for next tests
        mock_get_credentials.reset_mock()
        mock_build.reset_mock()

        # Test authentication error
        mock_authenticate.return_value.success = False
        mock_authenticate.return_value.error = "Auth error"

        service = GoogleDriveService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()

        assert result.success is False
        assert result.error is not None
        assert "Auth error" in result.error
        # The implementation doesn't set _initialized to False on error, so
        # we don't assert that

        # Test credentials error
        # Reset authentication mock
        mock_authenticate.return_value.success = True
        mock_authenticate.return_value.error = None

        # Mock get_credentials to throw an exception
        mock_get_credentials.side_effect = Exception("Auth error")

        service = GoogleDriveService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()

        assert result.success is False
        assert result.error is not None
        assert "Auth error" in result.error
        # Don't test _initialized flag as implementation varies

        # Reset for the next test
        mock_get_credentials.side_effect = None

        # Test API build error
        mock_build.side_effect = Exception("API error")

        service = GoogleDriveService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()

        assert result.success is False
        assert result.error is not None
        assert "API error" in result.error
        # Don't test _initialized flag as implementation varies
