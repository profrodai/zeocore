# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_plugins/test_protocols.py
# role: tests
# neighbors: __init__.py, test_discovery.py, test_explicit_loading.py, test_registry.py
# exports: SamplePlugin, SampleCommandPlugin, SampleWorkflowPlugin, SampleExtensionPlugin, SampleProviderPlugin, SampleConfigurablePlugin, SampleMixedPlugin, SampleProtocols
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===

"""
Tests for plugin protocol interfaces.
"""

from collections.abc import Callable
from typing import Any

import pytest
from quack_core.modules.protocols import (
    CommandPluginProtocol,
    ConfigurablePluginProtocol,
    ExtensionPluginProtocol,
    ProviderPluginProtocol,
    QuackPluginProtocol,
    WorkflowPluginProtocol,
)


# Test implementations of each protocol
class SamplePlugin(QuackPluginProtocol):
    """Test implementation of QuackPluginProtocol."""

    @property
    def name(self) -> str:
        return "test_plugin"


class SampleCommandPlugin(CommandPluginProtocol):
    """Test implementation of CommandPluginProtocol."""

    @property
    def name(self) -> str:
        return "test_command_plugin"

    def list_commands(self) -> list[str]:
        return ["cmd1", "cmd2"]

    def get_command(self, name: str) -> Callable | None:
        if name in self.list_commands():
            return lambda *args, **kwargs: f"Executed {name}"
        return None

    def execute_command(self, name: str, *args: object, **kwargs: object) -> str:
        cmd = self.get_command(name)
        if cmd:
            return cmd(*args, **kwargs)
        raise ValueError(f"Command {name} not found")


class SampleWorkflowPlugin(WorkflowPluginProtocol):
    """Test implementation of WorkflowPluginProtocol."""

    @property
    def name(self) -> str:
        return "test_workflow_plugin"

    def list_workflows(self) -> list[str]:
        return ["flow1", "flow2"]

    def get_workflow(self, name: str) -> Callable | None:
        if name in self.list_workflows():
            return lambda *args, **kwargs: f"Ran {name}"
        return None

    def execute_workflow(self, name: str, *args: object, **kwargs: object) -> str:
        wf = self.get_workflow(name)
        if wf:
            return wf(*args, **kwargs)
        raise ValueError(f"Workflow {name} not found")


class SampleExtensionPlugin(ExtensionPluginProtocol):
    """Test implementation of ExtensionPluginProtocol."""

    @property
    def name(self) -> str:
        return "test_extension_plugin"

    def get_target_plugin(self) -> str:
        return "target_plugin"

    def get_extensions(self) -> dict[str, Callable]:
        return {"ext1": lambda: "Extension 1", "ext2": lambda: "Extension 2"}


class SampleProviderPlugin(ProviderPluginProtocol):
    """Test implementation of ProviderPluginProtocol."""

    @property
    def name(self) -> str:
        return "test_provider_plugin"

    def get_services(self) -> dict[str, object]:
        return {"service1": "Service 1", "service2": "Service 2"}

    def get_service(self, name: str) -> object | None:
        return self.get_services().get(name)


class SampleConfigurablePlugin(ConfigurablePluginProtocol):
    """Test implementation of ConfigurablePluginProtocol."""

    def __init__(self) -> None:
        """Initialize with default configuration."""
        self._config: dict[str, Any] = {}  # Use Any for typing

    @property
    def name(self) -> str:
        return "test_configurable_plugin"

    def configure(self, config: dict[str, Any]) -> None:  # Use Any here
        self._config = config

    def get_config_schema(self) -> dict[str, Any]:  # Use Any here
        return {
            "settings": {
                "type": "object",
                "properties": {
                    "option1": {"type": "string"},
                    "option2": {"type": "integer"},
                },
            }
        }

    def validate_config(
        self, config: dict[str, Any]
    ) -> tuple[bool, list[str]]:  # Use Any here
        errors = []

        if "settings" not in config:
            errors.append("Missing 'settings' key")
        elif not isinstance(config["settings"], dict):
            errors.append("'settings' must be an object")
        else:
            settings = config["settings"]
            # Use safer dictionary access with .get()
            if "option1" in settings and not isinstance(settings.get("option1"), str):
                errors.append("'option1' must be a string")
            if "option2" in settings and not isinstance(settings.get("option2"), int):
                errors.append("'option2' must be an integer")

        return len(errors) == 0, errors


class SampleMixedPlugin(CommandPluginProtocol, WorkflowPluginProtocol):
    """Test implementation mixing multiple protocols."""

    @property
    def name(self) -> str:
        return "test_mixed_plugin"

    def list_commands(self) -> list[str]:
        return ["cmd1", "cmd2"]

    def get_command(self, name: str) -> Callable | None:
        if name in self.list_commands():
            return lambda *args, **kwargs: f"Executed {name}"
        return None

    def execute_command(self, name: str, *args: object, **kwargs: object) -> str:
        cmd = self.get_command(name)
        if cmd:
            return cmd(*args, **kwargs)
        raise ValueError(f"Command {name} not found")

    def list_workflows(self) -> list[str]:
        return ["flow1", "flow2"]

    def get_workflow(self, name: str) -> Callable | None:
        if name in self.list_workflows():
            return lambda *args, **kwargs: f"Ran {name}"
        return None

    def execute_workflow(self, name: str, *args: object, **kwargs: object) -> str:
        wf = self.get_workflow(name)
        if wf:
            return wf(*args, **kwargs)
        raise ValueError(f"Workflow {name} not found")


