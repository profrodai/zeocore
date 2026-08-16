# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/service/test_integration.py
# === QV-LLM:END ===

"""
Comprehensive tests for the LLM integration service class.

This module provides complete test coverage for the service/integration.py file,
which contains the main LLMIntegration class implementation.
"""

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from quack_core.core.errors import QuackIntegrationError
from quack_core.integrations.core.results import ConfigResult, IntegrationResult
from quack_core.integrations.llms.config import LLMConfigProvider
from quack_core.integrations.llms.fallback import FallbackConfig
from quack_core.integrations.llms.service.integration import LLMIntegration


def _mock_provider(integration: LLMIntegration) -> MagicMock:
    """Narrow integration.config_provider (typed ConfigProviderProtocol | None
    in production, since a real caller may not pass one) to the MagicMock the
    `integration` fixture below always installs, so tests can assert on mock
    call history without every call site re-asserting non-None. The cast is
    honest, not a suppression: the fixture's own body (below) guarantees this
    at construction time, mypy just can't see across the fixture boundary."""
    assert integration.config_provider is not None
    return cast(MagicMock, integration.config_provider)


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
        """Test initializing with custom parameters.

        Regression test for RULING-236: LLMIntegration.__init__ used to call
        super().__init__(config_provider, None, config_path, str(log_level))
        positionally against BaseIntegrationService.__init__'s real signature
        (config_provider, auth_provider, config, config_path, log_level) --
        shifting config_path into the `config` slot and a stringified
        log_level into the `config_path` slot. The old version of this test
        could not catch that: `mock_resolve_path.return_value` was a FIXED
        SimpleNamespace regardless of what string `resolve_path` was actually
        called with, so a corrupted config_path (e.g. the log level "10"
        resolved as a bogus relative path) and the real config_path
        ("custom_config.yaml" resolved correctly) both produced the exact
        same asserted value -- a false-positive that would have passed
        against either the buggy or the fixed call site. `resolve_path` is
        now a side_effect that echoes its actual argument, so the assertion
        below can only pass if `_set_config_path` (and therefore
        BaseIntegrationService.__init__) actually received the caller's real
        config_path string, not a stringified log level.
        """
        with patch(
            "quack_core.core.fs.service.standalone.get_file_info"
        ) as mock_file_info:
            # Create a proper FileInfoResult
            file_info_result = MagicMock()
            file_info_result.success = True
            file_info_result.exists = True
            file_info_result.is_file = True
            mock_file_info.return_value = file_info_result

            # Also patch resolve_path -- echo the input path instead of a
            # fixed return value, so the test can distinguish "resolved the
            # caller's real config_path" from "resolved something else
            # entirely" (e.g. a stringified log_level landing in that slot).
            with patch(
                "quack_core.core.fs.service.standalone.resolve_path"
            ) as mock_resolve_path:
                # A plain SimpleNamespace (not a bare MagicMock) is required
                # here: coerce_path_str's duck-typing checks .value()/
                # .unwrap() before .path, and a bare MagicMock auto-vivifies
                # both as callables, so it never reaches the real .path
                # attribute.
                mock_resolve_path.side_effect = lambda p: SimpleNamespace(
                    path=f"/Users/rodrivera/{p}"
                )

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
                    # config_path must resolve from the REAL passed path
                    # ("custom_config.yaml"), never from a log-level-derived
                    # nonsense path (e.g. "/Users/rodrivera/10").
                    assert (
                        integration.config_path
                        == "/Users/rodrivera/custom_config.yaml"
                    )
                    # config stays None (the ctor's own default): the bug
                    # shifted config_path into this slot, so a regression
                    # would set self.config to the string "custom_config.yaml"
                    # instead.
                    assert integration.config is None
                    assert integration.log_level == 10
                    # The base logger's effective level must reflect the
                    # caller's real log_level, not the base class's own
                    # default (20/INFO) that the bug silently fell back to
                    # by never passing log_level through positionally.
                    assert integration.logger.getEffectiveLevel() == 10
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
        provider = _mock_provider(integration)
        provider.load_config.assert_not_called()
        provider.get_default_config.assert_not_called()

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
        _mock_provider(integration).load_config.assert_called_once()

    def test_extract_config_provider_failure(self, integration: LLMIntegration) -> None:
        """Test extracting config when provider fails."""
        # Clear existing config
        integration.config = None
        provider = _mock_provider(integration)

        # Make load_config return failure
        provider.load_config.return_value = ConfigResult(
            success=False, error="Failed to load config"
        )

        # Extract config - should fall back to default
        result = integration._extract_config()

        # Should use default config
        assert result == provider.get_default_config.return_value
        provider.load_config.assert_called_once()
        provider.get_default_config.assert_called_once()

    def test_extract_config_load_exception(self, integration: LLMIntegration) -> None:
        """Test extracting config when provider raises an exception."""
        # Clear existing config
        integration.config = None
        provider = _mock_provider(integration)

        # Make load_config raise an exception
        provider.load_config.side_effect = Exception("Load error")

        # Extract config - should handle exception and fall back to default
        result = integration._extract_config()

        # Should use default config
        assert result == provider.get_default_config.return_value
        provider.load_config.assert_called_once()
        provider.get_default_config.assert_called_once()

    def test_extract_config_none_after_load_raises(
        self, integration: LLMIntegration
    ) -> None:
        """Test the defensive self.config is None guard (line ~115-116).

        Structurally reachable only if a config_provider misbehaves and
        returns None from get_default_config() despite its own dict[str,
        Any] signature -- not exercised by any other test since every
        other path sets a real dict. Forces that exact misbehavior via the
        mock provider directly, rather than leaving the guard body dead
        code, matching this chain's own established discipline for
        traced-safe defensive branches (SOW-57 s5)."""
        integration.config = None
        provider = _mock_provider(integration)
        provider.load_config.return_value = ConfigResult(
            success=False, error="Failed to load config"
        )
        provider.get_default_config.return_value = None

        with pytest.raises(QuackIntegrationError) as excinfo:
            integration._extract_config()

        assert "LLM configuration not initialized" in str(excinfo.value)

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
            _mock_provider(integration).load_config.assert_not_called()

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
                    success_result: IntegrationResult[Any] = IntegrationResult(
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
            ):
                # Mock extract_config with fallback configuration
                mock_config = {
                    "default_provider": "openai",
                    "fallback": {"providers": ["openai", "anthropic", "mock"]},
                }
                with patch.object(
                    integration, "_extract_config", return_value=mock_config
                ):
                    # Mock FallbackConfig creation
                    with patch(
                        "quack_core.integrations.llms.fallback.FallbackConfig"
                    ) as mock_fallback_config:
                        mock_fallback_config.return_value = FallbackConfig(
                            providers=["openai", "anthropic", "mock"]
                        )

                        # Mock fallback initialization
                        success_result: IntegrationResult[Any] = IntegrationResult(
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
            ):
                # Initialize should handle the error properly
                result = integration.initialize()

                assert result.success is False
                assert "Integration error" == result.error

                # Logger should record the error
                cast(MagicMock, integration.logger).error.assert_called()

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
            ):
                # Initialize should handle the error properly
                result = integration.initialize()

                assert result.success is False
                assert result.error is not None
                assert "Failed to initialize LLM integration" in result.error

                # Logger should record the error
                cast(MagicMock, integration.logger).error.assert_called()

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
