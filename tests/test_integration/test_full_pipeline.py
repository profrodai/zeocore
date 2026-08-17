"""
Integration tests for ZeoCore components working together.
"""

from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from zeo_core.config.loader import load_config
from zeo_core.config.models import ZeoConfig
from zeo_core.core.errors import ZeoError
from zeo_core.core.fs.service import FileSystemService
from zeo_core.core.paths import PathResolver
from zeo_core.core.paths import service as paths
from zeo_core.modules.protocols import (
    CommandPluginProtocol,
    ProviderPluginProtocol,
    ZeoPluginMetadata,
)
from zeo_core.modules.registry import PluginRegistry


# Test modules to register in the registry
class SampleFilePlugin(CommandPluginProtocol):
    """A test plugin for file _ops."""

    def __init__(self, fs_service: FileSystemService) -> None:
        """Initialize with a filesystem service."""
        self.fs = fs_service

    @property
    def plugin_id(self) -> str:
        return "file_plugin"

    @property
    def name(self) -> str:
        return "file_plugin"

    def get_metadata(self) -> ZeoPluginMetadata:
        return ZeoPluginMetadata(
            plugin_id=self.plugin_id,
            name=self.name,
            version="1.0.0",
            description="Test plugin for file operations",
            capabilities=[],
        )

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
            raise ZeoError(f"Failed to read file: {result.error}")
        assert result.content is not None
        return result.content

    def write_file(self, path: str, content: str) -> bool:
        """Write content to a file."""
        result = self.fs.write_text(path, content)
        return result.success


class SamplePathPlugin(CommandPluginProtocol):
    """A test plugin for path _ops."""

    def __init__(self, path_resolver: PathResolver) -> None:
        """Initialize with a path resolver."""
        self.resolver = path_resolver

    @property
    def plugin_id(self) -> str:
        return "path_plugin"

    @property
    def name(self) -> str:
        return "path_plugin"

    def get_metadata(self) -> ZeoPluginMetadata:
        return ZeoPluginMetadata(
            plugin_id=self.plugin_id,
            name=self.name,
            version="1.0.0",
            description="Test plugin for path operations",
            capabilities=[],
        )

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
        # paths.get_project_root/resolve_project_path are PathService INSTANCE
        # methods, not module-level free functions (the module never had
        # free functions -- see the sibling test_paths chain's own conftest
        # note, which established this same fact).
        result = paths.PathService().get_project_root(start_dir)
        if not result.success:
            raise ZeoError(f"Failed to find project root: {result.error}")
        assert result.path is not None
        return Path(result.path)

    def resolve_path(self, path: str, project_root: str | None = None) -> Path:
        """Resolve a path relative to the project root."""
        result = paths.PathService().resolve_project_path(path, project_root)
        if not result.success:
            raise ZeoError(f"Failed to resolve path: {result.error}")
        assert result.path is not None
        return Path(result.path)


class SampleConfigProvider(ProviderPluginProtocol):
    """A test plugin providing configuration services."""

    def __init__(self, config: ZeoConfig) -> None:
        """Initialize with a configuration."""
        self.config = config

    @property
    def plugin_id(self) -> str:
        return "config_provider"

    @property
    def name(self) -> str:
        return "config_provider"

    def get_metadata(self) -> ZeoPluginMetadata:
        return ZeoPluginMetadata(
            plugin_id=self.plugin_id,
            name=self.name,
            version="1.0.0",
            description="Test plugin providing configuration services",
            capabilities=[],
        )

    def get_services(self) -> dict[str, object]:
        return {"get_config": self.get_config, "get_value": self.get_value}

    def get_service(self, name: str) -> object | None:
        return self.get_services().get(name)

    def get_config(self) -> ZeoConfig:
        """Get the current configuration."""
        return self.config

    def get_value(self, path: str, default: object | None = None) -> object | None:
        """Get a configuration value by path."""
        from zeo_core.config.utils import get_config_value

        return get_config_value(self.config, path, default)


class TestIntegration:
    """Integration tests for ZeoCore components."""

    def test_config_to_filesystem_pipeline(self, temp_dir: Path) -> None:
        """Test integrating configuration with filesystem _ops."""
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

        # Test read/write _ops using configured paths
        output_file = output_dir / "output.txt"

        write_result = fs_service.write_text(output_file, "Generated output")
        assert write_result.success is True

        read_result = fs_service.read_text(test_file)
        assert read_result.success is True
        assert read_result.content == "Test data content"

        # Test reading through resolved paths
        data_path_result = paths.PathService().resolve_project_path(
            "data/test.txt", temp_dir
        )
        assert data_path_result.success is True
        data_path = data_path_result.path
        assert data_path is not None
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
        config = ZeoConfig(
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
        assert isinstance(retrieved_config, ZeoConfig)
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
        with pytest.raises(ZeoError):
            registry.execute_command("read_file", "nonexistent.txt")

        # Test error handling for non-existent command
        with pytest.raises(ZeoError):
            registry.execute_command("nonexistent_command")

        # Test path resolution error handling - use SamplePathPlugin
        path_plugin = SamplePathPlugin(PathResolver())
        with pytest.raises(ZeoError):
            path_plugin.find_project_root("/nonexistent/path")

        # Test config loading error handling
        with pytest.raises(ZeoError):
            load_config("/nonexistent/config.yaml")
