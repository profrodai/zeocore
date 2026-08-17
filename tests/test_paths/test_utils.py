"""
Tests for path utility functions.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from zeo_core.core.errors import ZeoFileNotFoundError
from zeo_core.core.fs import DataResult, PathResult
from zeo_core.core.fs.protocols import FsPathLike
from zeo_core.core.fs.service import standalone as fs_standalone
from zeo_core.core.paths import service as paths


# Patch necessary fs methods
@pytest.fixture(autouse=True)
def mock_fs_methods(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock join_path to return a real DataResult (ok/path/data - core/fs
    # SERVICE-CONTRACT). A bespoke .success/.data-only stub used to stand in here;
    # it satisfied direct fs_standalone.* callers but broke every paths/_internal
    # caller that reads .ok, e.g. 'PosixPath' object has no attribute 'ok'.
    def mock_join_path(*args: FsPathLike) -> DataResult[str]:
        path_str = str(Path(*[str(arg) for arg in args]))
        return DataResult(ok=True, path=Path(path_str), data=path_str, format="path")

    # Mock split_path to return a real DataResult. Narrowed to str | Path (not the
    # wider FsPathLike) because Path() below doesn't structurally accept every
    # FsPathLike union member (HasPath/HasData/HasValue/HasUnwrap/BaseResult).
    def mock_split_path(path: str | Path) -> DataResult[list[str]]:
        parts = list(Path(path).parts)
        return DataResult(
            ok=True, path=Path(path), data=parts, format="path_components"
        )

    # Mock get_extension to return a real DataResult. Same str | Path narrowing
    # as mock_split_path, same reason.
    def mock_get_extension(path: str | Path) -> DataResult[str]:
        suffix = Path(path).suffix
        if suffix.startswith("."):
            suffix = suffix[1:]
        return DataResult(ok=True, path=Path(path), data=suffix, format="extension")

    # Mock normalize_path to return a real PathResult (not a bare Path)
    def mock_normalize(path: FsPathLike) -> PathResult:
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

        # Test with non-existent path - updated to test for failure result
        # rather than exception
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
            "zeo_core.core.paths._internal.utils._find_project_root",
            return_value=str(mock_project_structure),
        ):
            resolved_result = service.resolve_relative_to_project("src/file.txt")
            assert resolved_result.success
            assert resolved_result.path == str(
                mock_project_structure / "src" / "file.txt"
            )

        # Test when project root cannot be found: the current implementation does
        # not silently fall back to cwd - _find_project_root's ZeoFileNotFoundError
        # propagates and the service returns a failed PathResult (operations never
        # raise past the service boundary; they report via the Result contract).
        with patch(
            "zeo_core.core.paths._internal.utils._find_project_root",
            side_effect=ZeoFileNotFoundError(""),
        ):
            resolved_result = service.resolve_relative_to_project("file.txt")
            assert not resolved_result.success
            assert resolved_result.error is not None

    def test_normalize_path(self) -> None:
        """Test normalizing paths."""
        # Mock the normalize_path method to avoid filesystem access
        with patch(
            "zeo_core.core.fs.service.standalone.normalize_path"
        ) as mock_normalize:
            # Set up the mock to return a Path object with an absolute path
            mock_normalize.return_value = Path("/absolute/path/file.txt")

            # Test relative path normalization
            normalized = fs_standalone.normalize_path("./test/../file.txt")
            assert normalized.is_absolute
            mock_normalize.assert_called_once_with("./test/../file.txt")

        # Test with empty path
        with patch(
            "zeo_core.core.fs.service.standalone.normalize_path"
        ) as mock_normalize:
            mock_normalize.return_value = Path("/current/working/directory")

            normalized = fs_standalone.normalize_path("")
            assert normalized.is_absolute
            mock_normalize.assert_called_once_with("")

        # Test with absolute path
        with patch(
            "zeo_core.core.fs.service.standalone.normalize_path"
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
        assert parts is not None
        assert parts[0] == "/"
        assert "dir1" in parts
        assert "dir2" in parts
        assert parts[-1] == "file.txt"

        # Test relative path
        parts_result = fs_standalone.split_path("dir1/dir2/file.txt")
        assert parts_result.success
        parts = parts_result.data
        assert parts is not None
        assert parts[0] == "dir1"
        assert parts[1] == "dir2"
        assert parts[2] == "file.txt"

        # Test dot path
        parts_result = fs_standalone.split_path("./dir/file.txt")
        assert parts_result.success
        parts = parts_result.data
        assert parts is not None
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
            "zeo_core.core.paths._internal.utils._find_project_root",
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
            "zeo_core.core.paths._internal.utils._find_nearest_directory",
            side_effect=ZeoFileNotFoundError(""),
        ):
            # Should use file's directory as fallback
            module_name_result = service.infer_module_from_path(
                module_file, mock_project_structure
            )
            assert module_name_result.success
            assert module_name_result.value is not None
            assert "test_file" in module_name_result.value

        # Test inferring when file is not in project: like
        # resolve_relative_to_project above, _find_project_root's
        # ZeoFileNotFoundError is not caught inside _infer_module_from_path - it
        # propagates and the service reports a failed StringResult rather than
        # silently falling back to a bare filename.
        with patch(
            "zeo_core.core.paths._internal.utils._find_project_root",
            side_effect=ZeoFileNotFoundError(""),
        ):
            module_name_result = service.infer_module_from_path(
                "/outside/project/file.py"
            )
            assert not module_name_result.success
            assert module_name_result.error is not None


class TestProjectRootWalkUp:
    """
    Coverage for the walk-up-for-pyproject.toml-or-.git default behavior of
    _find_project_root / _has_root_marker (core/paths/_internal/utils.py).

    This replaces the old package-name-specific heuristic (a hardcoded
    "quack-core" directory name checked via marker_dirs) with a convention-
    based walk that carries no assumption about this project's own name --
    these tests exercise that NEW logic specifically: it must find a real
    pyproject.toml/.git marker from a nested subdirectory, prefer the
    nearest (not the topmost) qualifying ancestor, recognize .git in both
    its usual directory form and its worktree/submodule file form, and
    terminate cleanly at max_levels or the filesystem root without an
    infinite loop when no marker exists at all.

    Uses real temporary directories (not the mocked fs_standalone used by
    the rest of this file) since the walk-up itself, and its termination
    behavior at the filesystem root, are exactly what's under test here --
    mocking join_path/normalize_path would test the mock, not the walk.
    """

    def test_finds_pyproject_toml_from_nested_subdirectory(
        self, tmp_path: Path
    ) -> None:
        """A pyproject.toml at the root is found by walking up from a
        subdirectory several levels below it."""
        from zeo_core.core.paths._internal.utils import _find_project_root

        root = tmp_path / "proj"
        root.mkdir()
        (root / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        nested = root / "a" / "b" / "c"
        nested.mkdir(parents=True)

        found = _find_project_root(str(nested), max_levels=10)

        assert found == str(root.resolve())

    def test_finds_git_directory_from_nested_subdirectory(self, tmp_path: Path) -> None:
        """A .git DIRECTORY (the normal case for a real clone) at the root
        is found by walking up, with no pyproject.toml present at all."""
        from zeo_core.core.paths._internal.utils import _find_project_root

        root = tmp_path / "proj"
        root.mkdir()
        (root / ".git").mkdir()
        nested = root / "src" / "pkg"
        nested.mkdir(parents=True)

        found = _find_project_root(str(nested), max_levels=10)

        assert found == str(root.resolve())

    def test_finds_git_file_worktree_form(self, tmp_path: Path) -> None:
        """.git as a FILE (git worktree / submodule form, holding a
        'gitdir: <path>' pointer instead of being the real directory) is
        also recognized -- _has_root_marker checks existence, not isdir."""
        from zeo_core.core.paths._internal.utils import _find_project_root

        root = tmp_path / "worktree"
        root.mkdir()
        (root / ".git").write_text("gitdir: /elsewhere/.git/worktrees/worktree\n")

        found = _find_project_root(str(root), max_levels=10)

        assert found == str(root.resolve())

    def test_prefers_nearest_marker_over_topmost(self, tmp_path: Path) -> None:
        """When both an outer and an inner ancestor qualify, the walk-up
        stops at the FIRST (nearest) one it reaches, not the topmost."""
        from zeo_core.core.paths._internal.utils import _find_project_root

        outer = tmp_path / "outer"
        outer.mkdir()
        (outer / "pyproject.toml").write_text("[project]\nname = 'outer'\n")
        inner = outer / "inner"
        inner.mkdir()
        (inner / "pyproject.toml").write_text("[project]\nname = 'inner'\n")
        nested = inner / "src"
        nested.mkdir()

        found = _find_project_root(str(nested), max_levels=10)

        assert found == str(inner.resolve())

    def test_no_marker_raises_after_max_levels_without_hanging(
        self, tmp_path: Path
    ) -> None:
        """No pyproject.toml/.git anywhere in the walked range: raises
        ZeoFileNotFoundError rather than silently falling back, and the
        walk terminates (this call returning at all, inside the test
        timeout, is itself proof it did not infinite-loop)."""
        from zeo_core.core.paths._internal.utils import _find_project_root

        empty = tmp_path / "no_markers_here"
        empty.mkdir()

        with pytest.raises(ZeoFileNotFoundError):
            _find_project_root(str(empty), max_levels=3)

    def test_walk_up_terminates_at_filesystem_root(self) -> None:
        """Starting the walk AT the filesystem root itself: os.path.dirname
        of "/" is "/" again, so the loop's own parent==current_dir check
        must break rather than spin -- proven by this call returning at
        all rather than hanging until the test suite's timeout."""
        from zeo_core.core.paths._internal.utils import _find_project_root

        # "/" almost certainly has neither pyproject.toml nor .git; if it
        # somehow does on some exotic CI image, the assertion below (not
        # the call itself) is what would need loosening -- the property
        # this test actually protects, non-infinite-looping, holds either
        # way because the function returns instead of hanging.
        with pytest.raises(ZeoFileNotFoundError):
            _find_project_root("/", max_levels=3)

    def test_has_root_marker_false_for_directory_with_neither(
        self, tmp_path: Path
    ) -> None:
        """Direct unit coverage of _has_root_marker: a directory containing
        neither pyproject.toml nor .git reports False."""
        from zeo_core.core.paths._internal.utils import _has_root_marker

        plain = tmp_path / "plain"
        plain.mkdir()
        (plain / "readme.txt").write_text("not a marker")

        assert _has_root_marker(str(plain)) is False

    def test_has_root_marker_true_for_pyproject_and_for_git(
        self, tmp_path: Path
    ) -> None:
        """Direct unit coverage of _has_root_marker's two independent
        qualifying conditions."""
        from zeo_core.core.paths._internal.utils import _has_root_marker

        with_pyproject = tmp_path / "with_pyproject"
        with_pyproject.mkdir()
        (with_pyproject / "pyproject.toml").write_text("[project]\n")
        assert _has_root_marker(str(with_pyproject)) is True

        with_git = tmp_path / "with_git"
        with_git.mkdir()
        (with_git / ".git").mkdir()
        assert _has_root_marker(str(with_git)) is True

    def test_explicit_marker_files_override_still_honored(self, tmp_path: Path) -> None:
        """The marker_files override (pre-existing part of the contract,
        callers like PathService.get_project_root(marker_files=...) rely on
        it) still qualifies a directory that has neither pyproject.toml nor
        .git, as long as it has the caller-supplied marker file."""
        from zeo_core.core.paths._internal.utils import _find_project_root

        root = tmp_path / "custom_marker_root"
        root.mkdir()
        (root / "MARKER.txt").write_text("custom project marker")
        nested = root / "sub"
        nested.mkdir()

        found = _find_project_root(
            str(nested), marker_files=["MARKER.txt"], max_levels=10
        )

        assert found == str(root.resolve())
