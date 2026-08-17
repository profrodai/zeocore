"""
Coverage-90 (RULING-234): tests for zeo_core.integrations.llms.service's
OWN LLMIntegration class and check_llm_dependencies function -- both are
standalone duplicates of the ones in service/integration.py and
service/dependencies.py respectively (confirmed live this session: no
re-export exists in service/__init__.py; every name is defined locally).

This matters for coverage because service/__init__.py's LLMIntegration is
the one actually reachable via the public import path
(zeo_core.integrations.llms.service.LLMIntegration, used by
zeo_core/integrations/llms/__init__.py and
zeo_core/prompt/_internal/enhancer.py) -- while the well-tested,
composed-from-helpers class lives at service/integration.py under its own
module path. This is a real structural duplication (recorded here as a
finding, not fixed -- out of this stream's coverage-work scope per
CLAUDE.md's circle of control); these tests close the coverage gap on the
class that is actually live on the public surface.

External SDK/network boundary mocked per RULING-235: importlib.util.find_spec,
requests.get, and zeo_core.integrations.llms.registry.get_llm_client --
never a zeo_core function under test.
"""

from unittest.mock import MagicMock, patch

import pytest
from zeo_core.core.errors import ZeoIntegrationError
from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.llms.models import ChatMessage, RoleType
from zeo_core.integrations.llms.service import (
    LLMIntegration,
    check_llm_dependencies,
)

from ..mocks.clients import MockClient


class TestCheckLlmDependenciesLocal:
    """The service/__init__.py-local check_llm_dependencies (not the
    service/dependencies.py twin, already covered by
    test_dependencies.py -- these two functions are separately defined,
    byte-similar but not identical (this one catches
    requests.exceptions.RequestException narrowly; the twin catches a
    broad Exception), so each needs its own coverage."""

    def test_all_missing(self) -> None:
        with patch("importlib.util.find_spec", return_value=None):
            success, message, providers = check_llm_dependencies()
            assert success is False
            assert "No LLM providers available" in message
            assert providers == ["mock"]

    def test_some_missing(self) -> None:
        def fake_find_spec(name: str) -> MagicMock | None:
            if name == "openai":
                return MagicMock()
            return None

        with patch("importlib.util.find_spec", side_effect=fake_find_spec):
            success, message, providers = check_llm_dependencies()
            assert success is True
            assert set(providers) == {"openai", "mock"}

    def test_ollama_connection_refused_narrow_exception(self) -> None:
        """The narrow requests.exceptions.RequestException catch (this
        function's own distinguishing behavior vs. its dependencies.py
        twin) -- a real, importable exception type, not a generic one."""
        import requests

        with patch("importlib.util.find_spec", return_value=MagicMock()):
            with patch(
                "requests.get",
                side_effect=requests.exceptions.ConnectionError("refused"),
            ):
                success, message, providers = check_llm_dependencies()
                assert success is True
                assert "ollama" not in providers

    def test_ollama_available(self) -> None:
        with patch("importlib.util.find_spec", return_value=MagicMock()):
            with patch(
                "requests.get", return_value=MagicMock(status_code=200)
            ) as mock_get:
                success, message, providers = check_llm_dependencies()
                assert success is True
                assert "ollama" in providers
                mock_get.assert_called_once_with(
                    "http://localhost:11434/api/version", timeout=1
                )

    def test_ollama_non_200_status_not_added(self) -> None:
        with patch("importlib.util.find_spec", return_value=MagicMock()):
            with patch("requests.get", return_value=MagicMock(status_code=500)):
                success, message, providers = check_llm_dependencies()
                assert "ollama" not in providers


