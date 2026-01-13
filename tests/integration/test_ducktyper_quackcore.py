# === QV-LLM:BEGIN ===
# path: tests/integration/test_ducktyper_quackcore.py
# role: module
# neighbors: __init__.py, conftest.py
# exports: test_ducktyper_can_list_quackcore_plugins
# git_branch: feat/9-make-setup-work
# git_commit: 9bcf4e79
# === QV-LLM:END ===

import pytest
from quack_core.modules.registry import list_plugins, get_plugin
from quack_chat.commands.list_cmd import list_tools


def test_ducktyper_can_list_quackcore_plugins():
    """Test that DuckTyper can list modules from quack_core."""
    # Get modules directly from QuackCore
    direct_plugins = list_plugins()

    # Get modules through DuckTyper's list command
    # This is simplified and would need adaptation to match how list_cmd works
    ducktyper_plugins = list_tools(ctx=None)

    # Verify that all QuackCore modules are available through DuckTyper
    assert len(direct_plugins) > 0
    for plugin in direct_plugins:
        assert plugin.name in [p.name for p in ducktyper_plugins]