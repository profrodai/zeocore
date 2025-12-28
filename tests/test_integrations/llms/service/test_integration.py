# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/service/test_integration.py
# role: service
# neighbors: __init__.py, test_dependencies.py, test_initialization.py, test_operations.py
# exports: TestLLMIntegrationComprehensive
# git_branch: refactor/newHeaders
# git_commit: 175956c
# === QV-LLM:END ===

"""
Comprehensive tests for the LLM integration service class.

This module provides complete test coverage for the service/integration.py file,
which contains the main LLMIntegration class implementation.
"""

from unittest.mock import MagicMock, patch

import pytest

from quack_core.lib.errors import QuackIntegrationError
from quack_core.integrations.core.results import ConfigResult, IntegrationResult
from quack_core.integrations.llms.config import LLMConfigProvider
from quack_core.integrations.llms.fallback import FallbackConfig
from quack_core.integrations.llms.service.integration import LLMIntegration


class TestLLMIntegrationComprehensive:
    """Comprehensive tests for the LLMIntegration class."""

    @pytest.fixture
    def integration(self) -> LLMIntegration:
        """Create an LLM integration instance with a mock config provider."""
        # Create a mock config provider
        mock_provider = MagicMock(spec=LLMConfigProvider)
        mock_provider.name = "LLMConfigProvider"
        mock_provider.get_default_config.return_value = {
            "default_provider": "openai",
            "timeout": 60,
            "openai": {"api_key": "mock-key", "default_model": "gpt-4o"},
        }

        # Create a config result
        config_result = ConfigResult(
            success=True,
            content={
                "default_provider": "openai",
                "timeout": 60,
                "openai": {"api_key": "mock-key", "default_model": "gpt-4o"},
            },
            config_path="/path/to/config.yaml",
        )
        mock_provider.load_config.return_value = config_result

        # Create the integration
        integration = LLMIntegration()
        integration.config_provider = mock_provider

        # Mock the logger for testing
        integration.logger = MagicMock()

        # Return without initializing
        integration._initialized = False
        return integration

    def test_init_default(self) -> None:
        """Test initializing with default parameters."""
        # We need to patch where it's imported, not its original location
        with patch(
            "quack_core.integrations.llms.service.integration.LLMConfigProvider"
        ) as mock_provider_class:
            integration = LLMIntegration()
            assert integration.provider is None
            assert integration.model is None
            assert integration.api_key is None
            assert integration.client is None
            assert integration._initialized is False
            assert integration._using_mock is False
            assert integration._enable_fallback is True
            assert integration._fallback_client is None

            # Check if config provider is initialized
            mock_provider_class.assert_called_once()

    def test_init_custom(self) -> None:
        """Test initializing with custom parameters."""
        with patch("quack_core.lib.fs.service.get_file_info") as mock_file_info:
            # Create a proper FileInfoResult
            file_info_result = MagicMock()
            file_info_result.success = True
            file_info_result.exists = True
            file_info_result.is_file = True
            mock_file_info.return_value = file_info_result

            # Also patch resolve_path
            with patch("quack_core.lib.fs.service.standalone.resolve_path") as mock_resolve_path:
                # Create a mock path string directly
                mock_path = "/Users/rodrivera/custom_config.yaml"
                mock_result = MagicMock()
                mock_result.path = mock_path
                mock_resolve_path.return_value = mock_result

                # Mock os.getcwd to prevent FileNotFoundError
                with patch("os.getcwd", return_value="/Users/rodrivera"):
                    integration = LLMIntegration(
                        provider="anthropic",
                        model="claude-3-opus",
                        api_key="test-key",
                        config_path="custom_config.yaml",
                        log_level=10,
                        enable_fallback=False,
                    )

                    assert integration.provider == "anthropic"
                    assert integration.model == "claude-3-opus"
                    assert integration.api_key == "test-key"
                    assert integration.config_path == mock_path
                    assert integration.log_level == 10
                    assert integration._enable_fallback is False

    def test_name_property(self, integration: LLMIntegration) -> None:
        """Test the name property."""
        assert integration.name == "LLM"

    def test_extract_config_existing(self, integration: LLMIntegration) -> None:
        """Test extracting config when it already exists."""
        # Set existing config
        test_config = {"default_provider": "test-provider"}
        integration.config = test_config

        # Extract config
        result = integration._extract_config()

        # Should return existing config without calling provider methods
        assert result == test_config
        integration.config_provider.load_config.assert_not_called()
        integration.config_provider.get_default_config.assert_not_called()

    def test_extract_config_from_provider(self, integration: LLMIntegration) -> None:
        """Test extracting config from the config provider."""
        # Clear existing config
        integration.config = None

        # Extract config
        result = integration._extract_config()

        # Should load from provider
        assert result == {
            "default_provider": "openai",
            "timeout": 60,
            "openai": {"api_key": "mock-key", "default_model": "gpt-4o"},
        }
        integration.config_provider.load_config.assert_called_once()

    def test_extract_config_provider_failure(self, integration: LLMIntegration) -> None:
        """Test extracting config when provider fails."""
        # Clear existing config
        integration.config = None

        # Make load_config return failure
        integration.config_provider.load_config.return_value = ConfigResult(
            success=False, error="Failed to load config"
        )

        # Extract config - should fall back to default
        result = integration._extract_config()

        # Should use default config
        assert result == integration.config_provider.get_default_config.return_value
        integration.config_provider.load_config.assert_called_once()
        integration.config_provider.get_default_config.assert_called_once()

    def test_extract_config_load_exception(self, integration: LLMIntegration) -> None:
        """Test extracting config when provider raises an exception."""
        # Clear existing config
        integration.config = None

        # Make load_config raise an exception
        integration.config_provider.load_config.side_effect = Exception("Load error")

        # Extract config - should handle exception and fall back to default
        result = integration._extract_config()

        # Should use default config
        assert result == integration.config_provider.get_default_config.return_value
        integration.config_provider.load_config.assert_called_once()
        integration.config_provider.get_default_config.assert_called_once()

    def test_extract_config_invalid(self, integration: LLMIntegration) -> None:
        """Test extracting invalid config."""
        # Clear existing config
        integration.config = None

        # Mock LLMConfig using the correct import path
        with patch("quack_core.integrations.llms.config.LLMConfig") as mock_llm_config:
            mock_llm_config.side_effect = ValueError("Invalid config")

            # Should raise QuackIntegrationError
            with pytest.raises(QuackIntegrationError) as excinfo:
                integration._extract_config()

            assert "Invalid LLM configuration" in str(excinfo.value)

    def test_initialize_base_failure(self, integration: LLMIntegration) -> None:
        """Test initialize when base class initialization fails."""
        # Mock base class initialize to fail
        with patch(
            "quack_core.integrations.core.base.BaseIntegrationService.initialize"
        ) as mock_base_init:
            mock_base_init.return_value = IntegrationResult(
                success=False, error="Base initialization failed"
            )

            # Initialize should fail too
            result = integration.initialize()

            assert result.success is False
            assert result.error == "Base initialization failed"

            # Shouldn't proceed to further initialization steps
            integration.config_provider.load_config.assert_not_called()

    def test_initialize_complete(self, integration: LLMIntegration) -> None:
        """Test complete initialization process."""
        # Mock base class initialize to succeed
        with patch(
            "quack_core.integrations.core.base.BaseIntegrationService.initialize"
        ) as mock_base_init:
            mock_base_init.return_value = IntegrationResult(success=True)

            # Mock check_llm_dependencies
            mock_deps_result = (
                True,
                "Available providers: openai, mock",
                ["openai", "mock"],
            )
            # Patch where it's actually imported, not just the function itself
            with patch(
                "quack_core.integrations.llms.service.integration.check_llm_dependencies",
                return_value=mock_deps_result,
            ) as mock_check_deps:
                # Mock extract_config
                with patch.object(
                    integration,
                    "_extract_config",
                    return_value={"default_provider": "openai"},
                ) as mock_extract:
                    # Mock single provider initialization
                    success_result = IntegrationResult(
                        success=True, message="Initialized"
                    )
                    with patch(
                        "quack_core.integrations.llms.service.initialization.initialize_single_provider",
                        return_value=success_result,
                    ) as mock_init_single:
                        # Call initialize
                        result = integration.initialize()

                        assert result.success is True
                        assert result.message == "Initialized"

                        # Verify method calls
                        mock_base_init.assert_called_once()
                        mock_check_deps.assert_called_once()
                        mock_extract.assert_called_once()
                        mock_init_single.assert_called_once_with(
                            integration,
                            {"default_provider": "openai"},
                            ["openai", "mock"],
                        )

    def test_initialize_with_fallback(self, integration: LLMIntegration) -> None:
        """Test initialization with fallback configuration."""
        # Mock base class initialize to succeed
        with patch(
            "quack_core.integrations.core.base.BaseIntegrationService.initialize"
        ) as mock_base_init:
            mock_base_init.return_value = IntegrationResult(success=True)

            # Mock check_llm_dependencies
            mock_deps_result = (
                True,
                "Available providers: openai, anthropic, mock",
                ["openai", "anthropic", "mock"],
            )
            with patch(
                "quack_core.integrations.llms.service.dependencies.check_llm_dependencies",
                return_value=mock_deps_result,
            ) as mock_check_deps:
                # Mock extract_config with fallback configuration
                mock_config = {
                    "default_provider": "openai",
                    "fallback": {"providers": ["openai", "anthropic", "mock"]},
                }
                with patch.object(
                    integration, "_extract_config", return_value=mock_config
                ) as mock_extract:
                    # Mock FallbackConfig creation
                    with patch(
                        "quack_core.integrations.llms.fallback.FallbackConfig"
                    ) as mock_fallback_config:
                        mock_fallback_config.return_value = FallbackConfig(
                            providers=["openai", "anthropic", "mock"]
                        )

                        # Mock fallback initialization
                        success_result = IntegrationResult(
                            success=True, message="Initialized with fallback"
                        )
                        with patch(
                            "quack_core.integrations.llms.service.initialization.initialize_with_fallback",
                            return_value=success_result,
                        ) as mock_init_fallback:
                            # Call initialize
                            result = integration.initialize()

                            assert result.success is True
                            assert result.message == "Initialized with fallback"

                            # Verify fallback was used
                            mock_init_fallback.assert_called_once()

    def test_initialize_integration_error(self, integration: LLMIntegration) -> None:
        """Test handling QuackIntegrationError during initialization."""
        # Mock base class initialize to succeed
        with patch(
            "quack_core.integrations.core.base.BaseIntegrationService.initialize"
        ) as mock_base_init:
            mock_base_init.return_value = IntegrationResult(success=True)

            # Make _extract_config raise an integration error
            with patch.object(
                integration,
                "_extract_config",
                side_effect=QuackIntegrationError("Integration error"),
            ) as mock_extract:
                # Initialize should handle the error properly
                result = integration.initialize()

                assert result.success is False
                assert "Integration error" == result.error

                # Logger should record the error
                integration.logger.error.assert_called()

    def test_initialize_generic_error(self, integration: LLMIntegration) -> None:
        """Test handling generic exceptions during initialization."""
        # Mock base class initialize to succeed
        with patch(
            "quack_core.integrations.core.base.BaseIntegrationService.initialize"
        ) as mock_base_init:
            mock_base_init.return_value = IntegrationResult(success=True)

            # Make _extract_config raise a generic exception
            with patch.object(
                integration, "_extract_config", side_effect=Exception("Generic error")
            ) as mock_extract:
                # Initialize should handle the error properly
                result = integration.initialize()

                assert result.success is False
                assert "Failed to initialize LLM integration" in result.error

                # Logger should record the error
                integration.logger.error.assert_called()

    def test_get_client_not_initialized(self, integration: LLMIntegration) -> None:
        """Test get_client when not initialized."""
        integration._initialized = False
        integration.client = None

        with pytest.raises(QuackIntegrationError) as excinfo:
            integration.get_client()

        assert "LLM client not initialized" in str(excinfo.value)

    def test_get_client_initialized(self, integration: LLMIntegration) -> None:
        """Test get_client when initialized."""
        integration._initialized = True
        mock_client = MagicMock()
        integration.client = mock_client

        client = integration.get_client()

        assert client == mock_client

    def test_is_using_mock_property(self, integration: LLMIntegration) -> None:
        """Test the is_using_mock property."""
        integration._using_mock = False
        assert integration.is_using_mock is False

        integration._using_mock = True
        assert integration.is_using_mock is True