class TestLLMIntegrationExtractConfig:
    """_extract_config branches not already covered by
    test_service.py::test_extract_config (the config_provider-missing
    guard, the DataResult .data branch, the load-exception fallback, and
    the invalid-config-raises branch)."""

    def test_no_config_provider_raises(self) -> None:
        service = LLMIntegration()
        service.config = None
        service.config_provider = None
        with pytest.raises(
            ZeoIntegrationError, match="Configuration provider not initialized"
        ):
            service._extract_config()

    def test_config_result_data_attribute_branch(self) -> None:
        """hasattr(config_result, 'data') branch -- a DataResult-shaped
        result rather than a ConfigResult-shaped one."""
        service = LLMIntegration()
        service.config = None
        service.config_provider = MagicMock()
        data_result = MagicMock()
        data_result.success = True
        data_result.content = None
        data_result.data = {"default_provider": "anthropic"}
        service.config_provider.load_config.return_value = data_result

        config = service._extract_config()
        assert config["default_provider"] == "anthropic"

    def test_config_result_success_but_empty_falls_back_to_default(self) -> None:
        service = LLMIntegration()
        service.config = None
        service.config_provider = MagicMock()
        empty_result = MagicMock()
        empty_result.success = True
        empty_result.content = None
        empty_result.data = None
        service.config_provider.load_config.return_value = empty_result
        service.config_provider.get_default_config.return_value = {
            "default_provider": "mock"
        }

        config = service._extract_config()
        assert config["default_provider"] == "mock"

    def test_config_result_failure_falls_back_to_default(self) -> None:
        """config_result.success is False (not an exception -- a clean,
        explicit failure), the plain else branch at line 152."""
        service = LLMIntegration()
        service.config = None
        service.config_provider = MagicMock()
        failed_result = MagicMock()
        failed_result.success = False
        service.config_provider.load_config.return_value = failed_result
        service.config_provider.get_default_config.return_value = {
            "default_provider": "mock"
        }

        config = service._extract_config()
        assert config["default_provider"] == "mock"

    def test_load_config_raises_falls_back_to_default(self) -> None:
        service = LLMIntegration()
        service.config = None
        service.config_provider = MagicMock()
        service.config_provider.load_config.side_effect = RuntimeError("boom")
        service.config_provider.get_default_config.return_value = {
            "default_provider": "mock"
        }

        config = service._extract_config()
        assert config["default_provider"] == "mock"

    def test_invalid_config_raises_zeo_integration_error(self) -> None:
        service = LLMIntegration()
        # An LLMConfig field that fails pydantic validation.
        service.config = {"timeout": "not-a-number-and-not-coercible-????"}
        with pytest.raises(ZeoIntegrationError, match="Invalid LLM configuration"):
            service._extract_config()