class SampleProtocols:
    """Tests for plugin protocols."""

    def test_basic_plugin_protocol(self) -> None:
        """Test the base QuackPluginProtocol."""
        plugin = SamplePlugin()

        # Test protocol conformance
        assert isinstance(plugin, QuackPluginProtocol)

        # Test properties
        assert plugin.name == "test_plugin"

    def test_command_plugin_protocol(self) -> None:
        """Test the CommandPluginProtocol."""
        plugin = SampleCommandPlugin()

        # Test protocol conformance
        assert isinstance(plugin, QuackPluginProtocol)
        assert isinstance(plugin, CommandPluginProtocol)

        # Test methods
        assert plugin.name == "test_command_plugin"
        assert plugin.list_commands() == ["cmd1", "cmd2"]
        assert callable(plugin.get_command("cmd1"))
        assert plugin.get_command("nonexistent") is None

        # Test command execution
        assert plugin.execute_command("cmd1") == "Executed cmd1"
        with pytest.raises(ValueError):
            plugin.execute_command("nonexistent")

    def test_workflow_plugin_protocol(self) -> None:
        """Test the WorkflowPluginProtocol."""
        plugin = SampleWorkflowPlugin()

        # Test protocol conformance
        assert isinstance(plugin, QuackPluginProtocol)
        assert isinstance(plugin, WorkflowPluginProtocol)

        # Test methods
        assert plugin.name == "test_workflow_plugin"
        assert plugin.list_workflows() == ["flow1", "flow2"]
        assert callable(plugin.get_workflow("flow1"))
        assert plugin.get_workflow("nonexistent") is None

        # Test workflow execution
        assert plugin.execute_workflow("flow1") == "Ran flow1"
        with pytest.raises(ValueError):
            plugin.execute_workflow("nonexistent")

    def test_extension_plugin_protocol(self) -> None:
        """Test the ExtensionPluginProtocol."""
        plugin = SampleExtensionPlugin()

        # Test protocol conformance
        assert isinstance(plugin, QuackPluginProtocol)
        assert isinstance(plugin, ExtensionPluginProtocol)

        # Test methods
        assert plugin.name == "test_extension_plugin"
        assert plugin.get_target_plugin() == "target_plugin"

        extensions = plugin.get_extensions()
        assert len(extensions) == 2
        assert "ext1" in extensions
        assert "ext2" in extensions
        assert callable(extensions["ext1"])
        assert callable(extensions["ext2"])
        assert extensions["ext1"]() == "Extension 1"
        assert extensions["ext2"]() == "Extension 2"

    def test_provider_plugin_protocol(self) -> None:
        """Test the ProviderPluginProtocol."""
        plugin = SampleProviderPlugin()

        # Test protocol conformance
        assert isinstance(plugin, QuackPluginProtocol)
        assert isinstance(plugin, ProviderPluginProtocol)

        # Test methods
        assert plugin.name == "test_provider_plugin"

        services = plugin.get_services()
        assert len(services) == 2
        assert "service1" in services
        assert "service2" in services

        assert plugin.get_service("service1") == "Service 1"
        assert plugin.get_service("service2") == "Service 2"
        assert plugin.get_service("nonexistent") is None

    def test_configurable_plugin_protocol(self) -> None:
        """Test the ConfigurablePluginProtocol."""
        plugin = SampleConfigurablePlugin()

        # Test protocol conformance
        assert isinstance(plugin, QuackPluginProtocol)
        assert isinstance(plugin, ConfigurablePluginProtocol)

        # Test methods
        assert plugin.name == "test_configurable_plugin"

        # Test schema
        schema = plugin.get_config_schema()
        assert "settings" in schema

        # Test configuration and validation
        valid_config = {"settings": {"option1": "test", "option2": 123}}
        is_valid, errors = plugin.validate_config(valid_config)
        assert is_valid is True
        assert len(errors) == 0

        plugin.configure(valid_config)
        assert plugin._config == valid_config

        invalid_config = {"settings": {"option1": 123, "option2": "test"}}
        is_valid, errors = plugin.validate_config(invalid_config)
        assert is_valid is False
        assert len(errors) > 0

    def test_mixed_plugin_protocols(self) -> None:
        """Test mixing multiple plugin protocols."""
        plugin = SampleMixedPlugin()

        # Test protocol conformance
        assert isinstance(plugin, QuackPluginProtocol)
        assert isinstance(plugin, CommandPluginProtocol)
        assert isinstance(plugin, WorkflowPluginProtocol)

        # Test command methods
        assert plugin.list_commands() == ["cmd1", "cmd2"]
        assert plugin.execute_command("cmd1") == "Executed cmd1"

        # Test workflow methods
        assert plugin.list_workflows() == ["flow1", "flow2"]
        assert plugin.execute_workflow("flow1") == "Ran flow1"

    def test_runtime_checkable(self) -> None:
        """Test that protocols are runtime checkable."""

        # Test non-conforming class
        class NonConforming:
            def __init__(self) -> None:
                self.name = "non_conforming"

        non_conforming = NonConforming()

        # Should not be recognized as implementing the protocols
        assert not isinstance(non_conforming, QuackPluginProtocol)
        assert not isinstance(non_conforming, CommandPluginProtocol)

        # Test partially conforming class
        class PartiallyConforming:
            @property
            def name(self) -> str:
                return "partially_conforming"

        partially_conforming = PartiallyConforming()

        # Should be recognized as implementing QuackPluginProtocol
        assert isinstance(partially_conforming, QuackPluginProtocol)

        # But not the more specific protocols
        assert not isinstance(partially_conforming, CommandPluginProtocol)
        assert not isinstance(partially_conforming, WorkflowPluginProtocol)
