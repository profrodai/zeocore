# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_paths/test_utils.py
# === QV-LLM:END ===

"""
Tests for path utility functions.
"""

import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from quack_core.core.errors import QuackFileNotFoundError
from quack_core.core.fs import DataResult, PathResult
from quack_core.core.fs.service import standalone as fs_standalone
from quack_core.core.paths import service as paths


# Patch necessary fs methods
@pytest.fixture(autouse=True)
def mock_fs_methods(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock join_path to return a real DataResult (ok/path/data - core/fs
    # SERVICE-CONTRACT). A bespoke .success/.data-only stub used to stand in here;
    # it satisfied direct fs_standalone.* callers but broke every paths/_internal
    # caller that reads .ok, e.g. 'PosixPath' object has no attribute 'ok'.
    def mock_join_path(*args: Any) -> DataResult[str]:
        path_str = str(Path(*[str(arg) for arg in args]))
        return DataResult(ok=True, path=Path(path_str), data=path_str, format="path")

    # Mock split_path to return a real DataResult
    def mock_split_path(path: Any) -> DataResult[list[str]]:
        parts = list(Path(path).parts)
        return DataResult(
            ok=True, path=Path(path), data=parts, format="path_components"
        )

    # Mock get_extension to return a real DataResult
    def mock_get_extension(path: Any) -> DataResult[str]:
        suffix = Path(path).suffix
        if suffix.startswith("."):
            suffix = suffix[1:]
        return DataResult(ok=True, path=Path(path), data=suffix, format="extension")

    # Mock normalize_path to return a real PathResult (not a bare Path)
    def mock_normalize(path: Any) -> PathResult:
        # Use Path.resolve() (non-strict), matching the real _resolve_path
        # (core/fs/_internal/path_ops.py) - plain os.path.abspath() does NOT
        # canonicalize symlinks (e.g. macOS /tmp -> /private/tmp), so an absolute
        # root passed in one form and a relative path resolved via os.getcwd() in
        # the other could disagree on a symlinked prefix and silently produce a
        # bogus os.path.relpath (".." walk into /private/..."), even though both
        # names point at the same directory.
        resolved = Path(os.path.join(os.getcwd(), str(path))).resolve()
        return PathResult(
            ok=True,
            path=resolved,
            is_absolute=resolved.is_absolute(),
            is_valid=True,
            exists=resolved.exists(),
        )

    monkeypatch.setattr(fs_standalone, "join_path", mock_join_path)
    monkeypatch.setattr(fs_standalone, "split_path", mock_split_path)
    monkeypatch.setattr(fs_standalone, "get_extension", mock_get_extension)
    monkeypatch.setattr(fs_standalone, "normalize_path", mock_normalize)


class TestPathUtils:
    """Tests for path utility functions."""

    def test_find_project_root(self, mock_project_structure: Path) -> None:
        """Test finding a project root directory."""
        # find_project_root is exposed as PathService.get_project_root (the module
        # never had module-level free functions - see conftest note above).
        service = paths.PathService()
        # mock_normalize (this file's autouse fixture) uses Path.resolve(), matching
        # the real _resolve_path (core/fs/_internal/path_ops.py) - which
        # canonicalizes symlinks (e.g. macOS /var -> /private/var, the tempfile
        # module's own mkdtemp() prefix). Compare against the same canonical form.
        expected_root = str(mock_project_structure.resolve())

        # Test finding from project root
        root_result = service.get_project_root(mock_project_structure)
        assert root_result.success
        assert root_result.path == expected_root

        # Test finding from subdirectory
        subdir = mock_project_structure / "src"
        root_result = service.get_project_root(subdir)
        assert root_result.success
        assert root_result.path == expected_root

        # Test with custom marker files
        root_result = service.get_project_root(
            mock_project_structure, marker_files=["pyproject.toml"]
        )
        assert root_result.success
        assert root_result.path == expected_root

        # Test with custom marker directories
        root_result = service.get_project_root(
            mock_project_structure, marker_dirs=["src", "tests"]
        )
        assert root_result.success
        assert root_result.path == expected_root

        # Test with non-existent path - updated to test for failure result rather than exception
        root_result = service.get_project_root("/nonexistent/path")
        assert not root_result.success
        assert root_result.error is not None

        # Test where no project root can be found - updated to test for failure result
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root_result = service.get_project_root(tmp_path)
            assert not root_result.success
            assert root_result.error is not None

    def test_find_nearest_directory(self, mock_project_structure: Path) -> None:
        """Test finding the nearest directory with a given name."""
        service = paths.PathService()

        # Create a nested directory structure
        nested = mock_project_structure / "src" / "nested" / "deeply" / "structure"
        nested.mkdir(parents=True)

        # Test finding from inside nested structure
        found_result = service.find_nearest_directory("src", nested)
        assert found_result.success
        assert found_result.path == str((mock_project_structure / "src").resolve())

        # Test finding non-existent directory - updated to test for failure result
        result = service.find_nearest_directory("nonexistent", mock_project_structure)
        assert not result.success
        assert result.error is not None

        # Test with max_levels - updated to test for failure result
        result = service.find_nearest_directory("src", nested, max_levels=2)
        assert not result.success
        assert result.error is not None

    def test_resolve_relative_to_project(self, mock_project_structure: Path) -> None:
        """Test resolving a path relative to the project root."""
        service = paths.PathService()

        # Test resolving a relative path
        resolved_result = service.resolve_relative_to_project(
            "src/file.txt", mock_project_structure
        )
        assert resolved_result.success
        assert resolved_result.path == str(mock_project_structure / "src" / "file.txt")

        # Test resolving an absolute path (should remain unchanged)
        abs_path = Path("/absolute/path/file.txt")
        resolved_result = service.resolve_relative_to_project(
            abs_path, mock_project_structure
        )
        assert resolved_result.success
        assert resolved_result.path == str(abs_path)

        # Test resolving without explicit project root
        with patch(
            "quack_core.core.paths._internal.utils._find_project_root",
            return_value=str(mock_project_structure),
        ):
            resolved_result = service.resolve_relative_to_project("src/file.txt")
            assert resolved_result.success
            assert resolved_result.path == str(
                mock_project_structure / "src" / "file.txt"
            )

        # Test when project root cannot be found: the current implementation does
        # not silently fall back to cwd - _find_project_root's QuackFileNotFoundError
        # propagates and the service returns a failed PathResult (operations never
        # raise past the service boundary; they report via the Result contract).
        with patch(
            "quack_core.core.paths._internal.utils._find_project_root",
            side_effect=QuackFileNotFoundError(""),
        ):
            resolved_result = service.resolve_relative_to_project("file.txt")
            assert not resolved_result.success
            assert resolved_result.error is not None

    def test_normalize_path(self) -> None:
        """Test normalizing paths."""
        # Mock the normalize_path method to avoid filesystem access
        with patch(
            "quack_core.core.fs.service.standalone.normalize_path"
        ) as mock_normalize:
            # Set up the mock to return a Path object with an absolute path
            mock_normalize.return_value = Path("/absolute/path/file.txt")

            # Test relative path normalization
            normalized = fs_standalone.normalize_path("./test/../file.txt")
            assert normalized.is_absolute
            mock_normalize.assert_called_once_with("./test/../file.txt")

        # Test with empty path
        with patch(
            "quack_core.core.fs.service.standalone.normalize_path"
        ) as mock_normalize:
            mock_normalize.return_value = Path("/current/working/directory")

            normalized = fs_standalone.normalize_path("")
            assert normalized.is_absolute
            mock_normalize.assert_called_once_with("")

        # Test with absolute path
        with patch(
            "quack_core.core.fs.service.standalone.normalize_path"
        ) as mock_normalize:
            mock_normalize.return_value = Path("/some/absolute/path")

            normalized = fs_standalone.normalize_path("/some/absolute/path")
            assert normalized.is_absolute
            mock_normalize.assert_called_once_with("/some/absolute/path")

    def test_join_path(self, mock_fs_methods: None) -> None:
        """Test joining path components."""
        # Test with string paths
        joined = fs_standalone.join_path("dir1", "dir2", "file.txt")
        assert joined.success
        assert joined.data == str(Path("dir1/dir2/file.txt"))

        # Test with Path objects
        joined = fs_standalone.join_path(Path("/dir1"), Path("dir2"), "file.txt")
        assert joined.success
        assert joined.data == str(Path("/dir1/dir2/file.txt"))

        # Test with mixed types
        joined = fs_standalone.join_path("/dir1", Path("dir2/dir3"), "file.txt")
        assert joined.success
        assert joined.data == str(Path("/dir1/dir2/dir3/file.txt"))

    def test_split_path(self, mock_fs_methods: None) -> None:
        """Test splitting a path into components."""
        # Test absolute path
        parts_result = fs_standalone.split_path("/dir1/dir2/file.txt")
        assert parts_result.success
        parts = parts_result.data
        assert parts[0] == "/"
        assert "dir1" in parts
        assert "dir2" in parts
        assert parts[-1] == "file.txt"

        # Test relative path
        parts_result = fs_standalone.split_path("dir1/dir2/file.txt")
        assert parts_result.success
        parts = parts_result.data
        assert parts[0] == "dir1"
        assert parts[1] == "dir2"
        assert parts[2] == "file.txt"

        # Test dot path
        parts_result = fs_standalone.split_path("./dir/file.txt")
        assert parts_result.success
        parts = parts_result.data
        # Update the test to reflect how Path handles normalization of "./dir/file.txt"
        assert parts[0] == "dir"  # Path normalization removes the './'
        assert parts[1] == "file.txt"

    def test_get_extension(self, mock_fs_methods: None) -> None:
        """Test getting file extensions."""
        assert fs_standalone.get_extension("file.txt").data == "txt"
        assert fs_standalone.get_extension("file.tar.gz").data == "gz"
        assert fs_standalone.get_extension("file").data == ""
        assert fs_standalone.get_extension(Path("/path/to/file.png")).data == "png"

        # Special case for dot files (implementation may vary)
        ext_result = fs_standalone.get_extension(".hidden")
        assert ext_result.success
        # Either it treats it as a file with no extension, or extracts "hidden"

    def test_infer_module_from_path(
        self, mock_project_structure: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test inferring a Python module name from a file path."""
        # infer_module_from_path is exposed as PathService.infer_module_from_path,
        # returning a StringResult (.value, not .path - see api/public/results.py).
        service = paths.PathService()

        # Create a module structure
        module_dir = mock_project_structure / "src" / "test_module"
        sub_module = module_dir / "submodule"
        sub_module.mkdir(parents=True, exist_ok=True)
        module_file = sub_module / "test_file.py"
        module_file.touch()

        # Test inferring from a file within src directory
        module_name_result = service.infer_module_from_path(
            module_file, mock_project_structure
        )
        assert module_name_result.success
        assert module_name_result.value == "test_module.submodule.test_file"

        # Test inferring from a file with a relative path. A bare relative string
        # is resolved via os.path.abspath, which anchors to the process CWD - so
        # for this case to genuinely resolve against mock_project_structure (rather
        # than the repo worktree CWD, which was the latent bug here previously),
        # the CWD must actually be mock_project_structure for the call.
        with patch(
            "quack_core.core.paths._internal.utils._find_project_root",
            return_value=str(mock_project_structure),
        ):
            monkeypatch.chdir(mock_project_structure)
            module_name_result = service.infer_module_from_path(
                "src/test_module/submodule/test_file.py"
            )
            assert module_name_result.success
            assert module_name_result.value == "test_module.submodule.test_file"

        # Test inferring when src directory cannot be found
        with patch(
            "quack_core.core.paths._internal.utils._find_nearest_directory",
            side_effect=QuackFileNotFoundError(""),
        ):
            # Should use file's directory as fallback
            module_name_result = service.infer_module_from_path(
                module_file, mock_project_structure
            )
            assert module_name_result.success
            assert "test_file" in module_name_result.value

        # Test inferring when file is not in project: like
        # resolve_relative_to_project above, _find_project_root's
        # QuackFileNotFoundError is not caught inside _infer_module_from_path - it
        # propagates and the service reports a failed StringResult rather than
        # silently falling back to a bare filename.
        with patch(
            "quack_core.core.paths._internal.utils._find_project_root",
            side_effect=QuackFileNotFoundError(""),
        ):
            module_name_result = service.infer_module_from_path(
                "/outside/project/file.py"
            )
            assert not module_name_result.success
            assert module_name_result.error is not None
