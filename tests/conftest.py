# === QV-LLM:BEGIN ===
# path: quack-core/tests/conftest.py
# role: tests
# neighbors: __init__.py, test_helper.py
# exports: MockPlugin, mock_fs_standalone, patch_filesystem_operations, temp_dir, test_file, test_binary_file, sample_config, mock_env_vars (+4 more)
# git_branch: refactor/toolkitWorkflow
# git_commit: 5d876e8
# === QV-LLM:END ===

"""
Shared fixtures for QuackCore tests.
"""

# Import the test helper first to set up the Python path

import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from _pytest.monkeypatch import MonkeyPatch

# Now try to import the quack-core modules
try:
    from quack_core.config.models import QuackConfig
    from quack_core.lib.fs import DataResult, OperationResult
    from quack_core.lib.fs.service import standalone as fs_standalone
    from quack_core.modules.protocols import QuackPluginProtocol
except ImportError as e:
    print(f"Error importing quack-core modules: {e}")
    # Emergency fallbacks if needed
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
    from quack_core.config.models import QuackConfig
    from quack_core.lib.fs import DataResult, OperationResult
    from quack_core.lib.fs.service import standalone as fs_standalone
    from quack_core.modules.protocols import QuackPluginProtocol


@pytest.fixture(autouse=True)
def mock_fs_standalone():
    """
    Mock the fs.standalone functionality for consistent test behavior
    across different platforms.

    This helps us handle path issues in tests by normalizing the
    behavior of the underlying fs module.
    """
    with patch("quack_core.lib.fs.service.standalone.normalize_path") as mock_normalize:
        # Make normalize_path return Path objects for consistent behavior
        mock_normalize.side_effect = lambda p: Path(os.path.abspath(str(p)))
        yield


@pytest.fixture(autouse=True)
def patch_filesystem_operations():
    """
    Patch filesystem operations for tests.

    This fixture ensures that DataResult and OperationResult objects
    are handled correctly in path-related operations during tests.
    """
    # Original Path.__init__ to preserve original behavior
    original_path_init = Path.__init__

    # Patched version that handles DataResult
    def patched_path_init(self, *args, **kwargs):
        new_args = list(args)
        for i, arg in enumerate(new_args):
            if isinstance(arg, (DataResult, OperationResult)) and hasattr(arg, "data"):
                new_args[i] = str(arg.data)
            elif hasattr(arg, "__fspath__"):
                try:
                    new_args[i] = arg.__fspath__()
                except Exception:
                    pass

        # Call original __init__ with potentially modified args
        original_path_init(self, *new_args)

    # Patch Path.__init__ to handle DataResult
    with patch("pathlib.Path.__init__", patched_path_init):
        yield


@pytest.fixture
def temp_dir() -> Generator[Path]:
    """Create a temporary directory for tests."""
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        yield tmp_dir
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def test_file(temp_dir: Path) -> Generator[Path]:
    """Create a test file with content."""
    file_path = temp_dir / "test_file.txt"
    with open(file_path, "w") as f:
        f.write("test content")
    yield file_path


@pytest.fixture
def test_binary_file(
        temp_dir: Path,
) -> Generator[Path]:
    """Create a binary test file."""
    file_path = temp_dir / "test_binary_file.bin"
    with open(file_path, "wb") as f:
        f.write(b"\x00\x01\x02\x03")
    yield file_path


@pytest.fixture
def sample_config(temp_dir: Path) -> QuackConfig:
    """Create a sample configuration."""
    # We use string paths instead of Path objects here
    temp_dir_str = str(temp_dir)
    base_dir = temp_dir_str
    output_dir = os.path.join(temp_dir_str, "output")

    # Using strings for paths in the configuration
    return QuackConfig(
        general={
            "project_name": "TestProject",
            "environment": "test",
            "debug": True,
        },
        paths={
            "base_dir": base_dir,
            "output_dir": output_dir,
            "assets_dir": "./assets",
            "data_dir": "./data",
            "temp_dir": "./temp",
        },
        logging={
            "level": "DEBUG",
            "file": None,
            "console": True,
        },
        integrations={
            "google": {
                "client_secrets_file": None,
                "credentials_file": None,
                "shared_folder_id": None,
                "gmail_labels": [],
                "gmail_days_back": 1,
            },
            "notion": {
                "api_key": None,
                "database_ids": {},
            },
        },
        plugins={
            "enabled": [],
            "disabled": [],
            "paths": [],
        },
    )


@pytest.fixture
def mock_env_vars(monkeypatch: MonkeyPatch) -> None:
    """Set up environment variables for testing."""
    monkeypatch.setenv("QUACK_ENV", "test")
    monkeypatch.setenv("QUACK_GENERAL__DEBUG", "true")
    monkeypatch.setenv("QUACK_LOGGING__LEVEL", "DEBUG")


@pytest.fixture
def mock_project_structure(temp_dir: Path) -> Path:
    """Create a mock project structure for testing."""
    # Create project root with marker files
    project_root = temp_dir / "test_project"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text("# Mock pyproject.toml")

    # Create src directory with module structure
    src_dir = project_root / "src"
    src_dir.mkdir()
    (src_dir / "__init__.py").touch()

    # Create module directory
    module_dir = src_dir / "test_module"
    module_dir.mkdir()
    (module_dir / "__init__.py").touch()

    # Create test file with some content
    test_module_file = module_dir / "test_file.py"
    test_module_file.write_text("def test_function():\n    return True")

    # Create other standard directories
    (project_root / "tests").mkdir()
    (project_root / "docs").mkdir()
    (project_root / "output").mkdir()
    (project_root / "config").mkdir()

    # Create a config file
    config_file = project_root / "config" / "default.yaml"
    config_file.write_text("general:\n  project_name: TestProject\n")

    return project_root


class MockPlugin(QuackPluginProtocol):
    """Mock plugin for testing."""

    @property
    def name(self) -> str:
        return "mock_plugin"


@pytest.fixture
def mock_plugin() -> MockPlugin:
    """Create a mock plugin for testing."""
    return MockPlugin()


def pytest_configure(config):
    """Register custom pytest marks."""
    config.addinivalue_line(
        "markers", "integration: mark a test as an integration test"
    )


# Fix for the mock_normalize_path fixture
@pytest.fixture(autouse=True)
def mock_normalize_path(monkeypatch):
    """Mock the normalize_path function to avoid filesystem access."""

    def mock_normalize(path):
        return Path(os.path.abspath(str(path)))

    # Fix: Use the correct import path for normalize_path
    monkeypatch.setattr(fs_standalone, "normalize_path", mock_normalize)
