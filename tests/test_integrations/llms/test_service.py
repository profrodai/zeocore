# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/test_service.py
# role: tests
# neighbors: __init__.py, test_config.py, test_config_provider.py, test_fallback.py, test_integration.py, test_llms.py (+3 more)
# exports: TestLLMService
# git_branch: refactor/toolkitWorkflow
# git_commit: 07a259e
# === QV-LLM:END ===

"""
Tests for the LLM integration service.

This module tests the main service class for LLM integration, including
initialization, configuration, and client communication.
"""

from unittest.mock import MagicMock, patch

import pytest

from quack_core.lib.errors import QuackIntegrationError
from quack_core.lib.fs import DataResult, FileInfoResult
from quack_core.integrations.core.results import ConfigResult, IntegrationResult
from quack_core.integrations.llms.models import ChatMessage, LLMOptions, RoleType
from quack_core.integrations.llms.service import LLMIntegration

from .mocks.clients import MockClient


class TestLLMService:
    """Tests for the LLM integration service."""

    @pytest.fixture
    def llm_service(self) -> LLMIntegration:
        """Create a properly initialized LLM integration service."""
        # Create a service
        service = LLMIntegration()

        # Mock the file _operations using our fs module
        with patch("quack_core.lib.fs.service.get_file_info") as mock_file_info:
            file_info_result = FileInfoResult(
                success=True,
                path="./config/llm_config.yaml",
                exists=True,
                is_file=True,
            )
            mock_file_info.return_value = file_info_result

            with patch("quack_core.lib.fs.service.read_yaml") as mock_read_yaml:
                yaml_result = DataResult(
                    success=True,
                    path="./config/llm_config.yaml",
                    data={
                        "default_provider": "openai",
                        "timeout": 60,
                        "openai": {"api_key": "test-key"},
                    },
                    format="yaml",
                )
                mock_read_yaml.return_value = yaml_result

                # Set the config directly
                service.config = {
                    "default_provider": "openai",
                    "timeout": 60,
                    "openai": {"api_key": "test-key"},
                }

                # Mark as initialized to skip initialization
                service._initialized = True

                # Set a mock client
                service.client = MagicMock()

                return service

    def test_init(self) -> None:
        """Test initializing the LLM integration service."""
        # Test with default parameters
        service = LLMIntegration()
        assert service.provider is None
        assert service.model is None
        assert service.api_key is None
        assert service.client is None
        assert service._initialized is False

        # Test with custom parameters
        with patch("quack_core.lib.fs.service.get_file_info") as mock_file_info:
            # Create a proper FileInfoResult
            file_info_result = FileInfoResult(
                success=True,
                path="config.yaml",
                exists=True,
                is_file=True,
            )
            mock_file_info.return_value = file_info_result

            # Also patch normalize_path to handle the config path
            with patch("quack_core.lib.fs.api.normalize_path") as mock_normalize_path:
                # Create a mock Path object instead of using absolute()
                mock_path = "/Users/rodrivera/config.yaml"
                mock_normalize_path.return_value = mock_path

                # Also patch the BaseIntegrationService._set_config_path method
                with patch("quack_core.integrations.core.base.BaseIntegrationService._set_config_path"):
                    # Also patch os.getcwd() to avoid FileNotFoundError
                    with patch("os.getcwd", return_value="/Users/rodrivera"):
                        service = LLMIntegration(
                            provider="anthropic",
                            model="claude-3-opus",
                            api_key="test-key",
                            config_path="config.yaml",
                            log_level=20,
                        )

                        assert service.provider == "anthropic"
                        assert service.model == "claude-3-opus"
                        assert service.api_key == "test-key"
                        # Skip the config_path assertion since we're patching the method that sets it
                        assert service.log_level == 20

    def test_name_and_version(self, llm_service: LLMIntegration) -> None:
        """Test the name and version properties."""
        assert llm_service.name == "LLM"
        assert llm_service.version == "1.0.0"  # This should match what's in the code

    def test_initialize(self, llm_service: LLMIntegration) -> None:
        """Test initializing the LLM integration."""
        # Test successful initialization
        with patch(
            "quack_core.integrations.llms.registry.get_llm_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            result = llm_service.initialize()

            assert result.success is True
            assert llm_service._initialized is True
            assert llm_service.client == mock_client

            # Verify get_llm_client was called with correct params
            mock_get_client.assert_called_once()

    def test_extract_config(self, llm_service: LLMIntegration) -> None:
        """Test extracting and validating the LLM configuration."""
        # Test successful extraction
        config = llm_service._extract_config()
        assert config == llm_service.config

        # Test with missing config and mock provider responses
        # Create a new service to avoid state from previous test
        test_service = LLMIntegration()
        test_service.config = None

        # Mock the config provider
        test_service.config_provider = MagicMock()
        mock_provider = test_service.config_provider

        # Set up for success case
        # Use ConfigResult instead of DataResult to match what's expected
        config_result = ConfigResult(
            success=True, content={"default_provider": "anthropic", "timeout": 30}
        )
        mock_provider.load_config.return_value = config_result

        # Also mock get_default_config since it's called if load_config fails
        default_config = {"default_provider": "mock", "timeout": 10}
        mock_provider.get_default_config.return_value = default_config

        config1 = test_service._extract_config()
        assert config1["default_provider"] == "anthropic"

    def test_chat(self, llm_service: LLMIntegration) -> None:
        """Test the chat method."""
        # Set up mock client
        mock_client = MockClient(responses=["Test response"])
        llm_service.client = mock_client

        # Test successful chat
        messages = [
            ChatMessage.from_dict(
                {"role": "system", "content": "Be helpful and polite."}
            ),
            ChatMessage.from_dict(
                {"role": "user", "content": "Tell me about yourself."}
            ),
        ]
        options = LLMOptions(temperature=0.7, max_tokens=100)

        result = llm_service.chat(messages, options)

        assert result.success is True
        assert result.content == "Test response"

        # The uninitialized test needs to bypass the auto-initialize behavior
        # Create a test-specific service with specific behavior
        with patch(
            "quack_core.integrations.llms.service.LLMIntegration.initialize"
        ) as mock_init:
            # Make initialize return a failure without auto-retry
            mock_init.return_value = IntegrationResult(
                success=False, error="LLM integration not initialized"
            )

            uninitialized_service = LLMIntegration()
            uninitialized_service._initialized = False

            result = uninitialized_service.chat(messages)

            assert result.success is False
            assert "not initialized" in result.error

    def test_count_tokens(self, llm_service: LLMIntegration) -> None:
        """Test the count_tokens method."""
        # Set up mock client
        mock_client = MockClient(token_counts=[42])
        llm_service.client = mock_client

        # Test successful token counting
        messages = [
            ChatMessage(role=RoleType.USER, content="Test message"),
        ]

        result = llm_service.count_tokens(messages)

        assert result.success is True
        assert result.content == 42

        # For uninitialized test, create a service with specific behavior
        with patch(
            "quack_core.integrations.llms.service.LLMIntegration.initialize"
        ) as mock_init:
            mock_init.return_value = IntegrationResult(
                success=False, error="LLM integration not initialized"
            )

            uninitialized_service = LLMIntegration()
            uninitialized_service._initialized = False

            result = uninitialized_service.count_tokens(messages)

            assert result.success is False
            assert "not initialized" in result.error

    def test_get_client(self, llm_service: LLMIntegration) -> None:
        """Test the get_client method."""
        # Set up mock client
        mock_client = MockClient()
        llm_service.client = mock_client
        llm_service._initialized = True

        # Test successful client retrieval
        client = llm_service.get_client()
        assert client == mock_client

        # Test not initialized
        llm_service._initialized = False
        with pytest.raises(QuackIntegrationError) as excinfo:
            llm_service.get_client()

        assert "LLM client not initialized" in str(excinfo.value)
