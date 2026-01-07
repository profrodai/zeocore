# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_fs/test_operations.py
# role: tests
# neighbors: __init__.py, test_atomic_wrapping.py, test_path_utils.py, test_results.py, test_service.py, test_utils.py
# exports: TestFileSystemOperations
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

"""
Tests for the FileSystemOperations class.

Note: These tests have been updated to reflect the internal refactoring
where operations return raw types instead of result objects.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from quack_core.lib.errors import QuackFileExistsError, QuackIOError
from quack_core.core.fs._operations import FileSystemOperations


class TestFileSystemOperations:
    """Tests for the FileSystemOperations class."""

    def test_initialize(self, temp_dir: Path) -> None:
        """Test initializing _operations with and without base_dir."""
        # Default initialization
        operations = FileSystemOperations()
        assert operations.base_dir == Path.cwd()

        # Initialize with custom base_dir (using the temp_dir fixture)
        operations = FileSystemOperations(base_dir=temp_dir)
        assert operations.base_dir == temp_dir

    def test_resolve_path(self) -> None:
        """Test resolving paths relative to the base directory."""
        base_dir = Path("/base/dir")
        operations = FileSystemOperations(base_dir=base_dir)

        # Test with relative path
        rel_path = Path("subdir/file.txt")
        resolved = operations._resolve_path(rel_path)
        assert resolved == base_dir / rel_path

        # Test with absolute path
        abs_path = Path("/absolute/path/file.txt")
        resolved = operations._resolve_path(abs_path)
        assert resolved == abs_path  # Should remain unchanged

        # Test with string path
        str_path = "string/path/file.txt"
        resolved = operations._resolve_path(str_path)
        assert resolved == base_dir / str_path

    def test_read_text(self, temp_dir: Path) -> None:
        """Test reading text from a file."""
        operations = FileSystemOperations(base_dir=temp_dir)

        # Create a test file
        file_path = temp_dir / "text_test.txt"
        file_path.write_text("test content")

        # Test successful read - now returns string directly
        result = operations._read_text("text_test.txt")
        assert isinstance(result, str)
        assert result == "test content"

        # Test custom encoding
        utf16_file = temp_dir / "utf16_test.txt"
        utf16_file.write_text("тест текст", encoding="utf-16")
        result = operations._read_text("utf16_test.txt", encoding="utf-16")
        assert isinstance(result, str)
        assert result == "тест текст"

        # Test reading non-existent file - now raises FileNotFoundError
        with pytest.raises(FileNotFoundError):
            operations._read_text("nonexistent.txt")

    def test_read_binary(self, temp_dir: Path) -> None:
        """Test reading binary data from a file."""
        operations = FileSystemOperations(base_dir=temp_dir)

        # Create a test binary file
        file_path = temp_dir / "binary_test.bin"
        file_path.write_bytes(b"\x00\x01\x02\x03")

        # Test successful read - now returns bytes directly
        result = operations._read_binary("binary_test.bin")
        assert isinstance(result, bytes)
        assert result == b"\x00\x01\x02\x03"

        # Test reading non-existent file - now raises FileNotFoundError
        with pytest.raises(FileNotFoundError):
            operations._read_binary("nonexistent.bin")

    def test_write_text(self, temp_dir: Path) -> None:
        """Test writing text to a file."""
        operations = FileSystemOperations(base_dir=temp_dir)

        # Test writing to a new file - now returns Path
        result = operations._write_text("write_test.txt", "test content")
        assert isinstance(result, Path)
        assert (temp_dir / "write_test.txt").read_text() == "test content"

        # Test writing with custom encoding
        result = operations._write_text("encoding_test.txt", "тест", encoding="utf-16")
        assert isinstance(result, Path)
        assert (temp_dir / "encoding_test.txt").read_text(encoding="utf-16") == "тест"

        # Test with atomic=False
        result = operations._write_text("nonatomic.txt", "content", atomic=False)
        assert isinstance(result, Path)
        assert (temp_dir / "nonatomic.txt").read_text() == "content"

        # Test with calculate_checksum=True
        # NOTE: Since _operations now return raw types, we can't check checksum directly
        # Just ensure the operation completes successfully
        result = operations._write_text(
            "checksum.txt", "content", calculate_checksum=True
        )
        assert isinstance(result, Path)
        assert (temp_dir / "checksum.txt").read_text() == "content"

    def test_write_binary(self, temp_dir: Path) -> None:
        """Test writing binary data to a file."""
        operations = FileSystemOperations(base_dir=temp_dir)

        # Test writing to a new file - now returns Path
        result = operations._write_binary("binary.bin", b"\x00\x01\x02\x03")
        assert isinstance(result, Path)
        assert (temp_dir / "binary.bin").read_bytes() == b"\x00\x01\x02\x03"

        # Test with atomic=False
        result = operations._write_binary(
            "nonatomic.bin", b"\x04\x05\x06\x07", atomic=False
        )
        assert isinstance(result, Path)
        assert (temp_dir / "nonatomic.bin").read_bytes() == b"\x04\x05\x06\x07"

        # Test with calculate_checksum=True
        # NOTE: Since _operations now return raw types, we can't check checksum directly
        # Just ensure the operation completes successfully
        result = operations._write_binary(
            "checksum.bin", b"\x08\x09\x0a\x0b", calculate_checksum=True
        )
        assert isinstance(result, Path)
        assert (temp_dir / "checksum.bin").read_bytes() == b"\x08\x09\x0a\x0b"

    def test_copy(self, temp_dir: Path) -> None:
        """Test copying a file."""
        operations = FileSystemOperations(base_dir=temp_dir)

        # Create a source file
        source_path = temp_dir / "source.txt"
        source_path.write_text("source content")

        # Test successful copy - now returns Path to destination
        result = operations._copy("source.txt", "dest.txt")
        assert isinstance(result, Path)
        assert (temp_dir / "dest.txt").exists()
        assert (temp_dir / "dest.txt").read_text() == "source content"

        # Test copy to existing file (should fail)
        with pytest.raises(Exception) as excinfo:
            operations._copy("source.txt", "dest.txt")
        assert "already exists" in str(excinfo.value).lower()

        # Test copy with overwrite
        result = operations._copy("source.txt", "dest.txt", overwrite=True)
        assert isinstance(result, Path)

        # Test copy with non-existent source - modified to check for error message
        with pytest.raises(Exception) as excinfo:
            operations._copy("nonexistent.txt", "new_dest.txt")
        assert "not found" in str(excinfo.value).lower()

    def test_move(self, temp_dir: Path) -> None:
        """Test moving a file."""
        operations = FileSystemOperations(base_dir=temp_dir)

        # Create a source file
        source_path = temp_dir / "move_source.txt"
        source_path.write_text("move content")

        # Test successful move - now returns Path to destination
        result = operations._move("move_source.txt", "move_dest.txt")
        assert isinstance(result, Path)
        assert (temp_dir / "move_dest.txt").exists()
        assert not (temp_dir / "move_source.txt").exists()
        assert (temp_dir / "move_dest.txt").read_text() == "move content"

        # Create new source file
        source_path.write_text("new move content")

        # Test move to existing file (should fail)
        with pytest.raises(Exception) as excinfo:
            operations._move("move_source.txt", "move_dest.txt")
        assert "already exists" in str(excinfo.value).lower()

        # Test move with overwrite
        result = operations._move("move_source.txt", "move_dest.txt", overwrite=True)
        assert isinstance(result, Path)
        assert (temp_dir / "move_dest.txt").read_text() == "new move content"

        # Test move with non-existent source
        with pytest.raises(Exception) as excinfo:
            operations._move("nonexistent.txt", "new_dest.txt")
        assert "not found" in str(excinfo.value).lower()

    def test_delete(self, temp_dir: Path) -> None:
        """Test deleting a file."""
        operations = FileSystemOperations(base_dir=temp_dir)

        # Create a file to delete
        file_path = temp_dir / "to_delete.txt"
        file_path.write_text("delete me")

        # Test successful delete - now returns bool
        result = operations._delete("to_delete.txt")
        assert result is True
        assert not file_path.exists()

        # Test deleting non-existent file (should succeed with missing_ok=True)
        # NOTE: This has been updated to match the actual implementation
        result = operations._delete("to_delete.txt")
        assert result is False  # The implementation returns False for missing files with missing_ok=True

        # Test deleting non-existent file with missing_ok=False
        with pytest.raises(Exception) as excinfo:
            operations._delete("to_delete.txt", missing_ok=False)
        assert "not found" in str(excinfo.value).lower() or "does not exist" in str(
            excinfo.value).lower()

    def test_create_directory(self, temp_dir: Path) -> None:
        """Test creating a directory."""
        operations = FileSystemOperations(base_dir=temp_dir)

        # Test creating directory - now returns Path
        result = operations._create_directory("new_dir")
        assert isinstance(result, Path)
        assert (temp_dir / "new_dir").is_dir()

        # Test creating existing directory (should succeed with exist_ok=True)
        result = operations._create_directory("new_dir")
        assert isinstance(result, Path)

        # Test creating existing directory with exist_ok=False
        with patch(
                "quack_core.core.fs._operations._ensure_directory"
        ) as mock_ensure_directory:
            mock_ensure_directory.side_effect = QuackFileExistsError(
                str(temp_dir / "new_dir")
            )
            with pytest.raises(QuackFileExistsError) as excinfo:
                operations._create_directory("new_dir", exist_ok=False)
            assert "already exists" in str(excinfo.value).lower()

    def test_get_file_info(self, temp_dir: Path) -> None:
        """Test getting file information."""
        operations = FileSystemOperations(base_dir=temp_dir)

        # Create a test file
        file_path = temp_dir / "info_test.txt"
        file_path.write_text("info content")

        # Create a test directory
        dir_path = temp_dir / "info_dir"
        dir_path.mkdir()

        # Test getting info for a file - now returns FileInfo object
        result = operations._get_file_info("info_test.txt")
        assert result.exists is True
        assert result.is_file is True
        assert result.is_dir is False
        assert result.size > 0
        assert result.modified is not None

        # Test getting info for a directory
        result = operations._get_file_info("info_dir")
        assert result.exists is True
        assert result.is_file is False
        assert result.is_dir is True

        # Test getting info for a non-existent file
        result = operations._get_file_info("nonexistent.txt")
        assert result.exists is False

    def test_list_directory(self, temp_dir: Path) -> None:
        """Test listing directory contents."""
        operations = FileSystemOperations(base_dir=temp_dir)

        # Create some files and directories for testing
        (temp_dir / "list_file1.txt").write_text("content1")
        (temp_dir / "list_file2.txt").write_text("content2")
        (temp_dir / ".hidden_file").write_text("hidden")
        (temp_dir / "list_dir").mkdir()

        # Test listing with default parameters - now returns DirectoryInfo object
        result = operations._list_directory(".")
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
        result = operations._list_directory(".", include_hidden=True)
        assert any(f.name == ".hidden_file" for f in result.files)

        # Test listing with pattern
        result = operations._list_directory(".", pattern="list_*.txt")
        assert len(result.files) == 2
        assert all(f.name.startswith("list_") for f in result.files)

        # Test listing non-existent directory - updated to expect FileNotFoundError
        with pytest.raises(FileNotFoundError) as excinfo:
            operations._list_directory("nonexistent_dir")
        assert "does not exist" in str(excinfo.value).lower()

    def test_find_files(self, temp_dir: Path) -> None:
        """Test finding files matching a pattern."""
        operations = FileSystemOperations(base_dir=temp_dir)

        # Create some files and directories for testing
        (temp_dir / "find_file1.txt").write_text("content1")
        (temp_dir / "find_file2.txt").write_text("content2")
        (temp_dir / "find_doc.pdf").write_text("pdf content")
        (temp_dir / "find_dir").mkdir()
        (temp_dir / "find_dir" / "subfile.txt").write_text("sub content")

        # Test finding with pattern: change pattern to match all files containing "file"
        # Now returns tuple of (files, directories)
        result = operations._find_files(".", "*file*.txt")
        files, directories = result
        assert len(files) == 3  # Now matches: find_file1.txt, find_file2.txt, and subfile.txt
        assert any(f.name == "find_file1.txt" for f in files)
        assert any(f.name == "find_file2.txt" for f in files)
        assert any(f.name == "subfile.txt" for f in files)

        # Test finding without recursion
        result = operations._find_files(".", "find_*.txt", recursive=False)
        files, directories = result
        assert len(files) == 2
        assert not any(f.name == "subfile.txt" for f in files)

        # Test finding directories
        result = operations._find_files(".", "*dir*")
        files, directories = result
        assert len(directories) >= 1
        assert any(d.name == "find_dir" for d in directories)

        # Test finding with non-existent directory - updated to expect FileNotFoundError
        with pytest.raises(Exception) as excinfo:
            operations._find_files("nonexistent_dir", "*")
        assert "does not exist" in str(excinfo.value).lower() or "not a directory" in str(excinfo.value).lower()

    def test_read_yaml(self, temp_dir: Path) -> None:
        """Test reading YAML files."""
        operations = FileSystemOperations(base_dir=temp_dir)

        # Create a YAML file
        data = {"name": "Test", "values": [1, 2, 3], "nested": {"key": "value"}}
        yaml_file = temp_dir / "test.yaml"
        yaml_file.write_text(yaml.dump(data))

        # Test successful read - now returns dict directly
        result = operations._read_yaml("test.yaml")
        assert isinstance(result, dict)
        assert result == data

        # Test empty YAML file (should return empty dict)
        empty_yaml = temp_dir / "empty.yaml"
        empty_yaml.write_text("")
        result = operations._read_yaml("empty.yaml")
        assert isinstance(result, dict)
        assert result == {}

        # Test reading invalid YAML - updated to handle actual error message
        invalid_yaml = temp_dir / "invalid.yaml"
        invalid_yaml.write_text("name: Test\ninvalid: : value")
        with pytest.raises(Exception) as excinfo:
            operations._read_yaml("invalid.yaml")
        # The error message contains details about the YAML parsing error
        assert "mapping values" in str(excinfo.value).lower() or "yaml" in str(
            excinfo.value).lower()

        # Test non-dictionary YAML
        list_yaml = temp_dir / "list.yaml"
        list_yaml.write_text("- item1\n- item2")
        with pytest.raises(Exception) as excinfo:
            operations._read_yaml("list.yaml")
        assert "not a dictionary" in str(excinfo.value).lower()

        # Test reading non-existent file
        with pytest.raises(FileNotFoundError) as excinfo:
            operations._read_yaml("nonexistent.yaml")
        assert "no such file" in str(excinfo.value).lower()

    def test_write_yaml(self, temp_dir: Path) -> None:
        """Test writing YAML files."""
        operations = FileSystemOperations(base_dir=temp_dir)

        # Test writing data - now returns Path
        data = {"name": "Test", "values": [1, 2, 3], "nested": {"key": "value"}}
        result = operations._write_yaml("write.yaml", data)
        assert isinstance(result, Path)

        # Verify the written data
        read_result = operations._read_yaml("write.yaml")
        assert read_result == data

        # Test writing with non-serializable data
        with patch("yaml.safe_dump") as mock_dump:
            mock_dump.side_effect = yaml.YAMLError("YAML error")
            with pytest.raises(Exception) as excinfo:
                operations._write_yaml("error.yaml", {"error": object()})
            assert "yaml" in str(excinfo.value).lower()

    def test_read_json(self, temp_dir: Path) -> None:
        """Test reading JSON files."""
        operations = FileSystemOperations(base_dir=temp_dir)

        # Create a JSON file
        data = {"name": "Test", "values": [1, 2, 3], "nested": {"key": "value"}}
        json_file = temp_dir / "test.json"
        json_file.write_text(json.dumps(data))

        # Test successful read - now returns dict directly
        result = operations._read_json("test.json")
        assert isinstance(result, dict)
        assert result == data

        # Test reading invalid JSON - updated to handle actual error message
        invalid_json = temp_dir / "invalid.json"
        invalid_json.write_text('{"name": "Test", "invalid": }')
        with pytest.raises(Exception) as excinfo:
            operations._read_json("invalid.json")
        # The error message contains details about the JSON parsing error
        assert "expecting value" in str(excinfo.value).lower() or "json" in str(
            excinfo.value).lower()

        # Test non-dictionary JSON
        list_json = temp_dir / "list.json"
        list_json.write_text("[1, 2, 3]")
        with pytest.raises(Exception) as excinfo:
            operations._read_json("list.json")
        assert "not an object" in str(excinfo.value).lower()

        # Test reading non-existent file
        with pytest.raises(FileNotFoundError) as excinfo:
            operations._read_json("nonexistent.json")
        assert "no such file" in str(excinfo.value).lower()

    def test_write_json(self, temp_dir: Path) -> None:
        """Test writing JSON files."""
        operations = FileSystemOperations(base_dir=temp_dir)

        # Test writing data - now returns Path
        data = {"name": "Test", "values": [1, 2, 3], "nested": {"key": "value"}}
        result = operations._write_json("write.json", data)
        assert isinstance(result, Path)

        # Verify the written data
        read_result = operations._read_json("write.json")
        assert read_result == data

        # Test writing with indent
        result = operations._write_json("pretty.json", data, indent=4)
        assert isinstance(result, Path)
        content = (temp_dir / "pretty.json").read_text()
        assert "    " in content  # Check for indentation

        # Test writing with non-serializable data
        with patch("json.dumps") as mock_dumps:
            mock_dumps.side_effect = TypeError("Type error")
            with pytest.raises(Exception) as excinfo:
                operations._write_json("error.json", {"error": object()})
            assert "json" in str(excinfo.value).lower() or "type error" in str(excinfo.value).lower()

    def test_error_handling(self, temp_dir: Path) -> None:
        """Test error handling in _operations."""
        operations = FileSystemOperations(base_dir=temp_dir)

        # Test permission error
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = PermissionError("Permission denied")
            with pytest.raises(PermissionError) as excinfo:
                operations._read_text("permission.txt")
            assert "permission denied" in str(excinfo.value).lower()

        # Test IO error
        with patch("quack_core.core.fs._operations._atomic_write") as mock_atomic_write:
            mock_atomic_write.side_effect = QuackIOError("IO error")
            with pytest.raises(QuackIOError) as excinfo:
                operations._write_text("io_error.txt", "content")
            assert "io error" in str(excinfo.value).lower()

        # Test unexpected error
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = RuntimeError("Unexpected error")
            with pytest.raises(RuntimeError) as excinfo:
                operations._read_text("unexpected.txt")
            assert "unexpected error" in str(excinfo.value).lower()
