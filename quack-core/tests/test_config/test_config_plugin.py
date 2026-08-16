# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_config/test_config_plugin.py
# === QV-LLM:END ===

"""
Tests for quack_core.config.plugin (0% covered before this file).

No external boundary here worth mocking per RULING-235 -- QuackConfigPlugin
is a thin lazy wrapper delegating to load_config/merge_configs/get_config_value,
all real quack_core code. The only collaborator worth stubbing is load_config
itself, since exercising the real config-file-discovery path is out of scope
for this unit (it's covered elsewhere, e.g. test_loader.py for config).
"""

from unittest.mock import patch

from quack_core.config.models import GeneralConfig, PathsConfig, QuackConfig
from quack_core.config.plugin import QuackConfigPlugin, create_plugin


class TestQuackConfigPluginLazyInit:
    def test_construction_does_not_load_config(self) -> None:
        plugin = QuackConfigPlugin()
        assert plugin._config is None

    def test_name_property(self) -> None:
        plugin = QuackConfigPlugin()
        assert plugin.name == "config"


class TestQuackConfigPluginBeforeLoad:
    """get_value/get_base_dir/get_output_dir before load_config() -- the
    'strict kernel philosophy' branch (raise, don't auto-load)."""

    def test_get_value_before_load_raises(self) -> None:
        plugin = QuackConfigPlugin()
        try:
            plugin.get_value("general.project_name")
            raise AssertionError("expected RuntimeError")
        except RuntimeError as e:
            assert "has not been loaded yet" in str(e)

    def test_get_base_dir_before_load_raises(self) -> None:
        plugin = QuackConfigPlugin()
        try:
            plugin.get_base_dir()
            raise AssertionError("expected RuntimeError")
        except RuntimeError as e:
            assert "Config not loaded" in str(e)

    def test_get_output_dir_before_load_raises(self) -> None:
        plugin = QuackConfigPlugin()
        try:
            plugin.get_output_dir()
            raise AssertionError("expected RuntimeError")
        except RuntimeError as e:
            assert "Config not loaded" in str(e)


class TestQuackConfigPluginAfterLoad:
    def _config(self) -> QuackConfig:
        return QuackConfig(
            general=GeneralConfig(project_name="TestProject"),
            paths=PathsConfig(base_dir="/base", output_dir="/base/output"),
        )

    def test_load_config_delegates_and_caches(self) -> None:
        plugin = QuackConfigPlugin()
        fake_config = self._config()

        with patch(
            "quack_core.config.plugin.load_config", return_value=fake_config
        ) as mock_load:
            result = plugin.load_config(
                config_path="/some/path.yaml", merge_env=False, merge_defaults=False
            )

        mock_load.assert_called_once_with(
            config_path="/some/path.yaml", merge_env=False, merge_defaults=False
        )
        assert result is fake_config
        assert plugin._config is fake_config

    def test_get_value_after_load_delegates_to_get_config_value(self) -> None:
        plugin = QuackConfigPlugin()
        with patch(
            "quack_core.config.plugin.load_config", return_value=self._config()
        ):
            plugin.load_config()

        assert plugin.get_value("general.project_name") == "TestProject"

    def test_get_value_returns_default_for_missing_path(self) -> None:
        plugin = QuackConfigPlugin()
        with patch(
            "quack_core.config.plugin.load_config", return_value=self._config()
        ):
            plugin.load_config()

        assert plugin.get_value("general.nonexistent", default="fallback") == "fallback"

    def test_get_base_dir_after_load(self) -> None:
        plugin = QuackConfigPlugin()
        with patch(
            "quack_core.config.plugin.load_config", return_value=self._config()
        ):
            plugin.load_config()

        assert plugin.get_base_dir() == "/base"

    def test_get_output_dir_after_load(self) -> None:
        plugin = QuackConfigPlugin()
        with patch(
            "quack_core.config.plugin.load_config", return_value=self._config()
        ):
            plugin.load_config()

        assert plugin.get_output_dir() == "/base/output"

    def test_merge_configs_delegates_to_module_function(self) -> None:
        plugin = QuackConfigPlugin()
        base = self._config()
        merged = self._config()
        merged.general.project_name = "Merged"

        with patch(
            "quack_core.config.plugin.merge_configs", return_value=merged
        ) as mock_merge:
            result = plugin.merge_configs(base, {"general": {"project_name": "Merged"}})

        mock_merge.assert_called_once_with(
            base, {"general": {"project_name": "Merged"}}
        )
        assert result is merged


class TestCreatePlugin:
    def test_create_plugin_returns_fresh_quack_config_plugin(self) -> None:
        plugin = create_plugin()
        assert isinstance(plugin, QuackConfigPlugin)
        assert plugin.name == "config"
        assert plugin._config is None
