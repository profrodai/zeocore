"""
Shared fixtures for ZeoCore tests.
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

# Now try to import the zeocore modules
try:
    from zeo_core.config.models import ZeoConfig
    from zeo_core.core.fs import DataResult, OperationResult, PathResult
    from zeo_core.core.fs.protocols import FsPathLike
    from zeo_core.core.fs.service import standalone as fs_standalone
    from zeo_core.modules.protocols import ZeoPluginMetadata, ZeoPluginProtocol
except ImportError as e:
    print(f"Error importing zeocore modules: {e}")
    # Emergency fallbacks if needed
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
    from zeo_core.config.models import ZeoConfig
    from zeo_core.core.fs import DataResult, OperationResult, PathResult
    from zeo_core.core.fs.protocols import FsPathLike
    from zeo_core.core.fs.service import standalone as fs_standalone
    from zeo_core.modules.protocols import ZeoPluginMetadata, ZeoPluginProtocol


@pytest.fixture(autouse=True)
def mock_fs_standalone() -> Generator[None]:
    """
    Mock the fs.standalone functionality for consistent test behavior
    across different platforms.

    This helps us handle path issues in tests by normalizing the
    behavior of the underlying fs module.
    """
    with patch("zeo_core.core.fs.service.standalone.normalize_path") as mock_normalize:
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

    Version note (see RULING/CI failure on py3.10 + py3.11, both green on
    3.12/3.13): pathlib's own __new__/__init__ split changed in the 3.12
    rewrite.
      - On 3.10/3.11, Path.__new__ does ALL real parsing itself (it calls
        cls._from_parts(args) using the RAW, uncoerced args), and
        Path.__init__ is just the inherited object.__init__ -- a no-op that
        does nothing with its args. Patching only __init__ on those versions
        is therefore too late: by the time our patched __init__ runs, the
        real Path has already been built from the raw, unconverted args, so
        a DataResult/OperationResult/__fspath__ object would already have
        blown up inside __new__ before our coercion ever saw it. Confirmed
        directly: object.__new__(...) followed by
        object.__init__(instance, *args) does NOT raise on 3.10/3.11 (the
        "extra args" check is normally skipped by type.__call__ when
        __new__ is overridden) -- but once mock.patch replaces Path.__init__
        with a plain function, that dispatch-level tolerance no longer
        applies, and calling straight through to the real (object.__init__)
        with any positional args raises
        "TypeError: object.__init__() takes exactly one argument" on every
        single Path(...) call in the suite (autouse fixture -> whole-suite
        INTERNALERROR).
      - On 3.12/3.13, Path.__new__ is a trivial object.__new__(cls) and all
        parsing moved into __init__, so patching __init__ alone is
        sufficient there -- but not on 3.10/3.11.
      - CPython's type.__call__ invokes __new__(cls, *args, **kwargs) and
        __init__(self, *args, **kwargs) *independently*, both with the
        original raw args (verified directly) -- __init__ does not see
        whatever __new__ did with its own copy. So the coercion has to be
        applied on entry to BOTH dunders, each calling through to its own
        original with the coerced args, to work uniformly across versions:
        __new__'s coercion is what actually matters on 3.10/3.11 (where the
        real parsing happens there), and __init__'s coercion is what
        actually matters on 3.12/3.13 (where the real parsing happens
        there). Patching only one or the other is what broke on 3.10/3.11.
    """
    # Originals to preserve real behavior
    original_path_new = Path.__new__
    original_path_init = Path.__init__

    def _coerce_path_args(args: tuple[Any, ...]) -> list[Any]:
        """Coerce DataResult/OperationResult/PathLike args to plain strings."""
        new_args = list(args)
        for i, arg in enumerate(new_args):
            if isinstance(arg, (DataResult, OperationResult)) and hasattr(arg, "data"):
                new_args[i] = str(arg.data)
            elif hasattr(arg, "__fspath__"):
                try:
                    new_args[i] = arg.__fspath__()
                except Exception:  # noqa: S110 -- this patched dunder runs on
                    # every Path() construction across the whole test suite; if
                    # __fspath__() fails, leaving the arg unchanged lets the real
                    # Path constructor raise its own natural error below, so
                    # swallowing here (not logging) avoids per-call log noise
                    # for a fallback path that's not itself an error.
                    pass
        return new_args

    def patched_path_new(
        cls: type[Path],
        *args: Any,  # noqa: ANN401 -- genuinely dynamic: monkeypatches Path.__new__ itself, must accept whatever Path's real constructor accepts
        **kwargs: Any,  # noqa: ANN401 -- genuinely dynamic: same as *args above
    ) -> Path:
        new_args = _coerce_path_args(args)
        # Call original __new__ with potentially modified args. This is what
        # does the real work on 3.10/3.11 (Path.__new__ -> _from_parts).
        return original_path_new(cls, *new_args, **kwargs)

    def patched_path_init(
        self: Path,
        *args: Any,  # noqa: ANN401 -- genuinely dynamic: monkeypatches Path.__init__ itself, must accept whatever Path's real constructor accepts
        **kwargs: Any,  # noqa: ANN401 -- genuinely dynamic: same as *args above
    ) -> None:
        if original_path_init is object.__init__:
            # 3.10/3.11: __init__ is a no-op by design (all real work already
            # happened in patched_path_new above, using coerced args). Calling
            # object.__init__(self, *args) directly here -- bypassing
            # type.__call__'s normal "tolerate extra args when __new__ is
            # overridden" dispatch logic -- unconditionally raises TypeError
            # on ANY extra positional args. Skip the passthrough entirely.
            return
        new_args = _coerce_path_args(args)
        # Call original __init__ with potentially modified args. This is what
        # does the real work on 3.12/3.13 (parsing moved here post-rewrite).
        original_path_init(self, *new_args, **kwargs)

    # Patch both Path.__new__ and Path.__init__ to handle DataResult /
    # OperationResult / PathLike args uniformly across Python 3.10-3.13 (see
    # version note in the docstring above for why both are required).
    with (
        patch("pathlib.Path.__new__", patched_path_new),
        patch("pathlib.Path.__init__", patched_path_init),
    ):
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
def sample_config(temp_dir: Path) -> ZeoConfig:
    """Create a sample configuration."""
    # We use string paths instead of Path objects here
    temp_dir_str = str(temp_dir)
    base_dir = temp_dir_str
    output_dir = os.path.join(temp_dir_str, "output")

    # Using strings for paths in the configuration
    return ZeoConfig(
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
    monkeypatch.setenv("ZEO_ENV", "test")
    monkeypatch.setenv("ZEO_GENERAL__DEBUG", "true")
    monkeypatch.setenv("ZEO_LOGGING__LEVEL", "DEBUG")


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


class MockPlugin(ZeoPluginProtocol):
    """Mock plugin for testing."""

    @property
    def plugin_id(self) -> str:
        return "mock_plugin"

    @property
    def name(self) -> str:
        return "mock_plugin"

    def get_metadata(self) -> ZeoPluginMetadata:
        """Get plugin metadata."""
        return ZeoPluginMetadata(
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
