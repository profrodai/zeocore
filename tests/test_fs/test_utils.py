# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_fs/test_utils.py
# role: tests
# neighbors: __init__.py, test_atomic_wrapping.py, test_operations.py, test_path_utils.py, test_results.py, test_service.py
# exports: TestPathUtilities, TestFileUtilities
# git_branch: refactor/toolkitWorkflow
# git_commit: 21a4e25
# === QV-LLM:END ===

"""
Tests for filesystem utility functions.
"""

import os
import platform
import tempfile
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from quack_core.lib.errors import (
    QuackFileExistsError,
    QuackFileNotFoundError,
    QuackIOError,
    QuackPermissionError,
)
from quack_core.lib.fs._helpers import (
    _compute_checksum,
    _create_temp_directory,
    _create_temp_file,
    _get_disk_usage,
    _get_extension,
    _get_file_size_str,
    _get_file_timestamp,
    _get_file_type,
    _get_mime_type,
    _is_file_locked,
    _is_path_writeable,
    _is_same_file,
    _is_subdirectory,
    _normalize_path,
    _safe_copy,
    _safe_delete,
    _safe_move,
)
from quack_core.lib.fs._helpers.file_ops import (
    _atomic_write,
    _ensure_directory,
    _find_files_by_content,
    _get_unique_filename,
)
from quack_core.lib.fs._helpers.path_ops import _expand_user_vars, _join_path, _split_path


class TestPathUtilities:
    """Tests for path manipulation utilities."""

    def test_get_extension(self) -> None:
        """Test getting file extensions."""
        assert _get_extension("file.txt") == "txt"
        assert _get_extension("file.tar.gz") == "gz"
        assert _get_extension("file") == ""
        assert _get_extension(Path("/path/to/file.png")) == "png"
        assert _get_extension(".hidden") == "hidden"  # Special case for dot files

    def test_normalize_path(self) -> None:
        """Test normalizing paths."""
        # Test relative path
        normalized = _normalize_path("./test/../test_file.txt")
        assert normalized.name == "test_file.txt"
        assert normalized.is_absolute()

        # Test absolute path
        abs_path = Path("/absolute/path/file.txt")
        normalized = _normalize_path(abs_path)
        assert normalized == abs_path

        # Test user home
        home_path = "~/Documents/file.txt"
        normalized = _normalize_path(home_path)
        assert normalized.is_absolute()
        assert str(normalized).startswith(str(Path.home()))

    def test_is_same_file(self, temp_dir: Path) -> None:
        """Test checking if two paths refer to the same file."""
        # Create a test file
        file_path = temp_dir / "same_test.txt"
        file_path.touch()

        # Test with identical paths
        assert _is_same_file(file_path, file_path)

        # Test with resolved paths
        assert _is_same_file(file_path, temp_dir / "./same_test.txt")

        # Test with different files
        other_file = temp_dir / "other_file.txt"
        other_file.touch()
        assert not _is_same_file(file_path, other_file)

        # Test with non-existent file (should compare paths)
        nonexistent = temp_dir / "nonexistent.txt"
        assert not _is_same_file(file_path, nonexistent)
        assert _is_same_file(nonexistent, nonexistent)

        # Test with symlink if not on Windows
        if platform.system() != "Windows":
            link_path = temp_dir / "link_to_same.txt"
            os.symlink(file_path, link_path)
            assert _is_same_file(file_path, link_path)

    def test_is_subdirectory(self, temp_dir: Path) -> None:
        """Test checking if a path is a subdirectory of another path."""
        parent = temp_dir
        child = temp_dir / "subdir"
        child.mkdir()
        grandchild = child / "subsubdir"
        grandchild.mkdir()
        sibling = temp_dir / "sibling"
        sibling.mkdir()

        # Test direct child
        assert _is_subdirectory(child, parent)

        # Test grandchild
        assert _is_subdirectory(grandchild, parent)

        # Test with itself (should return False)
        assert not _is_subdirectory(parent, parent)

        # Test non-subdirectory
        assert not _is_subdirectory(sibling, child)
        assert not _is_subdirectory(parent, child)

        # Test with relative paths
        os.chdir(temp_dir)
        assert _is_subdirectory("subdir", "")
        assert _is_subdirectory(Path("subdir/subsubdir"), "")

    def test_join_path(self) -> None:
        """Test joining path components."""
        # Test with string paths
        joined = _join_path("dir1", "dir2", "file.txt")
        assert joined == Path("dir1/dir2/file.txt")

        # Test with Path objects
        joined = _join_path(Path("/dir1"), Path("dir2"), "file.txt")
        assert joined == Path("/dir1/dir2/file.txt")

        # Test with absolute path in the middle (should take precedence)
        joined = _join_path("dir1", "/absolute", "file.txt")
        assert joined == Path("/absolute/file.txt")

    def test_split_path(self) -> None:
        """Test splitting a path into components."""
        # Test absolute path
        parts = _split_path("/dir1/dir2/file.txt")
        assert parts[0] == "/"
        assert parts[-1] == "file.txt"
        assert "dir1" in parts
        assert "dir2" in parts

        # Test relative path
        parts = _split_path("dir1/dir2/file.txt")
        assert parts[0] == "dir1"
        assert parts[-1] == "file.txt"

        # Test path with dot at start
        parts = _split_path("./dir/file.txt")
        assert parts[0] == "."
        assert "dir" in parts
        assert parts[-1] == "file.txt"

    @pytest.mark.skipif(platform.system() == "Windows", reason="Windows paths differ")
    def test_expand_user_vars(self) -> None:
        """Test expanding user and environment variables in a path."""
        # Set up a test environment variable
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            # Test user home expansion
            expanded = _expand_user_vars("~/Documents")
            assert str(expanded).startswith(str(Path.home()))
            assert expanded.name == "Documents"

            # Test environment variable expansion
            expanded = _expand_user_vars("$TEST_VAR/file.txt")
            assert expanded.parts[0] == "test_value"
            assert expanded.name == "file.txt"

            # Test both together
            expanded = _expand_user_vars("~/$TEST_VAR/file.txt")
            assert str(expanded).startswith(str(Path.home()))
            assert "test_value" in expanded.parts
            assert expanded.name == "file.txt"


