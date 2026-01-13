# QuackCore Plugins Documentation

## Table of Contents

- [Introduction](#introduction)
- [Plugin System Architecture](#plugin-system-architecture)
  - [Core Concepts](#core-concepts)
  - [Plugin Types](#plugin-types)
- [Creating Plugins](#creating-plugins)
  - [Basic Plugin](#basic-plugin)
  - [Command Plugin](#command-plugin)
  - [Workflow Plugin](#workflow-plugin)
  - [Extension Plugin](#extension-plugin)
  - [Provider Plugin](#provider-plugin)
  - [Configurable Plugin](#configurable-plugin)
- [Plugin Discovery](#plugin-discovery)
  - [Entry Points](#entry-points)
  - [Module Paths](#module-paths)
  - [Factory Functions](#factory-functions)
- [Plugin Registry](#plugin-registry)
  - [Registering Plugins](#registering-plugins)
  - [Accessing Plugins](#accessing-plugins)
  - [Executing Commands and Workflows](#executing-commands-and-workflows)
- [Best Practices](#best-practices)
  - [Naming Conventions](#naming-conventions)
  - [Error Handling](#error-handling)
  - [Plugin Dependencies](#plugin-dependencies)
  - [Testing Plugins](#testing-plugins)
- [Common Patterns](#common-patterns)
  - [Singleton Plugins](#singleton-plugins)
  - [Plugin Configuration](#plugin-configuration)
  - [Plugin Composition](#plugin-composition)
- [Anti-Patterns](#anti-patterns)
  - [Common Mistakes](#common-mistakes)
  - [Performance Issues](#performance-issues)
- [Examples](#examples)
  - [Basic QuackTool](#basic-quacktool)
  - [Advanced QuackTool](#advanced-quacktool)
- [Reference](#reference)
  - [API Reference](#api-reference)
  - [Glossary](#glossary)

## Introduction

QuackCore is a plugin-based framework designed for building modular and extensible applications. The `quack_core.modules` module provides the foundation for creating, discovering, and managing plugins within the QuackVerse ecosystem.

This documentation will guide you through the process of creating, registering, and using plugins with QuackCore, helping you build your own QuackTools as part of the QuackVerse.

### What is a QuackTool?

A QuackTool is a plugin that extends the functionality of quack_core. QuackTools are modular components that can be easily added or removed from a QuackCore application. By building a QuackTool, you're contributing to the QuackVerse ecosystem, allowing others to benefit from your code.

### Why Use Plugins?

Plugins offer several advantages for application development:

- **Modularity**: Break your application into separate, focused components
- **Extensibility**: Allow others to extend your application without modifying its core
- **Reusability**: Share functionality across different applications
- **Maintainability**: Isolate changes to specific plugins without affecting the entire application

## Plugin System Architecture

### Core Concepts

The QuackCore plugin system is built around several key components:

1. **Plugin Protocols**: Interfaces that define what a plugin should implement
2. **Plugin Loader**: Responsible for discovering and loading plugins
3. **Plugin Registry**: Manages registered plugins and provides access to them

Here's a high-level overview of how these components interact:

1. The **Plugin Loader** discovers plugins through entry points or module paths
2. Discovered plugins are validated and loaded
3. Loaded plugins are registered with the **Plugin Registry**
4. The application uses the registry to access and use plugins

### Plugin Types

QuackCore defines several plugin types, each serving a different purpose:

- **Base Plugin**: The foundation for all plugin types
- **Command Plugin**: Provides command functions that can be executed
- **Workflow Plugin**: Provides workflow functions that can be executed
- **Extension Plugin**: Extends the functionality of other plugins
- **Provider Plugin**: Provides services to other plugins
- **Configurable Plugin**: Can be configured with external settings

## Creating Plugins

### Basic Plugin

All plugins must implement the `QuackPluginProtocol`, which requires a `name` property. This is the simplest form of a plugin:

```python
from quack_core.modules.protocols import QuackPluginProtocol


class MyPlugin:
    """A simple QuackCore plugin."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "my-plugin"
```

When creating a plugin, you can expose it through a factory function:

```python
def create_plugin() -> QuackPluginProtocol:
    """Create an instance of MyPlugin."""
    return MyPlugin()
```

### Command Plugin

A Command Plugin provides executable commands. It must implement the `CommandPluginProtocol`:

```python
from quack_core.modules.protocols import CommandPluginProtocol
from typing import Any, Callable


class MyCommandPlugin:
    """A plugin that provides commands."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "my-command-plugin"

    def list_commands(self) -> list[str]:
        """List all commands provided by this plugin."""
        return ["hello", "goodbye"]

    def get_command(self, name: str) -> Callable[..., Any] | None:
        """Get a command by name."""
        commands = {
            "hello": self._hello_command,
            "goodbye": self._goodbye_command,
        }
        return commands.get(name)

    def execute_command(self, name: str, *args: object, **kwargs: object) -> Any:
        """Execute a command."""
        command = self.get_command(name)
        if command is None:
            raise ValueError(f"Command '{name}' not found")
        return command(*args, **kwargs)

    def _hello_command(self, name: str = "World") -> str:
        """Say hello to someone."""
        return f"Hello, {name}!"

    def _goodbye_command(self, name: str = "World") -> str:
        """Say goodbye to someone."""
        return f"Goodbye, {name}!"
```

### Workflow Plugin

A Workflow Plugin provides executable workflows, which are typically more complex than commands. It must implement the `WorkflowPluginProtocol`:

```python
from quack_core.modules.protocols import WorkflowPluginProtocol
from typing import Any, Callable


class MyWorkflowPlugin:
    """A plugin that provides workflows."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "my-workflow-plugin"

    def list_workflows(self) -> list[str]:
        """List all workflows provided by this plugin."""
        return ["process-data", "generate-report"]

    def get_workflow(self, name: str) -> Callable[..., Any] | None:
        """Get a workflow by name."""
        workflows = {
            "process-data": self._process_data_workflow,
            "generate-report": self._generate_report_workflow,
        }
        return workflows.get(name)

    def execute_workflow(self, name: str, *args: object, **kwargs: object) -> Any:
        """Execute a workflow."""
        workflow = self.get_workflow(name)
        if workflow is None:
            raise ValueError(f"Workflow '{name}' not found")
        return workflow(*args, **kwargs)

    def _process_data_workflow(self, data: list[dict]) -> list[dict]:
        """Process a list of data dictionaries."""
        # Example workflow that processes data
        return [self._process_item(item) for item in data]

    def _generate_report_workflow(self, data: list[dict], title: str) -> str:
        """Generate a report from data."""
        # Example workflow that generates a report
        processed_data = self._process_data_workflow(data)
        return self._format_report(processed_data, title)

    def _process_item(self, item: dict) -> dict:
        """Process a single data item."""
        # Example processing function
        return {k: v.upper() if isinstance(v, str) else v for k, v in item.items()}

    def _format_report(self, data: list[dict], title: str) -> str:
        """Format processed data as a report."""
        # Example formatting function
        report = f"# {title}\n\n"
        for item in data:
            report += f"- {item}\n"
        return report
```

### Extension Plugin

An Extension Plugin extends the functionality of other plugins. It must implement the `ExtensionPluginProtocol`:

```python
from quack_core.modules.protocols import ExtensionPluginProtocol
from typing import Any, Callable


class MyExtensionPlugin:
    """A plugin that extends another plugin."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "my-extension-plugin"

    def get_target_plugin(self) -> str:
        """Get the name of the plugin this extension targets."""
        return "target-plugin-name"

    def get_extensions(self) -> dict[str, Callable[..., Any]]:
        """Get all extensions provided by this plugin."""
        return {
            "additional-function": self._additional_function,
            "enhanced-feature": self._enhanced_feature,
        }

    def _additional_function(self, *args: object, **kwargs: object) -> Any:
        """An additional function provided by this extension."""
        # Implementation...
        return "Extension result"

    def _enhanced_feature(self, *args: object, **kwargs: object) -> Any:
        """An enhanced feature provided by this extension."""
        # Implementation...
        return "Enhanced feature result"
```

### Provider Plugin

A Provider Plugin provides services to other plugins. It must implement the `ProviderPluginProtocol`:

```python
from quack_core.modules.protocols import ProviderPluginProtocol
from typing import Any


class MyProviderPlugin:
    """A plugin that provides services."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "my-provider-plugin"

    def get_services(self) -> dict[str, Any]:
        """Get all services provided by this plugin."""
        return {
            "database": self._database_service,
            "logger": self._logger_service,
        }

    def get_service(self, name: str) -> Any | None:
        """Get a service by name."""
        services = self.get_services()
        return services.get(name)

    @property
    def _database_service(self) -> object:
        """A database service."""
        # Implementation...
        return DatabaseService()

    @property
    def _logger_service(self) -> object:
        """A logger service."""
        # Implementation...
        return LoggerService()


class DatabaseService:
    """A simple database service."""

    def query(self, sql: str) -> list[dict]:
        """Execute a SQL query."""
        # Implementation...
        return [{"result": "data"}]


class LoggerService:
    """A simple logger service."""

    def log(self, message: str, level: str = "INFO") -> None:
        """Log a message."""
        # Implementation...
        print(f"[{level}] {message}")
```

### Configurable Plugin

A Configurable Plugin can be configured with external settings. It must implement the `ConfigurablePluginProtocol`:

```python
from quack_core.modules.protocols import ConfigurablePluginProtocol, QuackPluginProtocol
from typing import Any


class MyConfigurablePlugin:
    """A plugin that can be configured."""

    def __init__(self) -> None:
        """Initialize the plugin with default configuration."""
        self._config = {
            "debug": False,
            "log_level": "INFO",
        }

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "my-configurable-plugin"

    def configure(self, config: dict[str, Any]) -> None:
        """Configure the plugin."""
        valid, errors = self.validate_config(config)
        if not valid:
            raise ValueError(f"Invalid configuration: {errors}")
        # Update configuration
        self._config.update(config)

    def get_config_schema(self) -> dict[str, Any]:
        """Get the configuration schema for this plugin."""
        return {
            "type": "object",
            "properties": {
                "debug": {"type": "boolean"},
                "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR"]},
            },
            "required": ["debug", "log_level"],
        }

    def validate_config(self, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a configuration dictionary."""
        errors = []
        # Example validation
        if "debug" in config and not isinstance(config["debug"], bool):
            errors.append("debug must be a boolean")
        if "log_level" in config and config["log_level"] not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            errors.append("log_level must be one of: DEBUG, INFO, WARNING, ERROR")
        return (len(errors) == 0, errors)
```

## Plugin Discovery

QuackCore provides several mechanisms for discovering plugins:

1. Entry points
2. Module paths
3. Factory functions

### Entry Points

Entry points allow Python packages to be automatically discovered and loaded. To make your plugin discoverable through entry points, add an entry point definition to your `setup.py` or `pyproject.toml`:

```python
# setup.py
setuptools.setup(
    name="my-quacktool",
    # ...
    entry_points={
        "quack_core.modules": [
            "my-plugin=my_quacktool.plugin:create_plugin",
        ],
    },
)
```

```toml
# pyproject.toml
[project.entry-points."quack_core.modules"]
my-plugin = "my_quacktool.plugin:create_plugin"
```

The entry point must point to a callable that returns a plugin instance.

### Module Paths

You can also load plugins from specific module paths:

```python
from quack_core.modules import loader

# Load a single plugin
plugin = loader.load_plugin("my_quacktool.plugin")

# Load multiple modules
plugins = loader.load_plugins([
    "my_quacktool.plugin1",
    "my_quacktool.plugin2",
])
```

### Factory Functions

QuackCore looks for factory functions in modules to create plugin instances. The recommended factory function names are:

- `create_plugin`: A general factory function for any plugin type
- `create_integration`: An alternative factory function for plugin integrations

Example implementation:

```python
# my_quacktool/plugin.py
from my_quacktool.plugins import MyPlugin
from quack_core.modules.protocols import QuackPluginProtocol


def create_plugin() -> QuackPluginProtocol:
    """Factory function to create a plugin instance."""
    return MyPlugin()
```

If no factory function is found, QuackCore will look for a class named `MockPlugin` or `MockIntegration`.

## Plugin Registry

The Plugin Registry manages registered plugins and provides access to them. QuackCore provides a global registry instance that you can use:

```python
from quack_core.modules import registry
```

### Registering Plugins

You can register plugins with the registry:

```python
from quack_core.modules import registry
from my_quacktool.plugins import MyPlugin

# Register a single plugin
plugin = MyPlugin()
registry.register(plugin)
```

When plugins are loaded through entry points, they are automatically registered with the global registry.

### Accessing Plugins

You can access plugins from the registry:

```python
# Get a plugin by name
plugin = registry.get_plugin("my-plugin")

# Check if a plugin is registered
if registry.is_registered("my-plugin"):
    print("Plugin is registered!")

# List all registered modules
plugin_names = registry.list_plugins()
```

For specific plugin types, you can use specialized methods:

```python
# Get a command plugin
command_plugin = registry.get_command_plugin("my-command-plugin")

# Get a workflow plugin
workflow_plugin = registry.get_workflow_plugin("my-workflow-plugin")

# Get an extension plugin
extension_plugin = registry.get_extension_plugin("my-extension-plugin")

# Get a provider plugin
provider_plugin = registry.get_provider_plugin("my-provider-plugin")
```

### Executing Commands and Workflows

You can execute commands and workflows directly through the registry:

```python
# Execute a command
result = registry.execute_command("hello", name="QuackVerse")

# Execute a workflow
result = registry.execute_workflow("process-data", data=[{"foo": "bar"}])
```

## Best Practices

### Naming Conventions

- **Plugin Names**: Use kebab-case (e.g., `my-plugin`, `database-provider`)
- **Command/Workflow Names**: Use kebab-case (e.g., `process-data`, `generate-report`)
- **Module Names**: Use snake_case (e.g., `my_plugin.py`, `database_provider.py`)
- **Class Names**: Use PascalCase (e.g., `MyPlugin`, `DatabaseProvider`)

### Error Handling

Use `QuackPluginError` for plugin-related errors and provide meaningful error messages:

```python
from quack_core.core.errors import QuackPluginError

try:
    plugin = loader.load_plugin("non_existent_module")
except QuackPluginError as e:
    print(f"Failed to load plugin: {e}")
```

### Plugin Dependencies

If your plugin depends on other plugins, check for their existence at runtime:

```python
from quack_core.modules import registry


class MyPlugin:
    """A plugin that depends on other modules."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "my-plugin"

    def __init__(self) -> None:
        """Initialize the plugin."""
        # Check for required modules
        if not registry.is_registered("required-plugin"):
            raise RuntimeError("Required plugin 'required-plugin' is not registered")

        # Get the required plugin
        self.required_plugin = registry.get_plugin("required-plugin")
```

### Testing Plugins

When testing plugins, create a separate test registry to avoid affecting the global registry:

```python
import unittest
from quack_core.modules import PluginRegistry
from my_quacktool.plugins import MyPlugin


class TestMyPlugin(unittest.TestCase):
    """Test cases for MyPlugin."""

    def setUp(self) -> None:
        """Set up the test environment."""
        self.registry = PluginRegistry()
        self.plugin = MyPlugin()
        self.registry.register(self.plugin)

    def test_plugin_name(self) -> None:
        """Test that the plugin name is correct."""
        self.assertEqual(self.plugin.name, "my-plugin")

    def test_plugin_registered(self) -> None:
        """Test that the plugin is registered."""
        self.assertTrue(self.registry.is_registered("my-plugin"))
```

## Common Patterns

### Singleton Plugins

If your plugin should be a singleton (only one instance should exist), use a factory function that returns the same instance:

```python
# Singleton plugin instance
_plugin_instance = None

def create_plugin() -> QuackPluginProtocol:
    """Factory function to create a singleton plugin instance."""
    global _plugin_instance
    if _plugin_instance is None:
        _plugin_instance = MyPlugin()
    return _plugin_instance
```

### Plugin Configuration

For configurable plugins, provide a way to configure them from external sources:

```python
from quack_core.modules.protocols import ConfigurablePluginProtocol


class MyConfigurablePlugin:
    """A configurable plugin."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "my-configurable-plugin"

    def __init__(self) -> None:
        """Initialize the plugin."""
        self._config = {
            "option1": "default",
            "option2": 123,
        }

    def configure(self, config: dict) -> None:
        """Configure the plugin."""
        self._config.update(config)
```

### Plugin Composition

You can compose multiple plugin types to create more complex plugins:

```python
from quack_core.modules.protocols import (
    CommandPluginProtocol,
    ProviderPluginProtocol,
    QuackPluginProtocol,
)
from typing import Any, Callable


class CompositePlugin:
    """A plugin that implements multiple plugin types."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "composite-plugin"

    # Command Plugin methods
    def list_commands(self) -> list[str]:
        """List all commands provided by this plugin."""
        return ["command1", "command2"]

    def get_command(self, name: str) -> Callable[..., Any] | None:
        """Get a command by name."""
        commands = {
            "command1": self._command1,
            "command2": self._command2,
        }
        return commands.get(name)

    def execute_command(self, name: str, *args: object, **kwargs: object) -> Any:
        """Execute a command."""
        command = self.get_command(name)
        if command is None:
            raise ValueError(f"Command '{name}' not found")
        return command(*args, **kwargs)

    # Provider Plugin methods
    def get_services(self) -> dict[str, Any]:
        """Get all services provided by this plugin."""
        return {
            "service1": self._service1,
            "service2": self._service2,
        }

    def get_service(self, name: str) -> Any | None:
        """Get a service by name."""
        services = self.get_services()
        return services.get(name)

    # Command implementations
    def _command1(self, *args: object, **kwargs: object) -> Any:
        """Command 1 implementation."""
        return "Command 1 result"

    def _command2(self, *args: object, **kwargs: object) -> Any:
        """Command 2 implementation."""
        return "Command 2 result"

    # Service implementations
    @property
    def _service1(self) -> object:
        """Service 1 implementation."""
        return Service1()

    @property
    def _service2(self) -> object:
        """Service 2 implementation."""
        return Service2()


class Service1:
    """A service provided by the composite plugin."""

    def do_something(self) -> str:
        """Do something."""
        return "Service 1 result"


class Service2:
    """Another service provided by the composite plugin."""

    def do_something_else(self) -> str:
        """Do something else."""
        return "Service 2 result"
```

## Anti-Patterns

### Common Mistakes

1. **Direct Instantiation**: Avoid creating plugin instances directly. Instead, use factory functions.

   ```python
   # Bad
   from my_quacktool.plugins import MyPlugin
   plugin = MyPlugin()
   
   # Good
   from my_quacktool.plugin import create_plugin
   plugin = create_plugin()
   ```

2. **Hardcoded Dependencies**: Avoid hardcoding dependencies to other plugins. Instead, use the registry to look them up.

   ```python
   # Bad
   from other_quacktool.plugins import OtherPlugin
   
   class MyPlugin:
       def __init__(self):
           self.other_plugin = OtherPlugin()
   
   # Good
   from quack_core.modules import registry
   
   class MyPlugin:
       def __init__(self):
           self.other_plugin = registry.get_plugin("other-plugin")
   ```

3. **Missing Validation**: Always validate plugin requirements before use.

   ```python
   # Bad
   def execute_command(self, name: str, *args, **kwargs):
       command = self.get_command(name)
       return command(*args, **kwargs)  # May raise an AttributeError if command is None
   
   # Good
   def execute_command(self, name: str, *args, **kwargs):
       command = self.get_command(name)
       if command is None:
           raise ValueError(f"Command '{name}' not found")
       return command(*args, **kwargs)
   ```

### Performance Issues

1. **Excessive Plugin Loading**: Avoid loading plugins that you don't need.

   ```python
   # Bad: Loading all modules
   plugins = loader.discover_plugins()
   
   # Good: Load only the modules you need
   plugins = loader.load_plugins(["plugin1", "plugin2"])
   ```

2. **Complex Plugin Initialization**: Keep plugin initialization simple to avoid performance issues.

   ```python
   # Bad: Complex initialization
   class MyPlugin:
       def __init__(self):
           # Expensive _ops during initialization
           self.data = self._load_large_dataset()
   
   # Good: Lazy initialization
   class MyPlugin:
       def __init__(self):
           # Defer expensive _ops
           self._data = None
       
       @property
       def data(self):
           if self._data is None:
               self._data = self._load_large_dataset()
           return self._data
   ```

## Examples

### Basic QuackTool

Here's a complete example of a basic QuackTool:

```python
# my_quacktool/plugin.py
from quack_core.modules.protocols import CommandPluginProtocol
from typing import Any, Callable


class MyQuackTool:
    """A basic QuackTool plugin."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "my-quacktool"

    def list_commands(self) -> list[str]:
        """List all commands provided by this plugin."""
        return ["quack", "duck"]

    def get_command(self, name: str) -> Callable[..., Any] | None:
        """Get a command by name."""
        commands = {
            "quack": self._quack_command,
            "duck": self._duck_command,
        }
        return commands.get(name)

    def execute_command(self, name: str, *args: object, **kwargs: object) -> Any:
        """Execute a command."""
        command = self.get_command(name)
        if command is None:
            raise ValueError(f"Command '{name}' not found")
        return command(*args, **kwargs)

    def _quack_command(self, times: int = 1) -> str:
        """Quack a certain number of times."""
        return "Quack! " * times

    def _duck_command(self, name: str = "Anonymous") -> str:
        """Greet a duck."""
        return f"Hello, {name} the Duck!"


def create_plugin() -> CommandPluginProtocol:
    """Factory function to create the plugin."""
    return MyQuackTool()
```

### Advanced QuackTool

Here's an example of a more advanced QuackTool that uses multiple plugin types:

```python
# advanced_quacktool/plugin.py
from quack_core.modules.protocols import (
    CommandPluginProtocol,
    ConfigurablePluginProtocol,
    ProviderPluginProtocol,
)
from typing import Any, Callable


class AdvancedQuackTool:
    """An advanced QuackTool plugin."""

    def __init__(self) -> None:
        """Initialize the plugin."""
        self._config = {
            "quack_volume": "normal",
            "duck_color": "yellow",
        }

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "advanced-quacktool"

    # Command Plugin methods
    def list_commands(self) -> list[str]:
        """List all commands provided by this plugin."""
        return ["fancy-quack", "super-duck"]

    def get_command(self, name: str) -> Callable[..., Any] | None:
        """Get a command by name."""
        commands = {
            "fancy-quack": self._fancy_quack_command,
            "super-duck": self._super_duck_command,
        }
        return commands.get(name)

    def execute_command(self, name: str, *args: object, **kwargs: object) -> Any:
        """Execute a command."""
        command = self.get_command(name)
        if command is None:
            raise ValueError(f"Command '{name}' not found")
        return command(*args, **kwargs)

    # Provider Plugin methods
    def get_services(self) -> dict[str, Any]:
        """Get all services provided by this plugin."""
        return {
            "duck-translator": self._duck_translator_service,
            "quack-analyzer": self._quack_analyzer_service,
        }

    def get_service(self, name: str) -> Any | None:
        """Get a service by name."""
        services = self.get_services()
        return services.get(name)

    # Configurable Plugin methods
    def configure(self, config: dict[str, Any]) -> None:
        """Configure the plugin."""
        valid, errors = self.validate_config(config)
        if not valid:
            raise ValueError(f"Invalid configuration: {errors}")
        self._config.update(config)

    def get_config_schema(self) -> dict[str, Any]:
        """Get the configuration schema for this plugin."""
        return {
            "type": "object",
            "properties": {
                "quack_volume": {
                    "type": "string",
                    "enum": ["quiet", "normal", "loud"],
                },
                "duck_color": {
                    "type": "string",
                },
            },
        }

    def validate_config(self, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a configuration dictionary."""
        errors = []
        if "quack_volume" in config and config["quack_volume"] not in ["quiet", "normal", "loud"]:
            errors.append("quack_volume must be one of: quiet, normal, loud")
        if "duck_color" in config and not isinstance(config["duck_color"], str):
            errors.append("duck_color must be a string")
        return (len(errors) == 0, errors)

    # Command implementations
    def _fancy_quack_command(self, times: int = 1) -> str:
        """A fancy quack command."""
        volume = self._config["quack_volume"]
        quack = {
            "quiet": "quack",
            "normal": "Quack",
            "loud": "QUACK!!!",
        }.get(volume, "Quack")
        return f"{quack} " * times

    def _super_duck_command(self, name: str = "Super") -> str:
        """A super duck command."""
        color = self._config["duck_color"]
        return f"Behold! {name} the {color.capitalize()} Super Duck has arrived!"

    # Service implementations
    @property
    def _duck_translator_service(self) -> object:
        """A duck translator service."""
        return DuckTranslatorService()

    @property
    def _quack_analyzer_service(self) -> object:
        """A quack analyzer service."""
        return QuackAnalyzerService()


class DuckTranslatorService:
    """A service for translating duck language."""

    def duck_to_human(self, duck_text: str) -> str:
        """Translate from duck to human."""
        # Implementation...
        return f"Human translation: {duck_text.replace('quack', 'hello')}"

    def human_to_duck(self, human_text: str) -> str:
        """Translate from human to duck."""
        # Implementation...
        return f"Duck translation: {human_text.replace('hello', 'quack')}"


class QuackAnalyzerService:
    """A service for analyzing quack patterns."""

    def analyze_quack(self, quack_text: str) -> dict:
        """Analyze a quack pattern."""
        # Implementation...
        return {
            "quack_count": quack_text.lower().count("quack"),
            "sentiment": "happy" if "!" in quack_text else "neutral",
            "loudness": "loud" if quack_text.isupper() else "normal",
        }


def create_plugin() -> CommandPluginProtocol:
    """Factory function to create the plugin."""
    return AdvancedQuackTool()
```

## Advanced Usage

### Plugin Dependency Management

When building complex QuackTools, you may need to manage dependencies between plugins. Here are some strategies for handling plugin dependencies:

#### Runtime Dependency Resolution

Check for dependencies at runtime and provide meaningful error messages:

```python
from quack_core.modules import registry


class MyPlugin:
    """A plugin with dependencies."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "my-plugin"

    def __init__(self) -> None:
        """Initialize the plugin."""
        # Check for dependencies
        required_plugins = ["database-provider", "config-manager"]
        missing_plugins = []

        for plugin_name in required_plugins:
            if not registry.is_registered(plugin_name):
                missing_plugins.append(plugin_name)

        if missing_plugins:
            raise RuntimeError(
                f"The following required modules are missing: {', '.join(missing_plugins)}"
            )

        # Get dependencies
        self.database = registry.get_plugin("database-provider")
        self.config = registry.get_plugin("config-manager")
```

#### Optional Dependencies

Handle optional dependencies gracefully:

```python
from quack_core.modules import registry


class MyPlugin:
    """A plugin with optional dependencies."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "my-plugin"

    def __init__(self) -> None:
        """Initialize the plugin."""
        # Check for optional dependencies
        self.analytics = None
        if registry.is_registered("analytics-provider"):
            self.analytics = registry.get_plugin("analytics-provider")

    def log_event(self, event_name: str, data: dict) -> None:
        """Log an event if the analytics provider is available."""
        if self.analytics is not None:
            self.analytics.get_service("event-logger").log(event_name, data)
        # Fallback behavior if analytics is not available
        else:
            print(f"Event: {event_name}, Data: {data}")
```

### Plugin Versioning

When developing plugins for QuackCore, it's important to consider versioning to ensure compatibility. Here are some versioning strategies:

#### Semantic Versioning

Use semantic versioning for your plugins:

```python
class MyPlugin:
    """A plugin with version information."""
    
    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "my-plugin"
    
    @property
    def version(self) -> str:
        """Get the plugin version."""
        return "1.2.3"  # Major.Minor.Patch
```

#### Version Compatibility Checks

Check for compatibility with QuackCore:

```python
import importlib.metadata
from packaging import version

class MyPlugin:
    """A plugin with compatibility checks."""
    
    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "my-plugin"
    
    def __init__(self) -> None:
        """Initialize the plugin."""
        # Check QuackCore version
        try:
            quackcore_version = importlib.metadata.version("quack-core")
            if version.parse(quackcore_version) < version.parse("1.0.0"):
                print(f"Warning: This plugin requires QuackCore 1.0.0 or higher. "
                      f"Current version: {quackcore_version}")
        except importlib.metadata.PackageNotFoundError:
            print("Warning: Could not determine QuackCore version")
```

### Dynamic Plugin Loading

For advanced use cases, you might want to dynamically load plugins based on configuration or user input:

```python
from quack_core.modules import loader, registry
from typing import List


def load_plugins_from_config(config: dict) -> List[str]:
    """
    Load modules based on configuration.
    
    Args:
        config: Configuration dictionary with plugin settings.
        
    Returns:
        List of loaded plugin names.
    """
    loaded_plugins = []

    # Load core modules
    if config.get("load_core_plugins", True):
        core_plugins = loader.load_entry_points()
        for plugin in core_plugins:
            registry.register(plugin)
            loaded_plugins.append(plugin.name)

    # Load additional modules
    additional_modules = config.get("additional_plugins", [])
    if additional_modules:
        additional_plugins = loader.load_plugins(additional_modules)
        for plugin in additional_plugins:
            registry.register(plugin)
            loaded_plugins.append(plugin.name)

    return loaded_plugins
```

### Plugin Hot-Reloading

For development environments, implementing plugin hot-reloading can be useful:

```python
import importlib
import sys
from quack_core.modules import registry


def reload_plugin(plugin_name: str) -> bool:
    """
    Reload a plugin module and re-register the plugin.
    
    Args:
        plugin_name: Name of the plugin to reload.
        
    Returns:
        True if the plugin was successfully reloaded, False otherwise.
    """
    plugin = registry.get_plugin(plugin_name)
    if plugin is None:
        return False

    # Get the module name
    module_name = plugin.__class__.__module__

    # Unregister the plugin
    registry.unregister(plugin_name)

    # Reload the module
    if module_name in sys.modules:
        module = sys.modules[module_name]
        importlib.reload(module)

        # Re-create and register the plugin
        if hasattr(module, "create_plugin"):
            new_plugin = module.create_plugin()
            registry.register(new_plugin)
            return True

    return False
```

## Reference

### API Reference

#### Plugin Protocols

- **QuackPluginProtocol**: The base protocol for all plugins
  - **name**: Property that returns the plugin name

- **CommandPluginProtocol**: Protocol for plugins that provide commands
  - **list_commands()**: Returns a list of command names
  - **get_command(name)**: Returns a command function by name
  - **execute_command(name, *args, **kwargs)**: Executes a command

- **WorkflowPluginProtocol**: Protocol for plugins that provide workflows
  - **list_workflows()**: Returns a list of workflow names
  - **get_workflow(name)**: Returns a workflow function by name
  - **execute_workflow(name, *args, **kwargs)**: Executes a workflow

- **ExtensionPluginProtocol**: Protocol for plugins that extend other plugins
  - **get_target_plugin()**: Returns the name of the target plugin
  - **get_extensions()**: Returns a dictionary of extension functions

- **ProviderPluginProtocol**: Protocol for plugins that provide services
  - **get_services()**: Returns a dictionary of service objects
  - **get_service(name)**: Returns a service object by name

- **ConfigurablePluginProtocol**: Protocol for plugins that can be configured
  - **configure(config)**: Configures the plugin
  - **get_config_schema()**: Returns the configuration schema
  - **validate_config(config)**: Validates a configuration dictionary

#### Plugin Loader

- **load_plugin(module_path)**: Loads a plugin from a module path
- **load_plugins(modules)**: Loads multiple plugins from module paths
- **load_entry_points(group="quack_core.modules")**: Loads plugins from entry points
- **discover_plugins(entry_point_group="quack_core.modules", additional_modules=None)**: Discovers plugins from entry points and additional modules

#### Plugin Registry

- **register(plugin)**: Registers a plugin
- **unregister(name)**: Unregisters a plugin
- **get_plugin(name)**: Gets a plugin by name
- **list_plugins()**: Lists all registered plugins
- **is_registered(name)**: Checks if a plugin is registered
- **execute_command(command, *args, **kwargs)**: Executes a command
- **execute_workflow(workflow, *args, **kwargs)**: Executes a workflow

### Glossary

- **QuackTool**: A plugin that extends the functionality of QuackCore
- **QuackVerse**: The ecosystem of QuackCore plugins and applications
- **Plugin**: A modular component that can be dynamically loaded and registered
- **Protocol**: A contract that defines what a plugin should implement
- **Registry**: A central repository for managing plugins
- **Loader**: A component responsible for discovering and loading plugins
- **Entry Point**: A mechanism for Python packages to be automatically discovered
- **Factory Function**: A function that creates and returns a plugin instance
- **Command**: A function that can be executed by a CommandPlugin
- **Workflow**: A function that can be executed by a WorkflowPlugin
- **Service**: An object provided by a ProviderPlugin
- **Extension**: A function that extends another plugin
- **Configuration**: A dictionary of settings for a ConfigurablePlugin

# Building Effective QuackTools

## What Makes a Good QuackTool?

A good QuackTool follows the single responsibility principle and has a clear, focused purpose. Here are the characteristics of a well-designed QuackTool:

### Characteristics of a Good QuackTool

1. **Focused Functionality**: A good QuackTool addresses a specific problem domain or provides a specific capability. For example:
   - `quack-db`: A database integration plugin
   - `quack-nlp`: Natural language processing capabilities
   - `quack-viz`: Data visualization tools
   - `quack-auth`: Authentication and authorization services

2. **Clear Interface**: A good QuackTool has a well-defined interface that's easy to understand and use. It should provide:
   - Clearly named commands or services
   - Consistent parameter naming and ordering
   - Comprehensive but concise documentation

3. **Self-Contained**: A good QuackTool should be relatively self-contained, with minimal dependencies on other plugins. When dependencies exist, they should be clearly documented.

4. **Configurable**: A good QuackTool should be configurable to adapt to different environments or use cases, implementing the `ConfigurablePluginProtocol`.

5. **Error Handling**: A good QuackTool handles errors gracefully and provides meaningful error messages.

6. **Testing**: A good QuackTool includes comprehensive tests to ensure it works as expected.

### Examples of Good QuackTools

#### Data Processing QuackTool

```python
# quack_etl/plugin.py
from quack_core.modules.protocols import CommandPluginProtocol
from typing import Any, Callable, List, Dict


class QuackETL:
    """A plugin for Extract, Transform, Load _ops on data."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "quack-etl"

    def list_commands(self) -> List[str]:
        """List all commands provided by this plugin."""
        return ["extract", "transform", "load", "etl-pipeline"]

    def get_command(self, name: str) -> Callable[..., Any] | None:
        """Get a command by name."""
        commands = {
            "extract": self._extract_command,
            "transform": self._transform_command,
            "load": self._load_command,
            "etl-pipeline": self._etl_pipeline_command,
        }
        return commands.get(name)

    def execute_command(self, name: str, *args: object, **kwargs: object) -> Any:
        """Execute a command."""
        command = self.get_command(name)
        if command is None:
            raise ValueError(f"Command '{name}' not found")
        return command(*args, **kwargs)

    def _extract_command(self, source: str, **options) -> List[Dict]:
        """Extract data from a source."""
        # Implementation to extract data from various sources
        # (files, databases, APIs, etc.)
        if source.endswith('.csv'):
            return self._extract_from_csv(source, **options)
        elif source.endswith('.json'):
            return self._extract_from_json(source, **options)
        # ... other source types
        else:
            raise ValueError(f"Unsupported source type: {source}")

    def _transform_command(self, data: List[Dict], transformations: List[Dict]) -> List[Dict]:
        """Apply transformations to data."""
        # Implementation to transform data based on specified transformations
        result = data.copy()
        for transformation in transformations:
            transform_type = transformation.get('type')
            if transform_type == 'filter':
                result = self._filter_transform(result, transformation)
            elif transform_type == 'map':
                result = self._map_transform(result, transformation)
            # ... other transformation types
            else:
                raise ValueError(f"Unsupported transformation type: {transform_type}")
        return result

    def _load_command(self, data: List[Dict], destination: str, **options) -> Dict:
        """Load data to a destination."""
        # Implementation to load data to various destinations
        # (files, databases, APIs, etc.)
        if destination.endswith('.csv'):
            return self._load_to_csv(data, destination, **options)
        elif destination.endswith('.json'):
            return self._load_to_json(data, destination, **options)
        # ... other destination types
        else:
            raise ValueError(f"Unsupported destination type: {destination}")

    def _etl_pipeline_command(self, source: str, destination: str, transformations: List[Dict] = None,
                              **options) -> Dict:
        """Run a full ETL pipeline."""
        # Extract
        data = self._extract_command(source, **options)

        # Transform
        if transformations:
            data = self._transform_command(data, transformations)

        # Load
        result = self._load_command(data, destination, **options)

        return {
            "source": source,
            "destination": destination,
            "records_processed": len(data),
            "result": result,
        }

    # Helper methods for extraction
    def _extract_from_csv(self, source: str, **options) -> List[Dict]:
        """Extract data from a CSV file."""
        # Implementation...
        pass

    def _extract_from_json(self, source: str, **options) -> List[Dict]:
        """Extract data from a JSON file."""
        # Implementation...
        pass

    # Helper methods for transformations
    def _filter_transform(self, data: List[Dict], transformation: Dict) -> List[Dict]:
        """Filter data based on criteria."""
        # Implementation...
        pass

    def _map_transform(self, data: List[Dict], transformation: Dict) -> List[Dict]:
        """Map data fields based on mapping rules."""
        # Implementation...
        pass

    # Helper methods for loading
    def _load_to_csv(self, data: List[Dict], destination: str, **options) -> Dict:
        """Load data to a CSV file."""
        # Implementation...
        pass

    def _load_to_json(self, data: List[Dict], destination: str, **options) -> Dict:
        """Load data to a JSON file."""
        # Implementation...
        pass


def create_plugin() -> CommandPluginProtocol:
    """Factory function to create the plugin."""
    return QuackETL()
```

#### Authentication QuackTool

```python
# quack_auth/plugin.py
from quack_core.modules.protocols import ProviderPluginProtocol
from typing import Any, Dict, Optional, List


class QuackAuth:
    """A plugin for authentication and authorization."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "quack-auth"

    def get_services(self) -> Dict[str, Any]:
        """Get all services provided by this plugin."""
        return {
            "authentication": self._authentication_service,
            "authorization": self._authorization_service,
            "user-management": self._user_management_service,
        }

    def get_service(self, name: str) -> Any | None:
        """Get a service by name."""
        services = self.get_services()
        return services.get(name)

    @property
    def _authentication_service(self) -> object:
        """Authentication service."""
        return AuthenticationService()

    @property
    def _authorization_service(self) -> object:
        """Authorization service."""
        return AuthorizationService()

    @property
    def _user_management_service(self) -> object:
        """User management service."""
        return UserManagementService()


class AuthenticationService:
    """Authentication service."""

    def authenticate(self, username: str, password: str) -> Dict:
        """Authenticate a user."""
        # Implementation...
        pass

    def verify_token(self, token: str) -> Dict:
        """Verify an authentication token."""
        # Implementation...
        pass

    def refresh_token(self, refresh_token: str) -> Dict:
        """Refresh an authentication token."""
        # Implementation...
        pass


class AuthorizationService:
    """Authorization service."""

    def check_permission(self, user_id: str, resource: str, action: str) -> bool:
        """Check if a user has permission to perform an action on a resource."""
        # Implementation...
        pass

    def get_user_roles(self, user_id: str) -> List[str]:
        """Get the roles assigned to a user."""
        # Implementation...
        pass

    def add_role_to_user(self, user_id: str, role: str) -> bool:
        """Add a role to a user."""
        # Implementation...
        pass


class UserManagementService:
    """User management service."""

    def create_user(self, username: str, password: str, **user_data) -> Dict:
        """Create a new user."""
        # Implementation...
        pass

    def update_user(self, user_id: str, **user_data) -> Dict:
        """Update a user."""
        # Implementation...
        pass

    def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        # Implementation...
        pass

    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get a user by ID."""
        # Implementation...
        pass


def create_plugin() -> ProviderPluginProtocol:
    """Factory function to create the plugin."""
    return QuackAuth()
```

## What Should Not Be a QuackTool?

Not everything should be designed as a QuackTool. Here are some examples of what should not be implemented as a QuackTool:

### Anti-Patterns for QuackTools

1. **Too Broad**: A plugin that tries to do too many unrelated things. For example, a `quack-everything` plugin that includes database access, UI components, and network utilities.

2. **Too Narrow**: A plugin that performs a function so specific that it could have been implemented as a simple utility function. For example, a `quack-adder` plugin that only adds two numbers.

3. **Core Functionality**: Functionality that should be part of the core framework rather than a plugin. For example, basic logging or configuration management.

4. **Internal Implementation Details**: Implementation details that should be hidden and not exposed as plugins.

5. **Tightly Coupled Components**: Components that are tightly coupled to specific application logic and wouldn't be useful in other contexts.

### Examples of What Not to Create as a QuackTool

#### Example 1: Too Broad

```python
# BAD EXAMPLE: Too broad and unfocused
class QuackUtilities:
    @property
    def name(self) -> str:
        return "quack-utilities"
    
    def list_commands(self) -> List[str]:
        return [
            "format-date", "validate-email", "encrypt-data", 
            "fetch-api", "parse-csv", "resize-image", 
            "generate-pdf", "compress-file", "send-email"
        ]
    
    # ... implementations for many unrelated commands
```

Instead, split this into focused plugins:
- `quack-datetime` for date/time operations
- `quack-validation` for validation operations
- `quack-crypto` for encryption/decryption
- `quack-http` for API operations
- etc.

#### Example 2: Too Narrow

```python
# BAD EXAMPLE: Too narrow to justify a plugin
class QuackAdder:
    @property
    def name(self) -> str:
        return "quack-adder"
    
    def list_commands(self) -> List[str]:
        return ["add"]
    
    def get_command(self, name: str) -> Callable[..., Any] | None:
        if name == "add":
            return self._add_command
        return None
    
    def execute_command(self, name: str, *args: object, **kwargs: object) -> Any:
        command = self.get_command(name)
        if command is None:
            raise ValueError(f"Command '{name}' not found")
        return command(*args, **kwargs)
    
    def _add_command(self, a: float, b: float) -> float:
        return a + b
```

Instead, this should be a utility function or part of a broader `quack-math` plugin.

## How QuackTools Can Interact with Each Other

QuackTools can interact in several ways:

### 1. Registry-Based Interaction

The most common way for QuackTools to interact is through the registry:

```python
from quack_core.modules import registry


class DataVisualizationPlugin:
    """A plugin for data visualization that depends on quack-etl."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "quack-viz"

    def __init__(self) -> None:
        """Initialize the plugin."""
        # Get the ETL plugin from the registry
        etl_plugin = registry.get_plugin("quack-etl")
        if etl_plugin is None:
            raise RuntimeError("quack-etl plugin is required but not found")

        self.etl_plugin = etl_plugin

    def list_commands(self) -> List[str]:
        """List all commands provided by this plugin."""
        return ["visualize-data", "create-chart", "export-visualization"]

    def get_command(self, name: str) -> Callable[..., Any] | None:
        """Get a command by name."""
        commands = {
            "visualize-data": self._visualize_data_command,
            "create-chart": self._create_chart_command,
            "export-visualization": self._export_visualization_command,
        }
        return commands.get(name)

    def execute_command(self, name: str, *args: object, **kwargs: object) -> Any:
        """Execute a command."""
        command = self.get_command(name)
        if command is None:
            raise ValueError(f"Command '{name}' not found")
        return command(*args, **kwargs)

    def _visualize_data_command(self, source: str, chart_type: str, **options) -> Dict:
        """Visualize data from a source."""
        # Use the ETL plugin to extract data
        data = registry.execute_command("extract", source=source, **options)

        # Process the data for visualization
        # ...

        # Generate the visualization
        return self._create_chart_command(data=data, chart_type=chart_type, **options)

    def _create_chart_command(self, data: List[Dict], chart_type: str, **options) -> Dict:
        """Create a chart from data."""
        # Implementation...
        pass

    def _export_visualization_command(self, chart: Dict, format: str, **options) -> str:
        """Export a visualization to a specific format."""
        # Implementation...
        pass
```

### 2. Extension Plugins

Extension plugins are designed specifically to extend other plugins:

```python
from quack_core.modules.protocols import ExtensionPluginProtocol
from typing import Any, Callable, Dict, List


class ETLExtensionPlugin:
    """An extension plugin for quack-etl."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "quack-etl-extension"

    def get_target_plugin(self) -> str:
        """Get the name of the plugin this extension targets."""
        return "quack-etl"

    def get_extensions(self) -> Dict[str, Callable[..., Any]]:
        """Get all extensions provided by this plugin."""
        return {
            "extract-from-excel": self._extract_from_excel,
            "extract-from-parquet": self._extract_from_parquet,
            "transform-pivot": self._transform_pivot,
        }

    def _extract_from_excel(self, source: str, **options) -> List[Dict]:
        """Extract data from an Excel file."""
        # Implementation...
        pass

    def _extract_from_parquet(self, source: str, **options) -> List[Dict]:
        """Extract data from a Parquet file."""
        # Implementation...
        pass

    def _transform_pivot(self, data: List[Dict], pivot_config: Dict) -> List[Dict]:
        """Pivot data based on configuration."""
        # Implementation...
        pass
```

### 3. Service Provider Interaction

Plugins can provide services that other plugins can consume:

```python
from quack_core.modules import registry


class DataAnalysisPlugin:
    """A plugin for data analysis that uses the quack-auth service."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "quack-analysis"

    def __init__(self) -> None:
        """Initialize the plugin."""
        # Check if auth plugin is available
        if not registry.is_registered("quack-auth"):
            print("Warning: quack-auth plugin not found. Authentication will be disabled.")

    def list_commands(self) -> List[str]:
        """List all commands provided by this plugin."""
        return ["analyze-data", "statistical-summary", "correlation-analysis"]

    def get_command(self, name: str) -> Callable[..., Any] | None:
        """Get a command by name."""
        commands = {
            "analyze-data": self._analyze_data_command,
            "statistical-summary": self._statistical_summary_command,
            "correlation-analysis": self._correlation_analysis_command,
        }
        return commands.get(name)

    def execute_command(self, name: str, *args: object, **kwargs: object) -> Any:
        """Execute a command."""
        command = self.get_command(name)
        if command is None:
            raise ValueError(f"Command '{name}' not found")

        # Check authentication if auth plugin is available
        if registry.is_registered("quack-auth"):
            user_token = kwargs.pop("token", None)
            if user_token:
                auth_plugin = registry.get_plugin("quack-auth")
                auth_service = auth_plugin.get_service("authentication")
                token_info = auth_service.verify_token(user_token)

                if not token_info.get("valid", False):
                    raise PermissionError("Invalid authentication token")

        return command(*args, **kwargs)

    def _analyze_data_command(self, data: List[Dict], analysis_type: str, **options) -> Dict:
        """Analyze data."""
        # Implementation...
        pass

    def _statistical_summary_command(self, data: List[Dict], columns: List[str] = None) -> Dict:
        """Generate a statistical summary of data."""
        # Implementation...
        pass

    def _correlation_analysis_command(self, data: List[Dict], target_column: str, **options) -> Dict:
        """Perform correlation analysis."""
        # Implementation...
        pass
```

### 4. Composite Commands

Plugins can create composite commands that use multiple plugins:

```python
from quack_core.modules import registry


def analyze_and_visualize(data_source: str, analysis_type: str, visualization_type: str, **options) -> Dict:
    """
    A composite command that combines data analysis and visualization.
    
    Args:
        data_source: The source of the data.
        analysis_type: The type of analysis to perform.
        visualization_type: The type of visualization to create.
        **options: Additional options.
        
    Returns:
        A dictionary with the analysis results and visualization.
    """
    # Extract data
    data = registry.execute_command("extract", source=data_source)

    # Analyze data
    analysis_results = registry.execute_command("analyze-data", data=data, analysis_type=analysis_type)

    # Visualize results
    visualization = registry.execute_command("create-chart", data=analysis_results, chart_type=visualization_type)

    return {
        "data_source": data_source,
        "analysis_type": analysis_type,
        "visualization_type": visualization_type,
        "analysis_results": analysis_results,
        "visualization": visualization,
    }


class WorkflowPlugin:
    """A plugin that defines workflows combining multiple modules."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "quack-workflows"

    def list_workflows(self) -> List[str]:
        """List all workflows provided by this plugin."""
        return ["data-pipeline", "etl-and-analyze", "analyze-and-visualize"]

    def get_workflow(self, name: str) -> Callable[..., Any] | None:
        """Get a workflow by name."""
        workflows = {
            "data-pipeline": self._data_pipeline_workflow,
            "etl-and-analyze": self._etl_and_analyze_workflow,
            "analyze-and-visualize": analyze_and_visualize,  # Using the function defined above
        }
        return workflows.get(name)

    def execute_workflow(self, name: str, *args: object, **kwargs: object) -> Any:
        """Execute a workflow."""
        workflow = self.get_workflow(name)
        if workflow is None:
            raise ValueError(f"Workflow '{name}' not found")
        return workflow(*args, **kwargs)

    def _data_pipeline_workflow(self, *args: object, **kwargs: object) -> Any:
        """Data pipeline workflow."""
        # Implementation...
        pass

    def _etl_and_analyze_workflow(self, *args: object, **kwargs: object) -> Any:
        """ETL and analyze workflow."""
        # Implementation...
        pass
```

### 5. Event-Based Communication

For more complex interactions, you can implement an event system:

```python
# First, create an event bus plugin
from quack_core.modules.protocols import ProviderPluginProtocol
from typing import Any, Callable, Dict, List, Set


class EventBusPlugin:
    """A plugin that provides an event bus for inter-plugin communication."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "quack-eventbus"

    def __init__(self) -> None:
        """Initialize the plugin."""
        self._subscribers: Dict[str, Set[Callable]] = {}

    def get_services(self) -> Dict[str, Any]:
        """Get all services provided by this plugin."""
        return {
            "event-bus": self,
        }

    def get_service(self, name: str) -> Any | None:
        """Get a service by name."""
        services = self.get_services()
        return services.get(name)

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: The type of event to subscribe to.
            callback: The callback function to call when the event occurs.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = set()
        self._subscribers[event_type].add(callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: The type of event to unsubscribe from.
            callback: The callback function to unsubscribe.
        """
        if event_type in self._subscribers:
            self._subscribers[event_type].discard(callback)
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]

    def publish(self, event_type: str, event_data: Any = None) -> None:
        """
        Publish an event.
        
        Args:
            event_type: The type of event to publish.
            event_data: The data to include with the event.
        """
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(event_type, event_data)
                except Exception as e:
                    print(f"Error in event callback: {e}")


def create_plugin() -> ProviderPluginProtocol:
    """Factory function to create the plugin."""
    return EventBusPlugin()
```

Then, plugins can communicate through the event bus:

```python
from quack_core.modules import registry


class DataLoggerPlugin:
    """A plugin that logs data events."""

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "quack-logger"

    def __init__(self) -> None:
        """Initialize the plugin."""
        # Get the event bus
        if not registry.is_registered("quack-eventbus"):
            raise RuntimeError("quack-eventbus plugin is required but not found")

        event_bus_plugin = registry.get_plugin("quack-eventbus")
        self.event_bus = event_bus_plugin.get_service("event-bus")

        # Subscribe to events
        self.event_bus.subscribe("data.extracted", self._on_data_extracted)
        self.event_bus.subscribe("data.transformed", self._on_data_transformed)
        self.event_bus.subscribe("data.loaded", self._on_data_loaded)

    def _on_data_extracted(self, event_type: str, event_data: Any) -> None:
        """Handle data extracted event."""
        print(f"Data extracted: {event_data.get('source')}, {event_data.get('record_count')} records")

    def _on_data_transformed(self, event_type: str, event_data: Any) -> None:
        """Handle data transformed event."""
        print(f"Data transformed: {event_data.get('transformation_type')}")

    def _on_data_loaded(self, event_type: str, event_data: Any) -> None:
        """Handle data loaded event."""
        print(f"Data loaded: {event_data.get('destination')}, {event_data.get('record_count')} records")


def create_plugin() -> ProviderPluginProtocol:
    """Factory function to create the plugin."""
    return DataLoggerPlugin()
```

And publish events from other plugins:

```python
# In the ETL plugin
def _extract_command(self, source: str, **options) -> List[Dict]:
    """Extract data from a source."""
    # Implementation...
    
    # Get the event bus if available
    if registry.is_registered("quack-eventbus"):
        event_bus_plugin = registry.get_plugin("quack-eventbus")
        event_bus = event_bus_plugin.get_service("event-bus")
        
        # Publish event
        event_bus.publish("data.extracted", {
            "source": source,
            "record_count": len(data),
            "options": options,
        })
    
    return data
```

## Best Practices for QuackTool Interactions

When designing QuackTools that interact with each other, follow these best practices:

1. **Loose Coupling**: Design plugins to be loosely coupled, with clear interfaces for interaction.

2. **Graceful Degradation**: Handle missing dependencies gracefully, either by providing fallback behavior or clearly communicating requirements.

3. **Clear Documentation**: Document the dependencies and interactions between plugins.

4. **Versioning**: Use versioning to manage compatibility between plugins.

5. **Consistent Interfaces**: Use consistent naming and parameter conventions across plugins.

6. **Error Handling**: Provide clear error messages when interaction fails.

By following these guidelines, you can create a robust ecosystem of QuackTools that work together seamlessly while maintaining modularity and flexibility.