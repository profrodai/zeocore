"""
Tests for quack_core.prompt.plugin (0% covered before this file).

PromptPlugin is a thin adapter over PromptService. Per RULING-235, the
service's own render/strategy logic is real quack_core code with its own
dedicated test coverage elsewhere in this suite (test_service.py) -- this
file's job is only to prove the plugin forwards correctly and exposes the
underlying service, so PromptService itself is mocked here (scope
discipline, same pattern as test_config_plugin.py / test_paths_plugin.py).
"""

from unittest.mock import MagicMock, patch

from quack_core.prompt.api.public.results import PromptRenderResult
from quack_core.prompt.plugin import PromptPlugin, create_plugin
from quack_core.prompt.service import PromptService


class TestPromptPluginConstruction:
    def test_name_is_prompt(self) -> None:
        with patch("quack_core.prompt.plugin.PromptService"):
            plugin = PromptPlugin()
        assert plugin.name == "prompt"

    def test_constructs_prompt_service_with_load_defaults_true(self) -> None:
        with patch("quack_core.prompt.plugin.PromptService") as mock_service_cls:
            PromptPlugin()
        mock_service_cls.assert_called_once_with(load_defaults=True)


class TestPromptPluginRender:
    def test_render_forwards_raw_prompt_and_kwargs_to_service(self) -> None:
        fake_result = MagicMock(spec=PromptRenderResult)
        with patch("quack_core.prompt.plugin.PromptService") as mock_service_cls:
            mock_service = mock_service_cls.return_value
            mock_service.render.return_value = fake_result
            plugin = PromptPlugin()

            result = plugin.render("Summarize this", tags=["summary"], strategy="cot")

        mock_service.render.assert_called_once_with(
            "Summarize this", tags=["summary"], strategy="cot"
        )
        assert result is fake_result

    def test_render_with_no_extra_kwargs(self) -> None:
        fake_result = MagicMock(spec=PromptRenderResult)
        with patch("quack_core.prompt.plugin.PromptService") as mock_service_cls:
            mock_service = mock_service_cls.return_value
            mock_service.render.return_value = fake_result
            plugin = PromptPlugin()

            plugin.render("Just the raw prompt")

        mock_service.render.assert_called_once_with("Just the raw prompt")


class TestPromptPluginGetService:
    def test_get_service_returns_the_underlying_service_instance(self) -> None:
        with patch("quack_core.prompt.plugin.PromptService") as mock_service_cls:
            mock_service = mock_service_cls.return_value
            plugin = PromptPlugin()

            assert plugin.get_service() is mock_service


class TestCreatePlugin:
    def test_create_plugin_returns_real_prompt_plugin(self) -> None:
        # Exercise the real, unmocked PromptService construction path once
        # here so create_plugin's own wiring is proven end to end (it is a
        # thin factory -- the plugin construction itself is otherwise
        # mocked throughout this file for scope discipline).
        plugin = create_plugin()
        assert isinstance(plugin, PromptPlugin)
        assert plugin.name == "prompt"
        assert isinstance(plugin.get_service(), PromptService)
