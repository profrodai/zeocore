# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integration/test_full_pipeline.py
# role: tests
# neighbors: __init__.py
# exports: SampleFilePlugin, SamplePathPlugin, SampleConfigProvider, TestIntegration
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
# === QV-LLM:END ===

"""
Integration tests for QuackCore components working together.
"""

from collections.abc import Callable
from pathlib import Path

import pytest
import yaml
from quack_core.config.loader import load_config
from quack_core.config.models import QuackConfig
from quack_core.lib.errors import QuackError
from quack_core.lib.fs.service import FileSystemService
from quack_core.lib.paths import PathResolver
from quack_core.lib.paths import service as paths
from quack_core.modules.protocols import (
    CommandPluginProtocol,
    ProviderPluginProtocol,
)
from quack_core.modules.registry import PluginRegistry


# Test modules to register in the registry
class SampleFilePlugin(CommandPluginProtocol):
    """A test plugin for file _operations."""

    def __init__(self, fs_service: FileSystemService) -> None:
        """Initialize with a filesystem service."""
        self.fs = fs_service

    @property
    def name(self) -> str:
        return "file_plugin"

    def list_commands(self) -> list[str]:
        return ["read_file", "write_file"]

    def get_command(self, name: str) -> Callable | None:
        if name == "read_file":
            return self.read_file
        elif name == "write_file":
            return self.write_file
        return None

    def execute_command(self, name: str, *args: object, **kwargs: object) -> object:
        cmd = self.get_command(name)
        if cmd:
            return cmd(*args, **kwargs)
        raise ValueError(f"Command {name} not found")

    def read_file(self, path: str) -> str:
        """Read a file and return its content."""
        result = self.fs.read_text(path)
        if not result.success:
            raise QuackError(f"Failed to read file: {result.error}")
        return result.content

    def write_file(self, path: str, content: str) -> bool:
        """Write content to a file."""
        result = self.fs.write_text(path, content)
        return result.success


class SamplePathPlugin(CommandPluginProtocol):
    """A test plugin for path _operations."""

    def __init__(self, path_resolver: PathResolver) -> None:
        """Initialize with a path resolver."""
        self.resolver = path_resolver

    @property
    def name(self) -> str:
        return "path_plugin"

    def list_commands(self) -> list[str]:
        return ["find_project_root", "resolve_path"]

    def get_command(self, name: str) -> Callable | None:
        if name == "find_project_root":
            return self.find_project_root
        elif name == "resolve_path":
            return self.resolve_path
        return None

    def execute_command(self, name: str, *args: object, **kwargs: object) -> object:
        cmd = self.get_command(name)
        if cmd:
            return cmd(*args, **kwargs)
        raise ValueError(f"Command {name} not found")

    def find_project_root(self, start_dir: str | None = None) -> Path:
        """Find the project root directory."""
        result = paths.get_project_root(start_dir)
        if not result.success:
            raise QuackError(f"Failed to find project root: {result.error}")
        return result.path

    def resolve_path(self, path: str, project_root: str | None = None) -> Path:
        """Resolve a path relative to the project root."""
        result = paths.resolve_project_path(path, project_root)
        if not result.success:
            raise QuackError(f"Failed to resolve path: {result.error}")
        return result.path


class SampleConfigProvider(ProviderPluginProtocol):
    """A test plugin providing configuration services."""

    def __init__(self, config: QuackConfig) -> None:
        """Initialize with a configuration."""
        self.config = config

    @property
    def name(self) -> str:
        return "config_provider"

    def get_services(self) -> dict[str, object]:
        return {"get_config": self.get_config, "get_value": self.get_value}

    def get_service(self, name: str) -> object | None:
        return self.get_services().get(name)

    def get_config(self) -> QuackConfig:
        """Get the current configuration."""
        return self.config

    def get_value(self, path: str, default: object | None = None) -> object | None:
        """Get a configuration value by path."""
        from quack_core.config.utils import get_config_value

        return get_config_value(self.config, path, default)


