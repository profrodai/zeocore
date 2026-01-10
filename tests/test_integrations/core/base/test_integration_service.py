# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/core/base/test_integration_service.py
# role: tests
# neighbors: __init__.py, auth_provider_impl.py, config_provider_impl.py, integration_service_impl.py, test_auth_provider.py, test_base.py (+3 more)
# exports: TestBaseIntegrationService
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

from unittest.mock import patch

from quack_core.integrations.core.results import (
    AuthResult,
    ConfigResult,
    IntegrationResult,
)

from .auth_provider_impl import (
    MockAuthProvider,
)
from .config_provider_impl import (
    MockConfigProvider,
)
from .integration_service_impl import (
    MockIntegrationService,
)


class TestBaseIntegrationService:
    """Tests for the BaseIntegrationService class."""

    def test_init(self) -> None:
        """Test initializing the integration service."""
        # Test with config and auth providers
        config_provider = MockConfigProvider()
        auth_provider = MockAuthProvider()

        # Patch the fs service standalone method to return the input path
        with patch("quack_core.core.fs.service.standalone.resolve_path") as mock_resolve:
            mock_resolve.return_value = "/test/config.yaml"

            service = MockIntegrationService(
                config_provider=config_provider,
                auth_provider=auth_provider,
                config_path="/test/config.yaml",
            )

            assert service.config_provider is config_provider
            assert service.auth_provider is auth_provider
            assert service.config_path == "/test/config.yaml"
            assert service._initialized is False

        # Test without providers
        service = MockIntegrationService()
        assert service.config_provider is None
        assert service.auth_provider is None
        assert service.config_path is None

    def test_properties(self) -> None:
        """Test integration service properties."""
        service = MockIntegrationService()

        assert service.name == "test_integration"
        assert service.version == "1.0.0"
        assert service.custom_method() == "custom method"

    def test_initialize(self) -> None:
        """Test initializing the integration."""
        # Test with config provider
        config_provider = MockConfigProvider()
        with patch.object(config_provider, "load_config") as mock_load:
            mock_load.return_value = ConfigResult(
                success=True,
                content={"test_key": "test_value"},
            )

            service = MockIntegrationService(config_provider=config_provider)
            result = service.initialize()

            assert result.success is True
            assert service._initialized is True
            mock_load.assert_called_once()

        # Test with auth provider
        auth_provider = MockAuthProvider()
        with patch.object(auth_provider, "authenticate") as mock_auth:
            mock_auth.return_value = AuthResult(success=True)

            service = MockIntegrationService(auth_provider=auth_provider)
            result = service.initialize()

            assert result.success is True
            assert service._initialized is True
            mock_auth.assert_called_once()

        # Test with config load failure
        config_provider = MockConfigProvider()
        with patch.object(config_provider, "load_config") as mock_load:
            mock_load.return_value = ConfigResult(
                success=False,
                error="Failed to load config",
            )

            service = MockIntegrationService(config_provider=config_provider)
            with patch("quack_core.core.errors.QuackConfigurationError", Exception):
                result = service.initialize()

                assert result.success is False
                assert "Failed to load config" in result.error
                assert service._initialized is False

        # Test with auth failure
        auth_provider = MockAuthProvider()
        with patch.object(auth_provider, "authenticate") as mock_auth:
            mock_auth.return_value = AuthResult(
                success=False,
                error="Authentication failed",
            )

            service = MockIntegrationService(auth_provider=auth_provider)
            result = service.initialize()

            assert result.success is False
            assert "Authentication failed" in result.error
            assert service._initialized is False

    def test_is_available(self) -> None:
        """Test checking if the integration is available."""
        service = MockIntegrationService()

        # Not initialized
        assert service.is_available() is False

        # Initialized
        service._initialized = True
        assert service.is_available() is True

    def test_ensure_initialized(self) -> None:
        """Test ensuring the integration is initialized."""
        service = MockIntegrationService()

        # Test when not initialized
        with patch.object(service, "initialize") as mock_init:
            mock_init.return_value = IntegrationResult(success=True)

            result = service._ensure_initialized()
            assert result is None
            mock_init.assert_called_once()

            # Now set initialized to True for the next test
            service._initialized = True

        # Test when already initialized
        with patch.object(service, "initialize") as mock_init:
            result = service._ensure_initialized()
            assert result is None
            mock_init.assert_not_called()

        # Test initialization failure
        service._initialized = False
        with patch.object(service, "initialize") as mock_init:
            mock_init.return_value = IntegrationResult(
                success=False, error="Initialization failed"
            )

            result = service._ensure_initialized()
            assert result is not None
            assert result.success is False
            assert "Initialization failed" in result.error
            mock_init.assert_called_once()
