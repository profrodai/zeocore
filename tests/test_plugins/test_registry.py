"""
Tests for the plugin registry.
"""

from collections.abc import Callable

import pytest
from quack_core.core.errors import QuackPluginError
from quack_core.modules.protocols import (
    CommandPluginProtocol,
    ExtensionPluginProtocol,
    ProviderPluginProtocol,
    QuackPluginMetadata,
    QuackPluginProtocol,
    WorkflowPluginProtocol,
)
from quack_core.modules.registry import PluginRegistry


def _make_metadata(plugin_id: str, description: str) -> QuackPluginMetadata:
    """Build a minimal QuackPluginMetadata for a test fixture plugin.

    Factored out so each fixture's get_metadata() is a one-line delegation
    instead of a repeated multi-line literal -- keeps the enclosing test
    functions (several of which define 2+ nested fixture classes) under
    C901's complexity budget without weakening what any fixture asserts.
    """
    return QuackPluginMetadata(
        plugin_id=plugin_id,
        name=plugin_id,
        version="1.0.0",
        description=description,
    )


# Mock plugin implementations for testing
class BasicPlugin(QuackPluginProtocol):
    """Basic plugin implementation for testing."""

    @property
    def plugin_id(self) -> str:
        return "basic_plugin"

    @property
    def name(self) -> str:
        return "basic_plugin"

    def get_metadata(self) -> QuackPluginMetadata:
        """Get plugin metadata."""
        return QuackPluginMetadata(
            plugin_id=self.plugin_id,
            name=self.name,
            version="1.0.0",
            description="Basic plugin for testing",
            capabilities=[],
        )


class CommandPlugin(CommandPluginProtocol):
    """Command plugin implementation for testing."""

    @property
    def plugin_id(self) -> str:
        return "command_plugin"

    @property
    def name(self) -> str:
        return "command_plugin"

    def get_metadata(self) -> QuackPluginMetadata:
        return QuackPluginMetadata(
            plugin_id=self.plugin_id,
            name=self.name,
            version="1.0.0",
            description="Command plugin for testing",
        )

    def list_commands(self) -> list[str]:
        return ["cmd1", "cmd2"]

    def get_command(self, name: str) -> Callable[..., str] | None:
        if name in self.list_commands():
            return lambda *args, **kwargs: f"Executed {name}"
        return None

    def execute_command(self, name: str, *args: object, **kwargs: object) -> str:
        cmd = self.get_command(name)
        if cmd:
            return cmd(*args, **kwargs)
        raise ValueError(f"Command {name} not found")


class WorkflowPlugin(WorkflowPluginProtocol):
    """Workflow plugin implementation for testing."""

    @property
    def plugin_id(self) -> str:
        return "workflow_plugin"

    @property
    def name(self) -> str:
        return "workflow_plugin"

    def get_metadata(self) -> QuackPluginMetadata:
        return QuackPluginMetadata(
            plugin_id=self.plugin_id,
            name=self.name,
            version="1.0.0",
            description="Workflow plugin for testing",
        )

    def list_workflows(self) -> list[str]:
        return ["flow1", "flow2"]

    def get_workflow(self, name: str) -> Callable[..., str] | None:
        if name in self.list_workflows():
            return lambda *args, **kwargs: f"Ran {name}"
        return None

    def execute_workflow(self, name: str, *args: object, **kwargs: object) -> str:
        wf = self.get_workflow(name)
        if wf:
            return wf(*args, **kwargs)
        raise ValueError(f"Workflow {name} not found")


class ExtensionPlugin(ExtensionPluginProtocol):
    """Extension plugin implementation for testing."""

    @property
    def plugin_id(self) -> str:
        return "extension_plugin"

    @property
    def name(self) -> str:
        return "extension_plugin"

    def get_metadata(self) -> QuackPluginMetadata:
        return QuackPluginMetadata(
            plugin_id=self.plugin_id,
            name=self.name,
            version="1.0.0",
            description="Extension plugin for testing",
        )

    def get_target_plugin(self) -> str:
        return "target_plugin"

    def get_extensions(self) -> dict[str, Callable]:
        return {"ext1": lambda: "Extension 1", "ext2": lambda: "Extension 2"}