class TestLLMIntegrationInitializeBranches:
    """initialize()'s own branches: super().initialize() failing,
    invalid fallback config falling back to single-provider init, and the
    two outer exception handlers."""

    def test_super_initialize_failure_short_circuits(self) -> None:
        service = LLMIntegration()
        service.config = {"default_provider": "mock"}
        with patch(
            "zeo_core.integrations.core.base.BaseIntegrationService.initialize"
        ) as mock_super_init:
            mock_super_init.return_value = IntegrationResult(
                success=False, error="base init failed"
            )
            result = service.initialize()
            assert result.success is False
            assert result.error is not None
            assert "base init failed" in result.error

    def test_invalid_fallback_config_warns_and_uses_single_provider(self) -> None:
        """A None-valued 'fallback' key is valid per LLMConfig's own field
        type (FallbackConfig | None), so _extract_config's validation
        passes -- but initialize()'s own separate `if "fallback" in
        llm_config` check only tests key PRESENCE, not truthiness, then
        tries FallbackConfig(**None), which raises TypeError ('argument
        after ** must be a mapping, not NoneType', confirmed live this
        session). Caught by initialize()'s own broad except Exception,
        correctly falling back to single-provider init -- this is the one
        real, reachable way to exercise lines 190-197's except branch,
        since any dict shape that fails FallbackConfig(**...) directly
        also fails LLMConfig's OWN nested fallback validation first
        (confirmed live: identical pydantic strictness), making that more
        obvious-looking case actually unreachable via this path."""
        service = LLMIntegration(enable_fallback=True)
        service.config = {
            "default_provider": "mock",
            "fallback": None,
        }
        with patch(
            "zeo_core.integrations.llms.registry.get_llm_client"
        ) as mock_get_client:
            mock_get_client.return_value = MagicMock()
            result = service.initialize()
            # Proves the except branch ran (the warning fired, confirmed
            # separately) and control genuinely fell through to
            # _initialize_single_provider rather than _initialize_with_fallback
            # -- get_llm_client is single-provider init's own call, never
            # made by the fallback path.
            assert result.success is True
            mock_get_client.assert_called_once()

    def test_extract_config_zeo_integration_error_is_caught(self) -> None:
        service = LLMIntegration()
        service.config = {"timeout": "not-a-number-and-not-coercible-????"}
        result = service.initialize()
        assert result.success is False
        assert result.error is not None
        assert "Invalid LLM configuration" in result.error

    def test_valid_fallback_config_dispatches_to_fallback_init(self) -> None:
        """A genuinely valid fallback dict: _extract_config's LLMConfig
        validation passes AND initialize()'s own separate
        FallbackConfig(**llm_config["fallback"]) construction also
        succeeds (lines 190-195's happy path), so initialize() dispatches
        to _initialize_with_fallback (line 206) rather than
        _initialize_single_provider. Using only the 'mock' provider keeps
        this inside zeo_core's own boundary per RULING-235."""
        service = LLMIntegration(enable_fallback=True)
        service.config = {
            "default_provider": "mock",
            "fallback": {"providers": ["mock"]},
        }
        with patch.object(
            service,
            "_initialize_with_fallback",
            wraps=service._initialize_with_fallback,
        ) as spy_fallback_init:
            result = service.initialize()
            assert result.success is True
            spy_fallback_init.assert_called_once()

    def test_unexpected_exception_during_initialize_is_caught(self) -> None:
        service = LLMIntegration()
        service.config = {"default_provider": "mock"}
        with patch.object(
            service, "_extract_config", side_effect=RuntimeError("unexpected")
        ):
            result = service.initialize()
            assert result.success is False
            assert result.error is not None
            assert "Failed to initialize LLM integration" in result.error


class TestLLMIntegrationSingleProviderFallbackBranches:
    """_initialize_single_provider's provider-unavailable branches: falls
    back to another available real provider, and falls back to mock when
    none are available -- plus the anthropic/ollama provider-specific
    client_args branches and the get_llm_client-raises-fallback-to-mock
    branch."""

    def test_requested_provider_unavailable_falls_back_to_first_available(
        self,
    ) -> None:
        service = LLMIntegration(provider="does-not-exist")
        service.config = {"default_provider": "does-not-exist"}
        with patch(
            "zeo_core.integrations.llms.registry.get_llm_client"
        ) as mock_get_client:
            mock_get_client.return_value = MagicMock()
            result = service._initialize_single_provider(
                service.config, ["anthropic", "mock"]
            )
            assert result.success is True
            assert service._using_mock is False
            # provider fell back to anthropic (first match in the
            # ["openai", "anthropic", "ollama"] preference order present
            # in available_providers)
            assert result.message is not None
            assert "anthropic" in result.message

    def test_no_real_providers_available_falls_back_to_mock(self) -> None:
        service = LLMIntegration(provider="does-not-exist")
        service.config = {"default_provider": "does-not-exist"}
        result = service._initialize_single_provider(service.config, ["mock"])
        assert result.success is True
        assert service._using_mock is True
        assert isinstance(service.client, object)

    def test_anthropic_provider_specific_args(self) -> None:
        service = LLMIntegration(provider="anthropic")
        service.config = {"default_provider": "anthropic", "anthropic": {}}
        with patch(
            "zeo_core.integrations.llms.registry.get_llm_client"
        ) as mock_get_client:
            mock_get_client.return_value = MagicMock()
            service._initialize_single_provider(service.config, ["anthropic"])
            _, kwargs = mock_get_client.call_args
            assert "api_base" in kwargs

    def test_ollama_provider_specific_args(self) -> None:
        service = LLMIntegration(provider="ollama")
        service.config = {"default_provider": "ollama", "ollama": {}}
        with patch(
            "zeo_core.integrations.llms.registry.get_llm_client"
        ) as mock_get_client:
            mock_get_client.return_value = MagicMock()
            service._initialize_single_provider(service.config, ["ollama"])
            _, kwargs = mock_get_client.call_args
            assert "api_base" in kwargs

    def test_get_llm_client_raises_falls_back_to_mock_client(self) -> None:
        service = LLMIntegration(provider="openai")
        service.config = {"default_provider": "openai", "openai": {}}
        with patch(
            "zeo_core.integrations.llms.registry.get_llm_client",
            side_effect=ZeoIntegrationError("no api key"),
        ):
            result = service._initialize_single_provider(service.config, ["openai"])
            assert result.success is True
            assert service._using_mock is True
            assert result.message is not None
            assert "using mock client" in result.message


