"""
Shared fixtures for QuackCore tests.
"""

# Import the test helper first to set up the Python path

import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from _pytest.monkeypatch import MonkeyPatch

# Now try to import the quack-core modules
try:
    from quack_core.config.models import QuackConfig
    from quack_core.core.fs import DataResult, OperationResult, PathResult
    from quack_core.core.fs.protocols import FsPathLike
    from quack_core.core.fs.service import standalone as fs_standalone
    from quack_core.modules.protocols import QuackPluginMetadata, QuackPluginProtocol
except ImportError as e:
    print(f"Error importing quack-core modules: {e}")
    # Emergency fallbacks if needed
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
    from quack_core.config.models import QuackConfig
    from quack_core.core.fs import DataResult, OperationResult, PathResult
    from quack_core.core.fs.protocols import FsPathLike
    from quack_core.core.fs.service import standalone as fs_standalone
    from quack_core.modules.protocols import QuackPluginMetadata, QuackPluginProtocol


@pytest.fixture(autouse=True)
def mock_fs_standalone() -> Generator[None]:
    """
    Mock the fs.standalone functionality for consistent test behavior
    across different platforms.

    This helps us handle path issues in tests by normalizing the
    behavior of the underlying fs module.
    """
    with patch(
        "quack_core.core.fs.service.standalone.normalize_path"
    ) as mock_normalize:
        # Return a real PathResult (ok/path contract, core/fs SERVICE-CONTRACT) so
        # callers that check `.ok`/`.path` on the result see a well-formed object,
        # not a bare Path (which has neither attribute).
        def _mock_normalize(p: FsPathLike) -> "PathResult":
            resolved = Path(os.path.abspath(str(p)))
            return PathResult(
                ok=True,
                path=resolved,
                is_absolute=resolved.is_absolute(),
                is_valid=True,
                exists=resolved.exists(),
                message=f"Mock-normalized: {resolved}",
            )

        mock_normalize.side_effect = _mock_normalize
        yield


@pytest.fixture(autouse=True)
def patch_filesystem_operations() -> Generator[None]:
    """
    Patch filesystem _ops for tests.

    This fixture ensures that DataResult and OperationResult objects
    are handled correctly in path-related _ops during tests.
    """
    # Original Path.__init__ to preserve original behavior
    original_path_init = Path.__init__

    # Patched version that handles DataResult
    def patched_path_init(
        self: Path,
        *args: Any,  # noqa: ANN401 -- genuinely dynamic: monkeypatches Path.__init__ itself, must accept whatever Path's real constructor accepts
        **kwargs: Any,  # noqa: ANN401 -- genuinely dynamic: same as *args above
    ) -> None:
        new_args = list(args)
        for i, arg in enumerate(new_args):
            if isinstance(arg, (DataResult, OperationResult)) and hasattr(arg, "data"):
                new_args[i] = str(arg.data)
            elif hasattr(arg, "__fspath__"):
                try:
                    new_args[i] = arg.__fspath__()
                except Exception:  # noqa: S110 -- this patched __init__ runs on
                    # every Path() construction across the whole test suite; if
                    # __fspath__() fails, leaving the arg unchanged lets the real
                    # Path.__init__ raise its own natural error below, so
                    # swallowing here (not logging) avoids per-call log noise
                    # for a fallback path that's not itself an error.
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
    def plugin_id(self) -> str:
        return "mock_plugin"

    @property
    def name(self) -> str:
        return "mock_plugin"

    def get_metadata(self) -> QuackPluginMetadata:
        """Get plugin metadata."""
        return QuackPluginMetadata(
            plugin_id=self.plugin_id,
            name=self.name,
            version="1.0.0",
            description="Mock plugin for testing",
            capabilities=[],
        )


@pytest.fixture
def mock_plugin() -> MockPlugin:
    """Create a mock plugin for testing."""
    return MockPlugin()


def pytest_configure(config: pytest.Config) -> None:
    """Register custom pytest marks."""
    config.addinivalue_line(
        "markers", "integration: mark a test as an integration test"
    )


# Fix for the mock_normalize_path fixture
@pytest.fixture(autouse=True)
def mock_normalize_path(monkeypatch: MonkeyPatch) -> None:
    """Mock the normalize_path function to avoid filesystem access."""

    def mock_normalize(path: FsPathLike) -> "PathResult":
        # Return a real PathResult (ok/path contract, core/fs SERVICE-CONTRACT) so
        # callers that check `.ok`/`.path` on the result see a well-formed object,
        # not a bare Path (which has neither attribute) - PosixPath-has-no-attribute
        # 'ok' was exactly this fixture handing production code a bare Path.
        resolved = Path(os.path.abspath(str(path)))
        return PathResult(
            ok=True,
            path=resolved,
            is_absolute=resolved.is_absolute(),
            is_valid=True,
            exists=resolved.exists(),
            message=f"Mock-normalized: {resolved}",
        )

    # Fix: Use the correct import path for normalize_path
    monkeypatch.setattr(fs_standalone, "normalize_path", mock_normalize)