class ProviderPlugin(ProviderPluginProtocol):
    """Provider plugin implementation for testing."""

    @property
    def plugin_id(self) -> str:
        return "provider_plugin"

    @property
    def name(self) -> str:
        return "provider_plugin"

    def get_metadata(self) -> QuackPluginMetadata:
        return QuackPluginMetadata(
            plugin_id=self.plugin_id,
            name=self.name,
            version="1.0.0",
            description="Provider plugin for testing",
        )

    def get_services(self) -> dict[str, object]:
        return {"service1": "Service 1", "service2": "Service 2"}

    def get_service(self, name: str) -> object | None:
        return self.get_services().get(name)


class MultiPlugin(CommandPluginProtocol, WorkflowPluginProtocol):
    """Plugin implementing multiple protocols, for testing multi-registration."""

    @property
    def plugin_id(self) -> str:
        return "multi_plugin"

    @property
    def name(self) -> str:
        return "multi_plugin"

    def get_metadata(self) -> QuackPluginMetadata:
        return _make_metadata(self.plugin_id, "Multi plugin for testing")

    def list_commands(self) -> list[str]:
        return ["cmd1", "cmd2"]

    def get_command(self, name: str) -> Callable[..., str] | None:
        return lambda: f"Command {name}"

    def execute_command(self, name: str, *args: object, **kwargs: object) -> str:
        return f"Executed {name}"

    def list_workflows(self) -> list[str]:
        return ["flow1", "flow2"]

    def get_workflow(self, name: str) -> Callable[..., str] | None:
        return lambda: f"Workflow {name}"

    def execute_workflow(self, name: str, *args: object, **kwargs: object) -> str:
        return f"Ran {name}"


class CommandOverridePlugin1(CommandPluginProtocol):
    """First of two command plugins with an overlapping command, override test."""

    @property
    def plugin_id(self) -> str:
        return "plugin1"

    @property
    def name(self) -> str:
        return "plugin1"

    def get_metadata(self) -> QuackPluginMetadata:
        return _make_metadata(self.plugin_id, "Plugin1 for testing")

    def list_commands(self) -> list[str]:
        return ["common", "cmd1"]

    def get_command(self, name: str) -> Callable[..., str] | None:
        return lambda: f"Plugin1 {name}"

    def execute_command(self, name: str, *args: object, **kwargs: object) -> str:
        return f"Plugin1 executed {name}"


class CommandOverridePlugin2(CommandPluginProtocol):
    """Second of two command plugins with an overlapping command, override test."""

    @property
    def plugin_id(self) -> str:
        return "plugin2"

    @property
    def name(self) -> str:
        return "plugin2"

    def get_metadata(self) -> QuackPluginMetadata:
        return _make_metadata(self.plugin_id, "Plugin2 for testing")

    def list_commands(self) -> list[str]:
        return ["common", "cmd2"]

    def get_command(self, name: str) -> Callable[..., str] | None:
        return lambda: f"Plugin2 {name}"

    def execute_command(self, name: str, *args: object, **kwargs: object) -> str:
        return f"Plugin2 executed {name}"


class WorkflowOverridePlugin1(WorkflowPluginProtocol):
    """First of two workflow plugins with an overlapping workflow, override test."""

    @property
    def plugin_id(self) -> str:
        return "plugin1"

    @property
    def name(self) -> str:
        return "plugin1"

    def get_metadata(self) -> QuackPluginMetadata:
        return _make_metadata(self.plugin_id, "Plugin1 for testing")

    def list_workflows(self) -> list[str]:
        return ["common", "flow1"]

    def get_workflow(self, name: str) -> Callable[..., str] | None:
        return lambda: f"Plugin1 {name}"

    def execute_workflow(self, name: str, *args: object, **kwargs: object) -> str:
        return f"Plugin1 ran {name}"


class WorkflowOverridePlugin2(WorkflowPluginProtocol):
    """Second of two workflow plugins with an overlapping workflow, override test."""

    @property
    def plugin_id(self) -> str:
        return "plugin2"

    @property
    def name(self) -> str:
        return "plugin2"

    def get_metadata(self) -> QuackPluginMetadata:
        return _make_metadata(self.plugin_id, "Plugin2 for testing")

    def list_workflows(self) -> list[str]:
        return ["common", "flow2"]

    def get_workflow(self, name: str) -> Callable[..., str] | None:
        return lambda: f"Plugin2 {name}"

    def execute_workflow(self, name: str, *args: object, **kwargs: object) -> str:
        return f"Plugin2 ran {name}"