class TestLLMIntegrationWithFallback:
    """_initialize_with_fallback -- essentially fully uncovered before
    this round. Uses only the 'mock' provider (no external deps) so the
    real FallbackLLMClient/MockLLMClient construction stays inside
    zeo_core's own boundary, per RULING-235 (mock the SDK/network edge,
    not zeo_core code)."""

    def test_fallback_with_only_mock_provider(self) -> None:
        from zeo_core.integrations.llms.fallback import FallbackConfig

        service = LLMIntegration(enable_fallback=True)
        service.config = {"default_provider": "mock", "mock": {}}
        fallback_config = FallbackConfig(providers=["mock"])

        result = service._initialize_with_fallback(
            service.config, fallback_config, ["mock"]
        )
        assert result.success is True
        assert service._using_mock is True
        assert service._fallback_client is not None
        assert service.client is service._fallback_client
        assert service._initialized is True

    def test_fallback_appends_mock_when_absent_from_providers(self) -> None:
        from zeo_core.integrations.llms.fallback import FallbackConfig

        service = LLMIntegration(enable_fallback=True)
        service.config = {"default_provider": "mock"}
        # fallback_config lists providers not in available_providers at all;
        # they should be filtered out and 'mock' appended as last resort.
        fallback_config = FallbackConfig(providers=["openai", "anthropic"])

        result = service._initialize_with_fallback(
            service.config, fallback_config, ["mock"]
        )
        assert result.success is True
        assert service._using_mock is True

    def test_fallback_requested_provider_uses_explicit_model_and_key(self) -> None:
        """provider == self.provider branches for model_map/api_key_map
        (lines ~348-361), matching only against the 'mock' provider so no
        real SDK client is constructed."""
        from zeo_core.integrations.llms.fallback import FallbackConfig

        service = LLMIntegration(
            provider="mock", model="explicit-model", api_key="explicit-key"
        )
        service.config = {"default_provider": "mock"}
        fallback_config = FallbackConfig(providers=["mock"])

        result = service._initialize_with_fallback(
            service.config, fallback_config, ["mock"]
        )
        assert result.success is True

    def test_fallback_openai_and_anthropic_provider_args_branches(self) -> None:
        """_initialize_with_fallback's OWN openai/anthropic-or-ollama
        provider_args branches (lines ~366-374) -- distinct from
        _initialize_single_provider's equivalent branches, already
        covered separately above. FallbackLLMClient.__init__ does not
        eagerly construct provider SDK clients (confirmed live this
        session: it only stores config/maps, real client construction is
        lazy via _get_client_for_provider), so passing real provider
        names here stays inside zeo_core's own boundary per RULING-235
        -- no real network/SDK call is made."""
        from zeo_core.integrations.llms.fallback import FallbackConfig

        service = LLMIntegration(enable_fallback=True)
        service.config = {
            "default_provider": "openai",
            "openai": {"api_base": "https://example.invalid", "organization": "org1"},
            "anthropic": {"api_base": "https://example.invalid"},
        }
        fallback_config = FallbackConfig(providers=["openai", "anthropic", "mock"])

        result = service._initialize_with_fallback(
            service.config, fallback_config, ["openai", "anthropic", "mock"]
        )
        assert result.success is True
        assert service._fallback_client is not None
        assert service._fallback_client._provider_args["openai"] == {
            "api_base": "https://example.invalid",
            "organization": "org1",
        }
        assert service._fallback_client._provider_args["anthropic"] == {
            "api_base": "https://example.invalid",
        }

    def test_fallback_client_construction_raises_falls_back_to_single_provider(
        self,
    ) -> None:
        from zeo_core.integrations.llms.fallback import FallbackConfig

        service = LLMIntegration(enable_fallback=True)
        service.config = {"default_provider": "mock"}
        fallback_config = FallbackConfig(providers=["mock"])

        with patch(
            "zeo_core.integrations.llms.fallback.FallbackLLMClient",
            side_effect=RuntimeError("construction failed"),
        ):
            result = service._initialize_with_fallback(
                service.config, fallback_config, ["mock"]
            )
            # Falls back to _initialize_single_provider, which succeeds
            # via the real MockLLMClient (no provider available -> mock).
            assert result.success is True
            assert service._using_mock is True


