# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_paths/test_paths_plugin.py
# === QV-LLM:END ===

"""
Tests for quack_core.core.paths.plugin (0% covered before this file).

QuackPathsPlugin is a thin adapter delegating to PathResolver's own
_get_project_root/_detect_project_context/_detect_content_context (each
independently covered by resolver-focused tests elsewhere in this suite).
Per RULING-235, the resolver itself is real quack_core logic, not an
external boundary -- but exercising its full filesystem-walking behavior
is out of scope for THIS unit (the plugin's own job: does it forward
start_dir correctly, including through _normalize_path_param, and return
whatever the resolver gives back). So the resolver's three methods are
mocked here, the same "thin wrapper" scope discipline as
test_config_plugin.py uses for QuackConfigPlugin.
"""

from unittest.mock import MagicMock, patch

from quack_core.core.fs import DataResult, PathResult
from quack_core.core.paths.models import ContentContext, ProjectContext
from quack_core.core.paths.plugin import QuackPathsPlugin, create_plugin


class TestQuackPathsPluginName:
    def test_name_property(self) -> None:
        plugin = QuackPathsPlugin()
        assert plugin.name == "paths"


class TestFindProjectRoot:
    def test_none_start_dir_passes_none_through(self) -> None:
        plugin = QuackPathsPlugin()
        with patch.object(
            plugin._resolver, "_get_project_root", return_value="/root"
        ) as mock_get_root:
            result = plugin.find_project_root(start_dir=None)

        mock_get_root.assert_called_once_with(None)
        assert result == "/root"

    def test_string_start_dir_normalized_and_forwarded(self) -> None:
        plugin = QuackPathsPlugin()
        with patch.object(
            plugin._resolver, "_get_project_root", return_value="/root"
        ) as mock_get_root:
            plugin.find_project_root(start_dir="/some/dir")

        mock_get_root.assert_called_once_with("/some/dir")

    def test_path_result_start_dir_unwraps_via_normalize(self) -> None:
        plugin = QuackPathsPlugin()
        path_result = PathResult(ok=True, path="/unwrapped/dir")
        with patch.object(
            plugin._resolver, "_get_project_root", return_value="/root"
        ) as mock_get_root:
            plugin.find_project_root(start_dir=path_result)

        mock_get_root.assert_called_once_with("/unwrapped/dir")

    def test_data_result_start_dir_unwraps_via_normalize(self) -> None:
        plugin = QuackPathsPlugin()
        data_result = DataResult(ok=True, data="/data/dir")
        with patch.object(
            plugin._resolver, "_get_project_root", return_value="/root"
        ) as mock_get_root:
            plugin.find_project_root(start_dir=data_result)

        mock_get_root.assert_called_once_with("/data/dir")


class TestDetectProjectContext:
    def test_none_start_dir(self) -> None:
        plugin = QuackPathsPlugin()
        fake_context = MagicMock(spec=ProjectContext)
        with patch.object(
            plugin._resolver, "_detect_project_context", return_value=fake_context
        ) as mock_detect:
            result = plugin.detect_project_context(start_dir=None)

        mock_detect.assert_called_once_with(None)
        assert result is fake_context

    def test_string_start_dir_forwarded(self) -> None:
        plugin = QuackPathsPlugin()
        fake_context = MagicMock(spec=ProjectContext)
        with patch.object(
            plugin._resolver, "_detect_project_context", return_value=fake_context
        ) as mock_detect:
            plugin.detect_project_context(start_dir="/proj")

        mock_detect.assert_called_once_with("/proj")


class TestDetectContentContext:
    def test_none_start_dir_and_no_content_type(self) -> None:
        plugin = QuackPathsPlugin()
        fake_context = MagicMock(spec=ContentContext)
        with patch.object(
            plugin._resolver, "_detect_content_context", return_value=fake_context
        ) as mock_detect:
            result = plugin.detect_content_context(start_dir=None, content_type=None)

        mock_detect.assert_called_once_with(None, None)
        assert result is fake_context

    def test_string_start_dir_and_content_type_forwarded(self) -> None:
        plugin = QuackPathsPlugin()
        fake_context = MagicMock(spec=ContentContext)
        with patch.object(
            plugin._resolver, "_detect_content_context", return_value=fake_context
        ) as mock_detect:
            plugin.detect_content_context(start_dir="/proj", content_type="video")

        mock_detect.assert_called_once_with("/proj", "video")


class TestCreatePlugin:
    def test_create_plugin_returns_fresh_quack_paths_plugin(self) -> None:
        plugin = create_plugin()
        assert isinstance(plugin, QuackPathsPlugin)
        assert plugin.name == "paths"