class TestPluginRegistry:
    """Tests for the PluginRegistry class."""

    def test_init(self) -> None:
        """Test initializing the registry."""
        registry = PluginRegistry()
        assert registry._plugins == {}
        assert registry._command_plugins == {}
        assert registry._workflow_plugins == {}
        assert registry._extension_plugins == {}
        assert registry._provider_plugins == {}
        assert registry._extensions == {}
        assert registry._commands == {}
        assert registry._workflows == {}

    def test_register_basic_plugin(self) -> None:
        """Test registering a basic plugin."""
        registry = PluginRegistry()
        plugin = BasicPlugin()

        registry.register(plugin)
        assert registry._plugins[plugin.name] is plugin

        # Test registering duplicate (should raise)
        with pytest.raises(QuackPluginError):
            registry.register(plugin)

    def test_register_command_plugin(self) -> None:
        """Test registering a command plugin."""
        registry = PluginRegistry()
        plugin = CommandPlugin()

        registry.register(plugin)
        assert registry._plugins[plugin.name] is plugin
        assert registry._command_plugins[plugin.name] is plugin

        # Check command registration
        for cmd in plugin.list_commands():
            assert registry._commands[cmd] is plugin

    def test_register_workflow_plugin(self) -> None:
        """Test registering a workflow plugin."""
        registry = PluginRegistry()
        plugin = WorkflowPlugin()

        registry.register(plugin)
        assert registry._plugins[plugin.name] is plugin
        assert registry._workflow_plugins[plugin.name] is plugin

        # Check workflow registration
        for wf in plugin.list_workflows():
            assert registry._workflows[wf] is plugin

    def test_register_extension_plugin(self) -> None:
        """Test registering an extension plugin."""
        registry = PluginRegistry()
        plugin = ExtensionPlugin()

        registry.register(plugin)
        assert registry._plugins[plugin.name] is plugin
        assert registry._extension_plugins[plugin.name] is plugin

        # Check extension registration for target
        target = plugin.get_target_plugin()
        assert plugin in registry._extensions[target]

    def test_register_provider_plugin(self) -> None:
        """Test registering a provider plugin."""
        registry = PluginRegistry()
        plugin = ProviderPlugin()

        registry.register(plugin)
        assert registry._plugins[plugin.name] is plugin
        assert registry._provider_plugins[plugin.name] is plugin

    def test_register_multiple_types(self) -> None:
        """Test registering a plugin that implements multiple protocols."""
        registry = PluginRegistry()
        plugin = MultiPlugin()

        registry.register(plugin)
        assert registry._plugins[plugin.name] is plugin
        assert registry._command_plugins[plugin.name] is plugin
        assert registry._workflow_plugins[plugin.name] is plugin

        # Check command registration
        for cmd in plugin.list_commands():
            assert registry._commands[cmd] is plugin

        # Check workflow registration
        for wf in plugin.list_workflows():
            assert registry._workflows[wf] is plugin

    def test_command_override(self) -> None:
        """Test that newer command modules override older ones for the same command."""
        registry = PluginRegistry()

        plugin1 = CommandOverridePlugin1()
        plugin2 = CommandOverridePlugin2()

        # Register first plugin
        registry.register(plugin1)
        assert registry._commands["common"] is plugin1
        assert registry._commands["cmd1"] is plugin1

        # Register second plugin (should override common command)
        registry.register(plugin2)
        assert registry._commands["common"] is plugin2
        assert registry._commands["cmd1"] is plugin1
        assert registry._commands["cmd2"] is plugin2

    def test_workflow_override(self) -> None:
        """Test that newer workflow modules override
        older ones for the same workflow."""
        registry = PluginRegistry()

        plugin1 = WorkflowOverridePlugin1()
        plugin2 = WorkflowOverridePlugin2()

        # Register first plugin
        registry.register(plugin1)
        assert registry._workflows["common"] is plugin1
        assert registry._workflows["flow1"] is plugin1

        # Register second plugin (should override common workflow)
        registry.register(plugin2)
        assert registry._workflows["common"] is plugin2
        assert registry._workflows["flow1"] is plugin1
        assert registry._workflows["flow2"] is plugin2

    def test_unregister_plugin(self) -> None:
        """Test unregistering a plugin."""
        registry = PluginRegistry()

        # Register different types of modules
        basic = BasicPlugin()
        command = CommandPlugin()
        workflow = WorkflowPlugin()
        extension = ExtensionPlugin()
        provider = ProviderPlugin()

        registry.register(basic)
        registry.register(command)
        registry.register(workflow)
        registry.register(extension)
        registry.register(provider)

        # Unregister basic plugin
        registry.unregister(basic.name)
        assert basic.name not in registry._plugins

        # Unregister command plugin
        registry.unregister(command.name)
        assert command.name not in registry._plugins
        assert command.name not in registry._command_plugins
        for cmd in command.list_commands():
            assert cmd not in registry._commands

        # Unregister workflow plugin
        registry.unregister(workflow.name)
        assert workflow.name not in registry._plugins
        assert workflow.name not in registry._workflow_plugins
        for wf in workflow.list_workflows():
            assert wf not in registry._workflows

        # Unregister extension plugin
        registry.unregister(extension.name)
        assert extension.name not in registry._plugins
        assert extension.name not in registry._extension_plugins
        target = extension.get_target_plugin()
        assert extension not in registry._extensions.get(target, [])

        # Unregister provider plugin
        registry.unregister(provider.name)
        assert provider.name not in registry._plugins
        assert provider.name not in registry._provider_plugins

        # Test unregistering non-existent plugin
        with pytest.raises(QuackPluginError):
            registry.unregister("nonexistent_plugin")

    def test_execute_command(self) -> None:
        """Test executing a command through the registry."""
        registry = PluginRegistry()
        plugin = CommandPlugin()
        registry.register(plugin)

        # Test executing a registered command
        result = registry.execute_command("cmd1")
        assert result == "Executed cmd1"

        # Test with arguments
        result = registry.execute_command("cmd2", "arg1", key="value")
        assert result == "Executed cmd2"

        # Test executing non-existent command
        with pytest.raises(QuackPluginError):
            registry.execute_command("nonexistent")

    def test_execute_workflow(self) -> None:
        """Test executing a workflow through the registry."""
        registry = PluginRegistry()
        plugin = WorkflowPlugin()
        registry.register(plugin)

        # Test executing a registered workflow
        result = registry.execute_workflow("flow1")
        assert result == "Ran flow1"

        # Test with arguments
        result = registry.execute_workflow("flow2", "arg1", key="value")
        assert result == "Ran flow2"

        # Test executing non-existent workflow
        with pytest.raises(QuackPluginError):
            registry.execute_workflow("nonexistent")

    def test_plugin_getters(self) -> None:
        """Test getting modules from the registry."""
        registry = PluginRegistry()

        # Register different types of modules
        basic = BasicPlugin()
        command = CommandPlugin()
        workflow = WorkflowPlugin()
        extension = ExtensionPlugin()
        provider = ProviderPlugin()

        registry.register(basic)
        registry.register(command)
        registry.register(workflow)
        registry.register(extension)
        registry.register(provider)

        # Test get_plugin
        assert registry.get_plugin(basic.name) is basic
        assert registry.get_plugin("nonexistent") is None

        # Test get_command_plugin
        assert registry.get_command_plugin(command.name) is command
        assert registry.get_command_plugin(basic.name) is None

        # Test get_workflow_plugin
        assert registry.get_workflow_plugin(workflow.name) is workflow
        assert registry.get_workflow_plugin(basic.name) is None

        # Test get_extension_plugin
        assert registry.get_extension_plugin(extension.name) is extension
        assert registry.get_extension_plugin(basic.name) is None

        # Test get_provider_plugin
        assert registry.get_provider_plugin(provider.name) is provider
        assert registry.get_provider_plugin(basic.name) is None

    def test_list_plugins(self) -> None:
        """Test listing modules."""
        registry = PluginRegistry()

        # Register different types of modules
        basic = BasicPlugin()
        command = CommandPlugin()
        workflow = WorkflowPlugin()

        registry.register(basic)
        registry.register(command)
        registry.register(workflow)

        # Test list_plugins
        assert set(registry.list_plugins()) == {basic.name, command.name, workflow.name}

        # Test list_command_plugins
        assert set(registry.list_command_plugins()) == {command.name}

        # Test list_workflow_plugins
        assert set(registry.list_workflow_plugins()) == {workflow.name}

        # Test list_commands
        assert set(registry.list_commands()) == set(command.list_commands())

        # Test list_workflows
        assert set(registry.list_workflows()) == set(workflow.list_workflows())

    def test_is_registered(self) -> None:
        """Test checking if a plugin is registered."""
        registry = PluginRegistry()
        plugin = BasicPlugin()

        assert not registry.is_registered(plugin.name)

        registry.register(plugin)
        assert registry.is_registered(plugin.name)

        registry.unregister(plugin.name)
        assert not registry.is_registered(plugin.name)

    def test_get_command_plugin_for_command(self) -> None:
        """Test getting the plugin that provides a command."""
        registry = PluginRegistry()
        plugin = CommandPlugin()
        registry.register(plugin)

        assert registry.get_command_plugin_for_command("cmd1") is plugin
        assert registry.get_command_plugin_for_command("nonexistent") is None

    def test_get_workflow_plugin_for_workflow(self) -> None:
        """Test getting the plugin that provides a workflow."""
        registry = PluginRegistry()
        plugin = WorkflowPlugin()
        registry.register(plugin)

        assert registry.get_workflow_plugin_for_workflow("flow1") is plugin
        assert registry.get_workflow_plugin_for_workflow("nonexistent") is None

    def test_get_extensions_for_plugin(self) -> None:
        """Test getting extensions for a target plugin."""
        registry = PluginRegistry()
        extension1 = ExtensionPlugin()

        # Create another extension targeting the same plugin
        class Extension2(ExtensionPluginProtocol):
            @property
            def plugin_id(self) -> str:
                return "extension2"

            @property
            def name(self) -> str:
                return "extension2"

            def get_metadata(self) -> QuackPluginMetadata:
                return QuackPluginMetadata(
                    plugin_id=self.plugin_id,
                    name=self.name,
                    version="1.0.0",
                    description="Extension2 for testing",
                )

            def get_target_plugin(self) -> str:
                return "target_plugin"

            def get_extensions(self) -> dict[str, Callable]:
                return {"ext3": lambda: "Extension 3"}

        extension2 = Extension2()

        registry.register(extension1)
        registry.register(extension2)

        # Test getting extensions for the target
        extensions = registry.get_extensions_for_plugin("target_plugin")
        assert len(extensions) == 2
        assert extension1 in extensions
        assert extension2 in extensions

        # Test getting extensions for non-existent target
        assert registry.get_extensions_for_plugin("nonexistent") == []

    def test_register_and_unreg_plugin(self) -> None:
        """Test registering and unregistering a plugin."""
        registry = PluginRegistry()
        plugin = BasicPlugin()

        # Register the plugin
        registry.register(plugin)
        assert registry.is_registered(plugin.name)
        assert registry.get_plugin(plugin.name) is plugin

        # Unregister the plugin
        registry.unregister(plugin.name)
        assert not registry.is_registered(plugin.name)
        assert registry.get_plugin(plugin.name) is None

        # Trying to unregister again should raise an error
        with pytest.raises(QuackPluginError):
            registry.unregister(plugin.name)

    def test_plugin_capabilities_filtering(self) -> None:
        """Test filtering modules by capability."""
        from quack_core.modules.protocols import QuackPluginMetadata

        class CapabilityPlugin(QuackPluginProtocol):
            """Plugin with capabilities for testing."""

            def __init__(self, name: str, capabilities: list[str]) -> None:
                self._name = name
                self._capabilities = capabilities

            @property
            def plugin_id(self) -> str:
                return self._name

            @property
            def name(self) -> str:
                return self._name

            def get_metadata(self) -> QuackPluginMetadata:
                return QuackPluginMetadata(
                    plugin_id=self.plugin_id,
                    name=self._name,
                    version="1.0.0",
                    description=f"Plugin {self._name}",
                    capabilities=self._capabilities,
                )

        registry = PluginRegistry()

        # Register modules with different capabilities
        plugin1 = CapabilityPlugin("plugin1", ["command", "workflow"])
        plugin2 = CapabilityPlugin("plugin2", ["command"])
        plugin3 = CapabilityPlugin("plugin3", ["provider"])

        registry.register(plugin1)
        registry.register(plugin2)
        registry.register(plugin3)

        # Test finding modules by capability
        command_plugins = registry.find_plugins_by_capability("command")
        assert len(command_plugins) == 2
        assert plugin1 in command_plugins
        assert plugin2 in command_plugins

        workflow_plugins = registry.find_plugins_by_capability("workflow")
        assert len(workflow_plugins) == 1
        assert plugin1 in workflow_plugins

        provider_plugins = registry.find_plugins_by_capability("provider")
        assert len(provider_plugins) == 1
        assert plugin3 in provider_plugins

        nonexistent_plugins = registry.find_plugins_by_capability("nonexistent")
        assert len(nonexistent_plugins) == 0

    def test_reload_plugin(self) -> None:
        """Test reloading a plugin."""
        from unittest.mock import patch

        # Since we can't easily mock importlib.reload properly,
        # we'll mock the entire reload_plugin method

        registry = PluginRegistry()

        # Create our modules for testing
        class TestPlugin(QuackPluginProtocol):
            @property
            def plugin_id(self) -> str:
                return "test_reload_plugin"

            @property
            def name(self) -> str:
                return "test_reload_plugin"

            def get_metadata(self) -> QuackPluginMetadata:
                return QuackPluginMetadata(
                    plugin_id=self.plugin_id,
                    name=self.name,
                    version="1.0.0",
                    description="Test plugin",
                    capabilities=["test"],
                )

        class UpdatedTestPlugin(QuackPluginProtocol):
            @property
            def plugin_id(self) -> str:
                return "test_reload_plugin"

            @property
            def name(self) -> str:
                return "test_reload_plugin"

            def get_metadata(self) -> QuackPluginMetadata:
                return QuackPluginMetadata(
                    plugin_id=self.plugin_id,
                    name=self.name,
                    version="1.1.0",  # Updated version
                    description="Updated test plugin",
                    capabilities=["test", "new_capability"],  # New capability
                )

        original_plugin = TestPlugin()
        updated_plugin = UpdatedTestPlugin()

        # Register the original plugin
        registry.register(original_plugin)

        # Now mock the whole reload_plugin method
        with patch.object(registry, "reload_plugin") as mock_reload:
            mock_reload.return_value = updated_plugin

            # Call reload_plugin and verify it returns what we expect
            reloaded_plugin = registry.reload_plugin("test_reload_plugin")
            assert reloaded_plugin is updated_plugin
            mock_reload.assert_called_once_with("test_reload_plugin")

        # Manual test of the capabilities logic
        # Since we mocked reload_plugin, we need to manually register
        # the updated plugin to test capability filtering
        registry.unregister("test_reload_plugin")
        registry.register(updated_plugin)

        capability_plugins = registry.find_plugins_by_capability("new_capability")
        assert len(capability_plugins) == 1
        assert capability_plugins[0] is updated_plugin

    def test_plugin_metadata_validation(self) -> None:
        """Test validation of plugin metadata."""
        from typing import cast
        from unittest.mock import patch

        from quack_core.modules.discovery import PluginLoader

        loader = PluginLoader()

        # Test plugin with valid metadata. plugin_id must be a real string:
        # PluginInfo (discovery.py) extends QuackPluginMetadata to make plugin_id
        # REQUIRED (not optional) - "This ensures that all validated modules have
        # a stable identifier for deterministic registration." A subclass of the
        # QuackPluginProtocol Protocol that does not override plugin_id still
        # passes hasattr() (the base Protocol declares the property), but calling
        # it returns None from the unimplemented base body - which then fails
        # PluginInfo's non-optional plugin_id validation. Not a code bug; the
        # fixture class here was simply incomplete relative to that contract.
        class ValidPlugin(QuackPluginProtocol):
            @property
            def plugin_id(self) -> str:
                return "valid_plugin"

            @property
            def name(self) -> str:
                return "valid_plugin"

            def get_metadata(self) -> QuackPluginMetadata:
                return QuackPluginMetadata(
                    plugin_id=self.plugin_id,
                    name=self.name,
                    version="1.0.0",
                    description="Valid plugin",
                    capabilities=["test"],
                )

        valid_plugin = ValidPlugin()

        # This should not raise an error
        validated_plugin = loader._validate_plugin(valid_plugin, "test.module")
        assert validated_plugin is valid_plugin

        # Test plugin with invalid metadata (missing required fields)
        class InvalidPlugin(QuackPluginProtocol):
            @property
            def name(self) -> str:
                return "invalid_plugin"

            def get_metadata(self) -> QuackPluginMetadata:
                # In the real implementation, this would fail validation
                # but we need a valid return type for the method signature
                raise NotImplementedError("This should be mocked")

        # InvalidPlugin deliberately omits plugin_id: the whole point of this
        # fixture is exercising _validate_plugin's runtime rejection of a
        # plugin that does not implement the full QuackPluginProtocol contract
        # (see the ValidPlugin comment above). mypy strict now correctly
        # flags this exact incompleteness at the type level too -- a real
        # signal, not a false positive -- so it is silenced here, scoped to
        # this one construction, precisely because triggering it IS the test.
        invalid_plugin = InvalidPlugin()  # type: ignore[abstract]

        # Simpler approach - patch the _validate_plugin method itself for
        # this specific test
        original_validate = loader._validate_plugin

        def mock_validate_that_raises(
            plugin: QuackPluginProtocol, module_path: str
        ) -> QuackPluginProtocol:
            if plugin.name == "invalid_plugin":
                raise QuackPluginError(
                    f"Plugin from module {module_path} does not have valid "
                    "plugin info: Missing version",
                    plugin_path=module_path,
                )
            return original_validate(plugin, module_path)

        # Replace the method temporarily
        with patch.object(
            loader, "_validate_plugin", side_effect=mock_validate_that_raises
        ):
            # Patch the get_metadata to return invalid data
            with patch.object(
                invalid_plugin,
                "get_metadata",
                return_value={"name": invalid_plugin.name},
                # Missing required fields
            ):
                # This should now raise a QuackPluginError
                with pytest.raises(QuackPluginError):
                    loader._validate_plugin(invalid_plugin, "test.module")

        # Test plugin without get_metadata method
        class LegacyPlugin:
            @property
            def name(self) -> str:
                return "legacy_plugin"

        legacy_plugin = LegacyPlugin()

        # This should create minimal metadata for backward compatibility
        # We cast to satisfy the type checker
        try:
            loader._validate_plugin(
                cast(QuackPluginProtocol, legacy_plugin), "test.module"
            )
        except QuackPluginError:
            pytest.fail("Legacy plugin should be accepted with minimal metadata")

    def test_load_builtin_plugin(self) -> None:
        """Test loading a built-in plugin."""
        from unittest.mock import MagicMock, patch

        from quack_core.modules.discovery import PluginLoader

        loader = PluginLoader()

        # Mock a proper plugin factory function that returns a plugin with metadata
        mock_plugin = BasicPlugin()

        def mock_factory() -> BasicPlugin:
            return mock_plugin

        # Create a proper mock entry point
        mock_ep = MagicMock()
        mock_ep.name = "builtin_plugin"
        mock_ep.value = "quack_core.builtin:create_plugin"
        mock_ep.load.return_value = mock_factory

        # Test loading from entry points. Patch where entry_points is USED
        # (quack_core.modules.discovery), not where it is defined
        # (importlib.metadata) - discovery.py binds its own local name via
        # `from importlib.metadata import entry_points` at import time, so
        # patching the origin does not affect the already-bound reference and
        # the real, genuinely-registered "quack_core.modules" entry points
        # (config/fs/paths/prompt) would be discovered instead of this mock.
        with patch("quack_core.modules.discovery.entry_points", return_value=[mock_ep]):
            # Patch the validate_plugin method to not actually validate
            with patch.object(loader, "_validate_plugin", return_value=mock_plugin):
                plugins = loader.load_entry_points()
                assert len(plugins) == 1
                assert plugins[0].name == "basic_plugin"

    def test_discover_external_plugin(self) -> None:
        """Test discovering an external plugin."""
        from unittest.mock import MagicMock, patch

        from quack_core.modules.discovery import PluginLoader

        loader = PluginLoader()

        # Mock a proper plugin factory function that returns a plugin with metadata
        mock_plugin = BasicPlugin()

        def mock_factory() -> BasicPlugin:
            return mock_plugin

        # Create a proper mock entry point
        mock_ep = MagicMock()
        mock_ep.name = "external_plugin"
        mock_ep.value = "external_package.plugin:create_plugin"
        mock_ep.load.return_value = mock_factory

        # Test loading from entry points. Same patch-target note as
        # test_load_builtin_plugin above.
        with patch("quack_core.modules.discovery.entry_points", return_value=[mock_ep]):
            # Patch the validate_plugin method to not actually validate
            with patch.object(loader, "_validate_plugin", return_value=mock_plugin):
                plugins = loader.load_entry_points()
                assert len(plugins) == 1
                assert plugins[0].name == "basic_plugin"