class TestLLMIntegrationChatCountTokensNoneClient:
    """chat()/count_tokens()'s own 'client not initialized' branches
    (self.client is falsy after _ensure_initialized already passed) and
    the mock-note-appended branches."""

    def test_chat_with_no_client_after_init(self) -> None:
        service = LLMIntegration()
        service._initialized = True
        service.client = None
        result = service.chat([ChatMessage(role=RoleType.USER, content="hi")])
        assert result.success is False
        assert result.error is not None
        assert "LLM client not initialized" in result.error

    def test_count_tokens_with_no_client_after_init(self) -> None:
        service = LLMIntegration()
        service._initialized = True
        service.client = None
        result = service.count_tokens([ChatMessage(role=RoleType.USER, content="hi")])
        assert result.success is False
        assert result.error is not None
        assert "LLM client not initialized" in result.error

    def test_chat_mock_note_appended_when_using_mock(self) -> None:
        service = LLMIntegration()
        service._initialized = True
        service._using_mock = True
        service.client = MockClient(responses=["hello"])
        result = service.chat([ChatMessage(role=RoleType.USER, content="hi")])
        assert result.success is True
        assert result.message is not None
        assert "using mock LLM" in result.message

    def test_count_tokens_mock_note_appended_when_using_mock(self) -> None:
        service = LLMIntegration()
        service._initialized = True
        service._using_mock = True
        service.client = MockClient(token_counts=[7])
        result = service.count_tokens([ChatMessage(role=RoleType.USER, content="hi")])
        assert result.success is True
        assert result.message is not None
        assert "using mock estimation" in result.message


class TestLLMIntegrationProviderStatusAndMockFlag:
    """get_provider_status, reset_provider_status, and is_using_mock --
    both the fallback-client-present and fallback-client-absent branches
    of each."""

    def test_get_provider_status_none_when_no_fallback_client(self) -> None:
        service = LLMIntegration()
        assert service._fallback_client is None
        assert service.get_provider_status() is None

    def test_get_provider_status_returns_dumped_status_list(self) -> None:
        service = LLMIntegration()
        status_a = MagicMock()
        status_a.model_dump.return_value = {"provider": "mock", "available": True}
        fake_fallback_client = MagicMock()
        fake_fallback_client.get_provider_status.return_value = [status_a]
        service._fallback_client = fake_fallback_client

        result = service.get_provider_status()
        assert result == [{"provider": "mock", "available": True}]

    def test_reset_provider_status_false_when_no_fallback_client(self) -> None:
        service = LLMIntegration()
        assert service.reset_provider_status() is False

    def test_reset_provider_status_true_and_delegates(self) -> None:
        service = LLMIntegration()
        fake_fallback_client = MagicMock()
        service._fallback_client = fake_fallback_client

        assert service.reset_provider_status() is True
        fake_fallback_client.reset_provider_status.assert_called_once()

    def test_is_using_mock_property_reflects_internal_flag(self) -> None:
        service = LLMIntegration()
        assert service.is_using_mock is False
        service._using_mock = True
        assert service.is_using_mock is True