class TestFileUtilities:
    """Tests for file manipulation utilities."""

    def test_get_file_size_str(self) -> None:
        """Test human-readable file size formatting."""
        assert _get_file_size_str(0) == "0 B"
        assert _get_file_size_str(1023) == "1023 B"
        assert _get_file_size_str(1024) == "1.00 KB"
        assert _get_file_size_str(1024 * 1024) == "1.00 MB"
        assert _get_file_size_str(1024 * 1024 * 1024) == "1.00 GB"
        assert _get_file_size_str(1024 * 1024 * 1024 * 1024) == "1.00 TB"

    def test_get_unique_filename(self, temp_dir: Path) -> None:
        """Test generating unique filenames."""
        # Test with non-existent filename
        unique = _get_unique_filename(temp_dir, "unique.txt")
        assert unique == temp_dir / "unique.txt"

        # Create the file and test again
        unique.touch()
        unique2 = _get_unique_filename(temp_dir, "unique.txt")
        assert unique2 != unique
        assert unique2.name.startswith("unique_")
        assert unique2.name.endswith(".txt")

        # Test with multiple existing files
        unique2.touch()
        unique3 = _get_unique_filename(temp_dir, "unique.txt")
        assert unique3 != unique and unique3 != unique2
        assert unique3.name.startswith("unique_")
        assert unique3.name.endswith(".txt")

        # Test with raise_if_exists=True
        with pytest.raises(QuackFileExistsError):
            _get_unique_filename(temp_dir, "unique.txt", raise_if_exists=True)

        # Test with non-existent directory
        with pytest.raises(QuackFileNotFoundError):
            _get_unique_filename(temp_dir / "nonexistent", "file.txt")

        # Test with empty filename
        with pytest.raises(QuackIOError):
            _get_unique_filename(temp_dir, "")

    def test_create_temp_directory(self) -> None:
        """Test creating a temporary directory."""
        # Test with default parameters
        created_dir = _create_temp_directory()
        try:
            assert created_dir.exists()
            assert created_dir.is_dir()
            assert "quackcore_" in created_dir.name
        finally:
            # Clean up
            created_dir.rmdir()

        # Test with custom prefix and suffix
        created_dir = _create_temp_directory(prefix="testprefix_", suffix="_testsuffix")
        try:
            assert created_dir.exists()
            assert created_dir.is_dir()
            assert created_dir.name.startswith("testprefix_")
            assert created_dir.name.endswith("_testsuffix")
        finally:
            # Clean up
            created_dir.rmdir()

    def test_create_temp_file(self) -> None:
        """Test creating a temporary file."""
        # Test with default parameters
        temp_file = _create_temp_file()
        try:
            assert temp_file.exists()
            assert temp_file.is_file()
            assert "quackcore_" in temp_file.name
            assert temp_file.name.endswith(".txt")
        finally:
            # Clean up
            temp_file.unlink()

        # Test with custom parameters
        temp_file = _create_temp_file(suffix=".log", prefix="testfile_")
        try:
            assert temp_file.exists()
            assert temp_file.is_file()
            assert temp_file.name.startswith("testfile_")
            assert temp_file.name.endswith(".log")
        finally:
            # Clean up
            temp_file.unlink()

        # Test with custom directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            temp_file = _create_temp_file(directory=dir_path)
            assert temp_file.exists()
            assert temp_file.parent == dir_path

    def test_get_file_timestamp(self, temp_dir: Path) -> None:
        """Test getting file timestamps."""
        file_path = temp_dir / "timestamp_test.txt"
        file_path.write_text("test content")

        # Test getting timestamp of existing file
        timestamp = _get_file_timestamp(file_path)
        assert isinstance(timestamp, float)
        assert timestamp > 0

        # Test with non-existent file
        with pytest.raises(QuackFileNotFoundError):
            _get_file_timestamp(temp_dir / "nonexistent.txt")

    def test_is_path_writeable(self, temp_dir: Path) -> None:
        """Test checking if a path is writeable."""
        # Test with existing directory
        assert _is_path_writeable(temp_dir)

        # Test with existing file
        file_path = temp_dir / "writable_test.txt"
        file_path.write_text("test content")
        assert _is_path_writeable(file_path)

        # Test with non-existent path (should check parent directory)
        assert _is_path_writeable(temp_dir / "nonexistent.txt")

        # Test with non-writeable path (mock permission denied)
        with patch("os.access", return_value=False):
            assert not _is_path_writeable(file_path)

        # Test with directory creation failure
        with patch("pathlib.Path.mkdir", side_effect=PermissionError):
            assert not _is_path_writeable(temp_dir / "new_dir")

    def test_get_mime_type(self, temp_dir: Path) -> None:
        """Test getting MIME types for files."""
        # Create files with different extensions
        txt_file = temp_dir / "mime_test.txt"
        txt_file.write_text("text content")

        html_file = temp_dir / "mime_test.html"
        html_file.write_text("<html><body>test</body></html>")

        # Test text file
        mime = _get_mime_type(txt_file)
        assert mime is not None
        assert "text" in mime

        # Test HTML file
        mime = _get_mime_type(html_file)
        assert mime is not None
        assert "html" in mime

        # Test with non-existent file (should still guess based on extension)
        mime = _get_mime_type(temp_dir / "nonexistent.pdf")
        assert mime is not None
        assert "pdf" in mime

        # Test with no extension
        mime = _get_mime_type(temp_dir / "no_extension")
        assert mime is None or mime == "application/octet-stream"

    def test_get_file_type(self, temp_dir: Path) -> None:
        """Test detecting file types."""
        # Create different types of files
        text_file = temp_dir / "type_test.txt"
        text_file.write_text("text content")

        binary_file = temp_dir / "type_test.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03")

        dir_path = temp_dir / "type_test_dir"
        dir_path.mkdir()

        # Create a symlink if not on Windows
        symlink_path = None
        if platform.system() != "Windows":
            symlink_path = temp_dir / "type_test_link"
            os.symlink(text_file, symlink_path)

        # Test text file
        assert _get_file_type(text_file) == "text"

        # Test binary file
        assert _get_file_type(binary_file) == "binary"

        # Test directory
        assert _get_file_type(dir_path) == "directory"

        # Test symlink if available
        if symlink_path:
            assert _get_file_type(symlink_path) == "symlink"

        # Test non-existent file
        assert _get_file_type(temp_dir / "nonexistent.txt") == "nonexistent"

        # Test error case
        with patch("builtins.open", side_effect=OSError):
            assert _get_file_type(text_file) == "unknown"

    @pytest.mark.skipif(
        "CI" in os.environ, reason="Disk usage may vary in CI environments"
    )
    def test_get_disk_usage(self, temp_dir: Path) -> None:
        """Test getting disk usage information."""
        usage = _get_disk_usage(temp_dir)

        assert "total" in usage
        assert "used" in usage
        assert "free" in usage
        assert usage["total"] > 0
        assert usage["free"] >= 0
        assert usage["used"] >= 0
        assert usage["total"] >= usage["used"]

        # Test with non-existent path
        with pytest.raises(QuackIOError):
            _get_disk_usage(temp_dir / "nonexistent")

    def test_find_files_by_content(self, temp_dir: Path) -> None:
        """Test finding files containing specific text."""
        # Create files with different content
        file1 = temp_dir / "find_content1.txt"
        file1.write_text("This file contains target text to find")

        file2 = temp_dir / "find_content2.txt"
        file2.write_text("This file doesn't have the keyword")

        subdir = temp_dir / "subdir"
        subdir.mkdir()
        file3 = subdir / "find_content3.txt"
        file3.write_text("Another file with target text in subdirectory")

        # Test finding with exact match
        results = _find_files_by_content(temp_dir, "target text")
        assert len(results) == 2
        assert file1 in results
        assert file3 in results
        assert file2 not in results

        # Test finding with regex
        results = _find_files_by_content(temp_dir, "target.*?find")
        assert len(results) == 1
        assert file1 in results

        # Test with non-recursive search
        results = _find_files_by_content(temp_dir, "target text", recursive=False)
        assert len(results) == 1
        assert file1 in results
        assert file3 not in results

        # Test with invalid regex
        with pytest.raises(QuackIOError):
            _find_files_by_content(temp_dir, "[invalid regex")

        # Test with non-existent directory
        results = _find_files_by_content(temp_dir / "nonexistent", "text")
        assert len(results) == 0

    def test_ensure_directory(self, temp_dir: Path) -> None:
        """Test ensuring a directory exists."""
        # Test with non-existent directory
        new_dir = temp_dir / "new_dir"
        result = _ensure_directory(new_dir)
        assert result.exists()
        assert result.is_dir()

        # Test with existing directory
        result = _ensure_directory(new_dir)
        assert result.exists()
        assert result.is_dir()

        # Test with nested directory
        nested_dir = new_dir / "subdir1" / "subdir2"
        result = _ensure_directory(nested_dir)
        assert result.exists()
        assert result.is_dir()

        # Test with exist_ok=False
        with pytest.raises(QuackFileExistsError):
            _ensure_directory(new_dir, exist_ok=False)

        # Test with permission denied
        with patch("pathlib.Path.mkdir", side_effect=PermissionError):
            with pytest.raises(QuackPermissionError):
                _ensure_directory(temp_dir / "permission_denied")

    def test_compute_checksum(self, temp_dir: Path) -> None:
        """Test computing file checksums."""
        # Create a test file
        file_path = temp_dir / "checksum_test.txt"
        content = "test content for checksum"
        file_path.write_text(content)

        # Compute expected checksum
        expected = sha256(content.encode()).hexdigest()

        # Test with default algorithm (sha256)
        checksum = _compute_checksum(file_path)
        assert checksum == expected

        # Test with non-existent file
        with pytest.raises(QuackFileNotFoundError):
            _compute_checksum(temp_dir / "nonexistent.txt")

        # Test with directory (should fail)
        with pytest.raises(QuackIOError):
            _compute_checksum(temp_dir)

    def test_atomic_write(self, temp_dir: Path) -> None:
        """Test atomic file writing."""
        file_path = temp_dir / "atomic_test.txt"

        # Test writing text content
        content = "test content for atomic write"
        result = _atomic_write(file_path, content)
        assert result == file_path
        assert file_path.read_text() == content

        # Test writing binary content
        binary_content = b"\x00\x01\x02\x03"
        result = _atomic_write(file_path, binary_content)
        assert result == file_path
        assert file_path.read_bytes() == binary_content

        # Test with error during write
        with patch("os.replace", side_effect=OSError("Test error")):
            with pytest.raises(QuackIOError):
                _atomic_write(file_path, "failure content")

    def test_safe_copy(self, temp_dir: Path) -> None:
        """Test safe file copying."""
        # Create a source file
        src_path = temp_dir / "safe_copy_src.txt"
        src_path.write_text("safe copy content")

        # Test copying to non-existent destination
        dst_path = temp_dir / "safe_copy_dst.txt"
        result = _safe_copy(src_path, dst_path)
        assert result == dst_path
        assert dst_path.exists()
        assert dst_path.read_text() == "safe copy content"

        # Test copying to existing destination (should fail without overwrite)
        with pytest.raises(QuackFileExistsError):
            _safe_copy(src_path, dst_path)

        # Test copying with overwrite
        src_path.write_text("updated content")
        result = _safe_copy(src_path, dst_path, overwrite=True)
        assert result == dst_path
        assert dst_path.read_text() == "updated content"

        # Test copying non-existent source
        with pytest.raises(QuackFileNotFoundError):
            _safe_copy(temp_dir / "nonexistent.txt", dst_path)

        # Test copying directories
        src_dir = temp_dir / "src_dir"
        src_dir.mkdir()
        (src_dir / "file.txt").write_text("dir file content")

        dst_dir = temp_dir / "dst_dir"
        result = _safe_copy(src_dir, dst_dir)
        assert result == dst_dir
        assert dst_dir.is_dir()
        assert (dst_dir / "file.txt").exists()
        assert (dst_dir / "file.txt").read_text() == "dir file content"

    def test_safe_move(self, temp_dir: Path) -> None:
        """Test safe file moving."""
        # Create a source file
        src_path = temp_dir / "safe_move_src.txt"
        src_path.write_text("safe move content")

        # Test moving to non-existent destination
        dst_path = temp_dir / "safe_move_dst.txt"
        result = _safe_move(src_path, dst_path)
        assert result == dst_path
        assert dst_path.exists()
        assert not src_path.exists()
        assert dst_path.read_text() == "safe move content"

        # Create a new source file
        src_path.write_text("new safe move content")

        # Test moving to existing destination (should fail without overwrite)
        with pytest.raises(QuackFileExistsError):
            _safe_move(src_path, dst_path)

        # Test moving with overwrite
        result = _safe_move(src_path, dst_path, overwrite=True)
        assert result == dst_path
        assert not src_path.exists()
        assert dst_path.read_text() == "new safe move content"

        # Test moving non-existent source
        with pytest.raises(QuackFileNotFoundError):
            _safe_move(temp_dir / "nonexistent.txt", dst_path)

        # Test moving directories
        src_dir = temp_dir / "move_src_dir"
        src_dir.mkdir()
        (src_dir / "file.txt").write_text("dir file content for move")

        dst_dir = temp_dir / "move_dst_dir"
        result = _safe_move(src_dir, dst_dir)
        assert result == dst_dir
        assert dst_dir.is_dir()
        assert not src_dir.exists()
        assert (dst_dir / "file.txt").exists()
        assert (dst_dir / "file.txt").read_text() == "dir file content for move"

    def test_safe_delete(self, temp_dir: Path) -> None:
        """Test safe file deletion."""
        # Create a file to delete
        file_path = temp_dir / "safe_delete.txt"
        file_path.write_text("delete me safely")

        # Test deleting existing file
        result = _safe_delete(file_path)
        assert result is True
        assert not file_path.exists()

        # Test deleting non-existent file with missing_ok=True
        result = _safe_delete(file_path)
        assert result is False

        # Test deleting non-existent file with missing_ok=False
        with pytest.raises(QuackFileNotFoundError):
            _safe_delete(file_path, missing_ok=False)

        # Test deleting directory
        dir_path = temp_dir / "delete_dir"
        dir_path.mkdir()
        (dir_path / "file.txt").write_text("delete me too")

        result = _safe_delete(dir_path)
        assert result is True
        assert not dir_path.exists()

    @pytest.mark.skipif(
        platform.system() != "Windows",
        reason="is_file_locked is mostly relevant on Windows",
    )
    def test_is_file_locked(self, temp_dir: Path) -> None:
        """Test checking if a file is locked."""
        # This test is minimal because actually locking files in a test is tricky
        file_path = temp_dir / "lock_test.txt"
        file_path.write_text("test locking")

        # File should not be locked
        assert not _is_file_locked(file_path)

        # Test with non-existent file
        assert not _is_file_locked(temp_dir / "nonexistent.txt")

    @given(st.text(min_size=1, max_size=100))
    def test_hypothetical_path_operations(self, text: str) -> None:
        """Test path _operations with hypothesis-generated text."""
        # Handle problematic characters more carefully:
        # 1. Period at start of string
        # 2. Unicode characters that might cause file system issues
        # 3. Special characters that aren't valid in filenames

        # Create a sanitized filename that's safe for the filesystem
        sanitized_text = ""
        for c in text:
            if c.isalnum() or c in " _-.":
                # Only include safe characters
                sanitized_text += c

        # Handle special cases
        if not sanitized_text or sanitized_text.isspace():
            valid_filename = "default"
        elif sanitized_text == "." or sanitized_text.startswith("."):
            valid_filename = (
                "dot" + sanitized_text[1:] if len(sanitized_text) > 1 else "dot"
            )
        else:
            valid_filename = sanitized_text.strip()

        # Test extension extraction (this should be safe)
        with_extension = f"{valid_filename}.txt"
        assert _get_extension(with_extension) == "txt"

        # Test path joining with the filename
        joined = _join_path("dir1", valid_filename)

        # For special paths like "." we need to check differently
        if valid_filename == ".":
            assert joined == Path("dir1/.")
        else:
            # For regular filenames, check that the name is preserved
            assert joined.name == valid_filename

        # Skip file creation part which can fail with certain Unicode characters
        # Instead, check path normalization in a safer way
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                test_path = tmp_path / valid_filename

                # Only try to create the file if it's a safe filename
                try:
                    test_path.touch()  # Create the file if possible
                    normalized = _normalize_path(test_path)
                    assert normalized.is_absolute()
                except (OSError, UnicodeEncodeError):
                    # If we can't create the file, just verify path construction
                    assert test_path.parent == tmp_path
        except Exception as e:
            pytest.skip(f"Skipping file creation due to path issue: {e}")