class TestIntegration:
    """Integration tests for QuackCore components."""

    def test_config_to_filesystem_pipeline(self, temp_dir: Path) -> None:
        """Test integrating configuration with filesystem _operations."""
        # Create a test configuration file
        config_file = temp_dir / "test_config.yaml"  # Fixed string concatenation
        config_data = {
            "general": {"project_name": "TestProject"},
            "paths": {
                "base_dir": str(temp_dir),
                "output_dir": "output",
                "data_dir": "data",
            },
            "logging": {"level": "DEBUG"},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Create output and data directories
        output_dir = temp_dir / "output"
        data_dir = temp_dir / "data"
        output_dir.mkdir()
        data_dir.mkdir()

        # Add a test file to the data directory
        test_file = data_dir / "test.txt"
        test_file.write_text("Test data content")

        # Load the configuration
        config = load_config(str(config_file))

        # Create services using the configuration
        fs_service = FileSystemService(base_dir=config.paths.base_dir)

        # Test read/write _operations using configured paths
        output_file = output_dir / "output.txt"

        write_result = fs_service.write_text(output_file, "Generated output")
        assert write_result.success is True

        read_result = fs_service.read_text(test_file)
        assert read_result.success is True
        assert read_result.content == "Test data content"

        # Test reading through resolved paths
        data_path_result = paths.resolve_project_path("data/test.txt", temp_dir)
        assert data_path_result.success is True
        data_path = data_path_result.path
        assert Path(data_path) == test_file

        read_result = fs_service.read_text(data_path)
        assert read_result.success is True
        assert read_result.content == "Test data content"

    def test_plugin_system(self, temp_dir: Path) -> None:
        """Test the plugin system with integration between components."""
        # Create a test project structure
        test_file = temp_dir / "test.txt"
        test_file.write_text("Test content")

        # Initialize core components
        config = QuackConfig(
            general={"project_name": "TestProject"}, paths={"base_dir": str(temp_dir)}
        )
        fs_service = FileSystemService(base_dir=temp_dir)
        path_resolver = PathResolver()

        # Initialize modules
        file_plugin = SampleFilePlugin(fs_service)
        path_plugin = SamplePathPlugin(path_resolver)
        config_provider = SampleConfigProvider(config)

        # Register modules in the registry
        registry = PluginRegistry()
        registry.register(file_plugin)
        registry.register(path_plugin)
        registry.register(config_provider)

        # Test command execution through registry
        content = registry.execute_command("read_file", "test.txt")
        assert content == "Test content"

        new_file = "new_file.txt"
        success = registry.execute_command("write_file", new_file, "New content")
        assert success is True
        assert (temp_dir / new_file).exists()
        assert (temp_dir / new_file).read_text() == "New content"

        # Test getting service from provider
        config_provider_plugin = registry.get_provider_plugin("config_provider")
        assert config_provider_plugin is not None

        get_config_service = config_provider_plugin.get_service("get_config")
        assert callable(get_config_service)

        retrieved_config = get_config_service()
        assert isinstance(retrieved_config, QuackConfig)
        assert retrieved_config.general.project_name == "TestProject"

        # Test extension plugin functionality (if it were implemented)
        # This is a placeholder for actual extension plugin tests
        extensions = registry.get_extensions_for_plugin("file_plugin")
        assert isinstance(extensions, list)  # Should be empty in this test

    def test_error_handling_integration(self, temp_dir: Path) -> None:
        """Test error handling integration across components."""
        # Initialize core components
        fs_service = FileSystemService(base_dir=temp_dir)

        # Initialize plugin
        file_plugin = SampleFilePlugin(fs_service)

        # Register plugin in the registry
        registry = PluginRegistry()
        registry.register(file_plugin)

        # Test error handling when reading non-existent file
        with pytest.raises(QuackError):
            registry.execute_command("read_file", "nonexistent.txt")

        # Test error handling for non-existent command
        with pytest.raises(QuackError):
            registry.execute_command("nonexistent_command")

        # Test path resolution error handling - use SamplePathPlugin
        path_plugin = SamplePathPlugin(PathResolver())
        with pytest.raises(QuackError):
            path_plugin.find_project_root("/nonexistent/path")

        # Test config loading error handling
        with pytest.raises(QuackError):
            load_config("/nonexistent/config.yaml")
