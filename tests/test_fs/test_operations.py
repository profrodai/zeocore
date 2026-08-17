"""
Tests for the FileSystemOperations class.

Note: These tests have been updated to reflect the internal refactoring
where _ops return raw types instead of result objects.

NOTE (fs-internals-fix, 2026-08-15): a second round of updates, on top of
the note above. `FileSystemOperations` now lives at
`quack_core.core.fs._ops.base` (composed from mixins in `_ops/*.py`), not
`quack_core.core.fs._operations` -- that module name does not exist
anywhere in this repo's tracked history (confirmed: `git log --oneline --all`
on the literal path returns nothing). Reading `_ops/base.py` in full:
`FileSystemOperations.__init__` takes NO arguments at all (no `base_dir`)
and every method takes an absolute/already-resolved `Path` directly --
there is no relative-path-to-base_dir joining or sandboxing at this layer
anymore. That whole concern (base_dir anchoring, sandbox escape checks,
`FsPathLike` coercion) moved up to `quack_core.core.fs.service.
_BaseFileSystemService`, confirmed by reading `service/base.py` in full
(`self.operations = FileSystemOperations()` -- zero-arg construction; base_dir
lives on the SERVICE, not the ops class). This is a genuine architectural
move, not a rename: `_ops.FileSystemOperations` is now a raw, unconfigured
operation surface; `service.FileSystemService`/`_BaseFileSystemService` is
the only base_dir-aware, sandboxed adapter (Vision-Invariants Brief
directionality, CLAUDE.md s11: _internal raises bare -> _ops raises ->
service is the only adapter).

Disposition, file-wide: REWORK, not DELETE. Every method
`test_initialize`/`test_resolve_path` exercised through base_dir-relative
calls (`operations._read_text("text_test.txt")` resolving against
`base_dir`) still has a live, behaviorally-equivalent counterpart on
`FileSystemOperations` -- it just now takes the already-resolved absolute
`Path` directly (`operations._read_text(temp_dir / "text_test.txt")`).
`test_initialize` and the base_dir-joining half of `test_resolve_path` test
a concept (base_dir-anchored construction) that no longer exists on this
class at all -- that coverage is retargeted at `_ops.path_ops.
PathOperationsMixin._resolve_path`, the real current method with that name
(a thin `Path.resolve()` wrapper, no base_dir), which the original file
never actually exercised despite the method existing.

`patch()` targets are also corrected: the original file patched
`"quack_core.core.fs._ops._ensure_directory"` and
`"quack_core.core.fs._ops._atomic_write"` -- but `_ops/__init__.py` only
ever imports and re-exports `FileSystemOperations` (confirmed by reading it
in full); `_ensure_directory`/`_atomic_write` are imported into
`_ops.directory_ops`/`_ops.write_ops` from `_internal.*`, never into the
`_ops` package namespace itself, so the original patch targets never
actually intercepted the real call in production code (grep confirms
`_ops/__init__.py` has always had exactly one import line). Patches below
target the real call sites.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from quack_core.core.errors import QuackIOError
from quack_core.core.fs._ops.base import FileSystemOperations


class TestFileSystemOperations:
    """Tests for the FileSystemOperations class."""

    def test_initialize(self) -> None:
        """Test that FileSystemOperations constructs with no arguments.

        NOTE (fs-internals-fix): `base_dir`-anchored construction is GONE
        from this class (confirmed: `__init__(self) -> None`, zero
        parameters, reading `_ops/base.py` in full). That concept now lives
        entirely on `service._BaseFileSystemService.__init__(base_dir=...)`.
        This subtest is retargeted at what the class actually does on
        construction: initialize mimetypes and come up with every mixin's
        methods present, nothing more.
        """
        operations = FileSystemOperations()
        assert operations is not None
        # Confirm the composed mixin surface is present (existence check,
        # not a base_dir concept this class no longer has).
        assert hasattr(operations, "_read_text")
        assert hasattr(operations, "_write_text")
        assert hasattr(operations, "_resolve_path")

    def test_resolve_path(self) -> None:
        """Test resolving paths via the actual current `_resolve_path`
        (a thin `Path.resolve()` wrapper on `PathOperationsMixin`, no
        base_dir joining -- see the file-level NOTE for why the old
        base_dir-relative version of this test no longer applies)."""
        operations = FileSystemOperations()

        # Relative path: absolutized and .. collapsed by resolve()
        rel_path = Path("subdir/file.txt")
        resolved = operations._resolve_path(rel_path)
        assert resolved.is_absolute()
        assert resolved.name == "file.txt"

        # Absolute path: passed through resolve() (may normalize symlinks,
        # but the name/absoluteness invariants hold)
        abs_path = Path("/absolute/path/file.txt")
        resolved = operations._resolve_path(abs_path)
        assert resolved.is_absolute()
        assert resolved.name == "file.txt"

    def test_read_text(self, temp_dir: Path) -> None:
        """Test reading text from a file."""
        operations = FileSystemOperations()

        # Create a test file
        file_path = temp_dir / "text_test.txt"
        file_path.write_text("test content")

        # Test successful read - returns string directly
        result = operations._read_text(file_path)
        assert isinstance(result, str)
        assert result == "test content"

        # Test custom encoding
        utf16_file = temp_dir / "utf16_test.txt"
        utf16_file.write_text("тест текст", encoding="utf-16")
        result = operations._read_text(utf16_file, encoding="utf-16")
        assert isinstance(result, str)
        assert result == "тест текст"

        # Test reading non-existent file - raises FileNotFoundError
        with pytest.raises(FileNotFoundError):
            operations._read_text(temp_dir / "nonexistent.txt")

    def test_read_binary(self, temp_dir: Path) -> None:
        """Test reading binary data from a file."""
        operations = FileSystemOperations()

        # Create a test binary file
        file_path = temp_dir / "binary_test.bin"
        file_path.write_bytes(b"\x00\x01\x02\x03")

        # Test successful read - returns bytes directly
        result = operations._read_binary(file_path)
        assert isinstance(result, bytes)
        assert result == b"\x00\x01\x02\x03"

        # Test reading non-existent file - raises FileNotFoundError
        with pytest.raises(FileNotFoundError):
            operations._read_binary(temp_dir / "nonexistent.bin")

    def test_write_text(self, temp_dir: Path) -> None:
        """Test writing text to a file."""
        operations = FileSystemOperations()

        # Test writing to a new file - returns Path
        result = operations._write_text(temp_dir / "write_test.txt", "test content")
        assert isinstance(result, Path)
        assert (temp_dir / "write_test.txt").read_text() == "test content"

        # Test writing with custom encoding
        result = operations._write_text(
            temp_dir / "encoding_test.txt", "тест", encoding="utf-16"
        )
        assert isinstance(result, Path)
        assert (temp_dir / "encoding_test.txt").read_text(encoding="utf-16") == "тест"

        # Test with atomic=False
        result = operations._write_text(
            temp_dir / "nonatomic.txt", "content", atomic=False
        )
        assert isinstance(result, Path)
        assert (temp_dir / "nonatomic.txt").read_text() == "content"

    def test_write_binary(self, temp_dir: Path) -> None:
        """Test writing binary data to a file."""
        operations = FileSystemOperations()

        # Test writing to a new file - returns Path
        result = operations._write_binary(temp_dir / "binary.bin", b"\x00\x01\x02\x03")
        assert isinstance(result, Path)
        assert (temp_dir / "binary.bin").read_bytes() == b"\x00\x01\x02\x03"

        # Test with atomic=False
        result = operations._write_binary(
            temp_dir / "nonatomic.bin", b"\x04\x05\x06\x07", atomic=False
        )
        assert isinstance(result, Path)
        assert (temp_dir / "nonatomic.bin").read_bytes() == b"\x04\x05\x06\x07"

    def test_copy(self, temp_dir: Path) -> None:
        """Test copying a file."""
        operations = FileSystemOperations()

        # Create a source file
        source_path = temp_dir / "source.txt"
        source_path.write_text("source content")
        dest_path = temp_dir / "dest.txt"

        # Test successful copy - returns Path to destination
        result = operations._copy(source_path, dest_path)
        assert isinstance(result, Path)
        assert dest_path.exists()
        assert dest_path.read_text() == "source content"

        # Test copy to existing file (should fail) - bare FileExistsError
        with pytest.raises(FileExistsError):
            operations._copy(source_path, dest_path)

        # Test copy with overwrite
        result = operations._copy(source_path, dest_path, overwrite=True)
        assert isinstance(result, Path)

        # Test copy with non-existent source - bare FileNotFoundError
        with pytest.raises(FileNotFoundError):
            operations._copy(temp_dir / "nonexistent.txt", temp_dir / "new_dest.txt")

    def test_move(self, temp_dir: Path) -> None:
        """Test moving a file."""
        operations = FileSystemOperations()

        # Create a source file
        source_path = temp_dir / "move_source.txt"
        source_path.write_text("move content")
        dest_path = temp_dir / "move_dest.txt"

        # Test successful move - returns Path to destination
        result = operations._move(source_path, dest_path)
        assert isinstance(result, Path)
        assert dest_path.exists()
        assert not source_path.exists()
        assert dest_path.read_text() == "move content"

        # Create new source file
        source_path.write_text("new move content")

        # Test move to existing file (should fail) - bare FileExistsError
        with pytest.raises(FileExistsError):
            operations._move(source_path, dest_path)

        # Test move with overwrite
        result = operations._move(source_path, dest_path, overwrite=True)
        assert isinstance(result, Path)
        assert dest_path.read_text() == "new move content"

        # Test move with non-existent source - bare FileNotFoundError
        with pytest.raises(FileNotFoundError):
            operations._move(temp_dir / "nonexistent.txt", temp_dir / "new_dest.txt")

    def test_delete(self, temp_dir: Path) -> None:
        """Test deleting a file."""
        operations = FileSystemOperations()

        # Create a file to delete
        file_path = temp_dir / "to_delete.txt"
        file_path.write_text("delete me")

        # Test successful delete - returns bool
        result = operations._delete(file_path)
        assert result is True
        assert not file_path.exists()

        # Test deleting non-existent file (should succeed with missing_ok=True,
        # the default)
        result = operations._delete(file_path)
        assert result is False

        # Test deleting non-existent file with missing_ok=False - bare
        # FileNotFoundError
        with pytest.raises(FileNotFoundError):
            operations._delete(file_path, missing_ok=False)

    def test_create_directory(self, temp_dir: Path) -> None:
        """Test creating a directory.

        NOTE (fs-internals-fix): the method is `_ensure_directory`, not
        `_create_directory` -- `FileSystemOperations` has no method named
        `_create_directory` at all (confirmed by reading `DirectoryOperationsMixin`
        and `UtilityOperationsMixin`, both of which define `_ensure_directory`
        identically). The mock patch target is corrected to the real call
        site (`_internal.directory_ops._ensure_directory`, imported into
        `_ops.directory_ops`), not the non-existent `quack_core.core.fs._ops.
        _ensure_directory` package-level name (see file-level NOTE on patch
        targets).
        """
        operations = FileSystemOperations()

        # Test creating directory - returns Path
        result = operations._ensure_directory(temp_dir / "new_dir")
        assert isinstance(result, Path)
        assert (temp_dir / "new_dir").is_dir()

        # Test creating existing directory (should succeed with exist_ok=True,
        # the default)
        result = operations._ensure_directory(temp_dir / "new_dir")
        assert isinstance(result, Path)

        # Test creating existing directory with exist_ok=False - bare
        # FileExistsError, raised for real (no mock needed, the directory
        # already exists from above)
        with pytest.raises(FileExistsError) as excinfo:
            operations._ensure_directory(temp_dir / "new_dir", exist_ok=False)
        assert "already exists" in str(excinfo.value).lower()

    def test_get_file_info(self, temp_dir: Path) -> None:
        """Test getting file information."""
        operations = FileSystemOperations()

        # Create a test file
        file_path = temp_dir / "info_test.txt"
        file_path.write_text("info content")

        # Create a test directory
        dir_path = temp_dir / "info_dir"
        dir_path.mkdir()

        # Test getting info for a file - returns the internal _FileInfo DTO
        result = operations._get_file_info(file_path)
        assert result.exists is True
        assert result.is_file is True
        assert result.is_dir is False
        assert result.size > 0
        assert result.modified is not None

        # Test getting info for a directory
        result = operations._get_file_info(dir_path)
        assert result.exists is True
        assert result.is_file is False
        assert result.is_dir is True

        # Test getting info for a non-existent file
        result = operations._get_file_info(temp_dir / "nonexistent.txt")
        assert result.exists is False

    def test_list_directory(self, temp_dir: Path) -> None:
        """Test listing directory contents."""
        operations = FileSystemOperations()

        # Create some files and directories for testing
        (temp_dir / "list_file1.txt").write_text("content1")
        (temp_dir / "list_file2.txt").write_text("content2")
        (temp_dir / ".hidden_file").write_text("hidden")
        (temp_dir / "list_dir").mkdir()

        # Test listing with default parameters - returns _DirectoryInfo DTO
        result = operations._list_directory(temp_dir)
        assert hasattr(result, "files")
        assert hasattr(result, "directories")
        assert hasattr(result, "is_empty")
        assert result.is_empty is False
        assert len(result.files) >= 2  # At least our created files
        assert len(result.directories) >= 1  # At least our created directory
        assert any(f.name == "list_file1.txt" for f in result.files)
        assert any(f.name == "list_file2.txt" for f in result.files)
        assert any(d.name == "list_dir" for d in result.directories)

        # Test listing with include_hidden=True
        result = operations._list_directory(temp_dir, include_hidden=True)
        assert any(f.name == ".hidden_file" for f in result.files)

        # Test listing with pattern
        result = operations._list_directory(temp_dir, pattern="list_*.txt")
        assert len(result.files) == 2
        assert all(f.name.startswith("list_") for f in result.files)

        # Test listing non-existent directory - FileNotFoundError
        with pytest.raises(FileNotFoundError) as excinfo:
            operations._list_directory(temp_dir / "nonexistent_dir")
        assert "not found" in str(excinfo.value).lower()

    def test_find_files(self, temp_dir: Path) -> None:
        """Test finding files matching a pattern."""
        operations = FileSystemOperations()

        # Create some files and directories for testing
        (temp_dir / "find_file1.txt").write_text("content1")
        (temp_dir / "find_file2.txt").write_text("content2")
        (temp_dir / "find_doc.pdf").write_text("pdf content")
        (temp_dir / "find_dir").mkdir()
        (temp_dir / "find_dir" / "subfile.txt").write_text("sub content")

        # Test finding with pattern: matches all files containing "file"
        # Returns tuple of (files, directories)
        result = operations._find_files(temp_dir, "*file*.txt")
        files, directories = result
        assert len(files) == 3  # find_file1.txt, find_file2.txt, and subfile.txt
        assert any(f.name == "find_file1.txt" for f in files)
        assert any(f.name == "find_file2.txt" for f in files)
        assert any(f.name == "subfile.txt" for f in files)

        # Test finding without recursion
        result = operations._find_files(temp_dir, "find_*.txt", recursive=False)
        files, directories = result
        assert len(files) == 2
        assert not any(f.name == "subfile.txt" for f in files)

        # Test finding directories
        result = operations._find_files(temp_dir, "*dir*")
        files, directories = result
        assert len(directories) >= 1
        assert any(d.name == "find_dir" for d in directories)

        # Test finding with non-existent directory - NotADirectoryError
        # (the current implementation, read in full, raises this for BOTH
        # "does not exist" and "not a directory" via one check:
        # `if not path.exists() or not path.is_dir(): raise
        # NotADirectoryError(...)`)
        with pytest.raises(NotADirectoryError) as excinfo:
            operations._find_files(temp_dir / "nonexistent_dir", "*")
        assert "invalid search directory" in str(excinfo.value).lower()

    def test_read_yaml(self, temp_dir: Path) -> None:
        """Test reading YAML files."""
        operations = FileSystemOperations()

        # Create a YAML file
        data = {"name": "Test", "values": [1, 2, 3], "nested": {"key": "value"}}
        yaml_file = temp_dir / "test.yaml"
        yaml_file.write_text(yaml.dump(data))

        # Test successful read - returns dict directly
        result = operations._read_yaml(yaml_file)
        assert isinstance(result, dict)
        assert result == data

        # Test empty YAML file (should return empty dict)
        empty_yaml = temp_dir / "empty.yaml"
        empty_yaml.write_text("")
        result = operations._read_yaml(empty_yaml)
        assert isinstance(result, dict)
        assert result == {}

        # Test reading invalid YAML - bare yaml.YAMLError (subclasses Exception,
        # not QuackIOError -- _ops/serialization_ops.py has no try/except at
        # all, it lets yaml.safe_load's own error propagate)
        invalid_yaml = temp_dir / "invalid.yaml"
        invalid_yaml.write_text("name: Test\ninvalid: : value")
        with pytest.raises(yaml.YAMLError):
            operations._read_yaml(invalid_yaml)

        # Test non-dictionary YAML - bare ValueError
        list_yaml = temp_dir / "list.yaml"
        list_yaml.write_text("- item1\n- item2")
        with pytest.raises(ValueError) as excinfo:
            operations._read_yaml(list_yaml)
        assert "not a dict" in str(excinfo.value).lower()

        # Test reading non-existent file - bare FileNotFoundError
        with pytest.raises(FileNotFoundError):
            operations._read_yaml(temp_dir / "nonexistent.yaml")

    def test_write_yaml(self, temp_dir: Path) -> None:
        """Test writing YAML files."""
        operations = FileSystemOperations()

        # Test writing data - returns Path
        data = {"name": "Test", "values": [1, 2, 3], "nested": {"key": "value"}}
        write_path = temp_dir / "write.yaml"
        result = operations._write_yaml(write_path, data)
        assert isinstance(result, Path)

        # Verify the written data
        read_result = operations._read_yaml(write_path)
        assert read_result == data

        # Test writing with non-serializable data - bare yaml.YAMLError
        # propagates (no try/except wrapping at this layer)
        with patch("yaml.safe_dump") as mock_dump:
            mock_dump.side_effect = yaml.YAMLError("YAML error")
            with pytest.raises(yaml.YAMLError):
                operations._write_yaml(temp_dir / "error.yaml", {"error": object()})

    def test_read_json(self, temp_dir: Path) -> None:
        """Test reading JSON files."""
        operations = FileSystemOperations()

        # Create a JSON file
        data = {"name": "Test", "values": [1, 2, 3], "nested": {"key": "value"}}
        json_file = temp_dir / "test.json"
        json_file.write_text(json.dumps(data))

        # Test successful read - returns dict directly
        result = operations._read_json(json_file)
        assert isinstance(result, dict)
        assert result == data

        # Test reading invalid JSON - bare json.JSONDecodeError (a ValueError
        # subclass; no try/except wrapping at this layer)
        invalid_json = temp_dir / "invalid.json"
        invalid_json.write_text('{"name": "Test", "invalid": }')
        with pytest.raises(json.JSONDecodeError):
            operations._read_json(invalid_json)

        # Test non-dictionary JSON - bare ValueError. NOTE (fs-internals-fix):
        # the current message reads "JSON content is not a dict: ..."
        # (read in full in _ops/serialization_ops.py), not the old "not an
        # object" wording.
        list_json = temp_dir / "list.json"
        list_json.write_text("[1, 2, 3]")
        with pytest.raises(ValueError) as excinfo:
            operations._read_json(list_json)
        assert "not a dict" in str(excinfo.value).lower()

        # Test reading non-existent file - bare FileNotFoundError
        with pytest.raises(FileNotFoundError):
            operations._read_json(temp_dir / "nonexistent.json")

    def test_write_json(self, temp_dir: Path) -> None:
        """Test writing JSON files."""
        operations = FileSystemOperations()

        # Test writing data - returns Path
        data = {"name": "Test", "values": [1, 2, 3], "nested": {"key": "value"}}
        write_path = temp_dir / "write.json"
        result = operations._write_json(write_path, data)
        assert isinstance(result, Path)

        # Verify the written data
        read_result = operations._read_json(write_path)
        assert read_result == data

        # Test writing with indent
        pretty_path = temp_dir / "pretty.json"
        result = operations._write_json(pretty_path, data, indent=4)
        assert isinstance(result, Path)
        content = pretty_path.read_text()
        assert "    " in content  # Check for indentation

        # Test writing with non-serializable data - bare TypeError propagates
        with patch("json.dumps") as mock_dumps:
            mock_dumps.side_effect = TypeError("Type error")
            with pytest.raises(TypeError):
                operations._write_json(temp_dir / "error.json", {"error": object()})

    def test_error_handling(self, temp_dir: Path) -> None:
        """Test error handling in _ops.

        NOTE (fs-internals-fix): patch targets corrected to the real call
        sites -- `_ops.write_ops._atomic_write` (imported from `_internal.
        file_ops`, used directly inside `WriteOperationsMixin._write_text`
        when `atomic=True`, the default), not the non-existent `quack_core.
        core.fs._ops._atomic_write` package-level name (see file-level
        NOTE). `_read_text` propagates a bare `PermissionError`/`RuntimeError`
        unchanged (`_internal.file_ops._read_file_text` does a plain
        `open()`, no except clause), so no QuackIOError wrapping applies at
        this layer either.
        """
        operations = FileSystemOperations()

        # Test permission error
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = PermissionError("Permission denied")
            with pytest.raises(PermissionError) as perm_excinfo:
                operations._read_text(temp_dir / "permission.txt")
            assert "permission denied" in str(perm_excinfo.value).lower()

        # Test IO error during atomic write
        with patch(
            "quack_core.core.fs._ops.write_ops._atomic_write"
        ) as mock_atomic_write:
            mock_atomic_write.side_effect = QuackIOError("IO error")
            with pytest.raises(QuackIOError) as io_excinfo:
                operations._write_text(temp_dir / "io_error.txt", "content")
            assert "io error" in str(io_excinfo.value).lower()

        # Test unexpected error
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = RuntimeError("Unexpected error")
            with pytest.raises(RuntimeError) as runtime_excinfo:
                operations._read_text(temp_dir / "unexpected.txt")
            assert "unexpected error" in str(runtime_excinfo.value).lower()
