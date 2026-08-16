# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_fs/test_results.py
# === QV-LLM:END ===

"""
Tests for the filesystem operation result classes.
"""

from pathlib import Path

from quack_core.core.fs import (
    DataResult,
    DirectoryInfoResult,
    FileInfoResult,
    FindResult,
    OperationResult,
    ReadResult,
    WriteResult,
)


class TestOperationResult:
    """Tests for the base OperationResult class."""

    def test_basic_result(self) -> None:
        """Test creating a basic operation result."""
        # ok is a required field (no default) on the canonical current
        # OperationResult contract -- confirmed live via a ValidationError before
        # this fix (pydantic-mypy-plugin round, quackverse-lint-mypy-backlog-SOW-07).
        # `success` is a read-only computed_field aliasing .ok (deprecated,
        # transitional), not a settable constructor kwarg -- kept below only on the
        # read side, where it still legitimately exercises that back-compat alias.
        # Applies uniformly to every construction call site in this file.
        result = OperationResult(ok=True, path=Path("/test/path"))

        assert result.success is True
        assert result.path == Path("/test/path")
        assert result.message is None
        assert result.error is None

    def test_failed_result(self) -> None:
        """Test creating a failed operation result."""
        result = OperationResult(
            ok=False, path=Path("/test/path"), error="Operation failed"
        )

        assert result.success is False
        assert result.path == Path("/test/path")
        assert result.error == "Operation failed"


class TestReadResult:
    """Tests for the ReadResult class."""

    def test_text_result(self) -> None:
        """Test creating a read result with text content."""
        result = ReadResult[str](
            ok=True,
            path=Path("/test/file.txt"),
            content="text content",
            encoding="utf-8",
        )

        assert result.success is True
        assert result.path == Path("/test/file.txt")
        assert result.content == "text content"
        assert result.encoding == "utf-8"

        # Test the text property
        assert result.text == "text content"

        # Test the binary property with text content
        binary = result.binary
        assert isinstance(binary, bytes)
        assert binary.decode("utf-8") == "text content"

    def test_binary_result(self) -> None:
        """Test creating a read result with binary content.

        The original test expected `.text` to RAISE UnicodeDecodeError on
        undecodable bytes under the default utf-8 encoding. Two independent
        problems, both confirmed live before touching anything: (1)
        b"\\x00\\x01\\x02\\x03" is itself valid UTF-8 (four ASCII control
        bytes) -- it was never going to fail decoding regardless of
        ReadResult's implementation, a pre-existing test-authoring bug, not a
        reorg-caused drift; (2) even with genuinely undecodable bytes
        (b"\\xff\\xfe..."), `.text` still does not raise -- its own docstring
        ("Safe access to text content. Returns None if invalid type/missing")
        and source (`except Exception: return None`) show this is a
        deliberate, documented safe-access design, not a bug. Reworked to
        assert the real current contract: `.text` returns None on a decode
        failure rather than raising.
        """
        invalid_utf8 = b"\xff\xfe\x02\x03"
        result = ReadResult[bytes](
            ok=True, path=Path("/test/file.bin"), content=invalid_utf8
        )

        assert result.success is True
        assert result.path == Path("/test/file.bin")
        assert result.content == invalid_utf8

        # Test the binary property
        assert result.binary == invalid_utf8

        # Test the text property with binary content that fails to decode under
        # the default utf-8 encoding: .text safely returns None, it never raises.
        assert result.text is None

        # Test with explicit encoding
        result.encoding = "latin1"
        text = result.text
        assert isinstance(text, str)
        assert text == invalid_utf8.decode("latin1")

    def test_invalid_content_type(self) -> None:
        """Test handling invalid content types.

        ReadResult.text/.binary are documented "safe access" properties (see their
        own docstrings in results.py: "Returns None if invalid type/missing") that
        deliberately catch and swallow decode/type errors, returning None rather
        than propagating an exception -- confirmed live, current, and intentional
        (not a regression to route around). Reworked from "raises TypeError" to
        "returns None", matching the real current, documented contract.
        """
        result = ReadResult(
            ok=True,
            path=Path("/test/file"),
            content=[1, 2, 3],  # type: ignore
        )

        # Both text and binary properties safely return None for an invalid type
        assert result.text is None
        assert result.binary is None


class TestWriteResult:
    """Tests for the WriteResult class."""

    def test_basic_write_result(self) -> None:
        """Test creating a basic write result."""
        result = WriteResult(ok=True, path=Path("/test/file.txt"), bytes_written=100)

        assert result.success is True
        assert result.path == Path("/test/file.txt")
        assert result.bytes_written == 100
        assert result.original_path is None
        assert result.checksum is None

    def test_write_result_with_checksum(self) -> None:
        """Test creating a write result with checksum."""
        result = WriteResult(
            ok=True,
            path=Path("/test/file.txt"),
            bytes_written=100,
            checksum="abcdef1234567890",
        )

        assert result.success is True
        assert result.checksum == "abcdef1234567890"

    def test_copy_move_result(self) -> None:
        """Test creating a result for copy/move _ops."""
        result = WriteResult(
            ok=True,
            path=Path("/test/dest.txt"),
            original_path=Path("/test/source.txt"),
            bytes_written=100,
        )

        assert result.success is True
        assert result.path == Path("/test/dest.txt")
        assert result.original_path == Path("/test/source.txt")
        assert result.bytes_written == 100


class TestFileInfoResult:
    """Tests for the FileInfoResult class."""

    def test_file_info(self) -> None:
        """Test creating a file info result."""
        result = FileInfoResult(
            ok=True,
            path=Path("/test/file.txt"),
            exists=True,
            is_file=True,
            is_dir=False,
            size=100,
            modified=1234567890.0,
            created=1234567800.0,
            owner="user",
            permissions=0o644,
            mime_type="text/plain",
        )

        assert result.success is True
        assert result.path == Path("/test/file.txt")
        assert result.exists is True
        assert result.is_file is True
        assert result.is_dir is False
        assert result.size == 100
        assert result.modified == 1234567890.0
        assert result.created == 1234567800.0
        assert result.owner == "user"
        assert result.permissions == 0o644
        assert result.mime_type == "text/plain"

    def test_directory_info(self) -> None:
        """Test creating a directory info result."""
        result = FileInfoResult(
            ok=True,
            path=Path("/test/dir"),
            exists=True,
            is_file=False,
            is_dir=True,
            size=None,
            modified=1234567890.0,
            created=1234567800.0,
            owner="user",
            permissions=0o755,
        )

        assert result.success is True
        assert result.path == Path("/test/dir")
        assert result.exists is True
        assert result.is_file is False
        assert result.is_dir is True
        assert result.size is None
        assert result.modified == 1234567890.0
        assert result.created == 1234567800.0
        assert result.owner == "user"
        assert result.permissions == 0o755
        assert result.mime_type is None

    def test_non_existent_file(self) -> None:
        """Test creating a result for a non-existent file."""
        result = FileInfoResult(
            ok=True, path=Path("/test/nonexistent.txt"), exists=False
        )

        assert result.success is True
        assert result.path == Path("/test/nonexistent.txt")
        assert result.exists is False
        assert result.is_file is False
        assert result.is_dir is False
        assert result.size is None
        assert result.modified is None
        assert result.created is None
        assert result.owner is None
        assert result.permissions is None
        assert result.mime_type is None


class TestDirectoryInfoResult:
    """Tests for the DirectoryInfoResult class."""

    def test_directory_listing(self) -> None:
        """Test creating a directory listing result."""
        files = [Path("/test/dir/file1.txt"), Path("/test/dir/file2.txt")]
        directories = [Path("/test/dir/subdir1"), Path("/test/dir/subdir2")]

        result = DirectoryInfoResult(
            ok=True,
            path=Path("/test/dir"),
            exists=True,
            is_empty=False,
            files=files,
            directories=directories,
            total_files=2,
            total_directories=2,
            total_size=1000,
        )

        assert result.success is True
        assert result.path == Path("/test/dir")
        assert result.exists is True
        assert result.is_empty is False
        assert result.files == files
        assert result.directories == directories
        assert result.total_files == 2
        assert result.total_directories == 2
        assert result.total_size == 1000

    def test_empty_directory(self) -> None:
        """Test creating a result for an empty directory."""
        result = DirectoryInfoResult(
            ok=True,
            path=Path("/test/empty_dir"),
            exists=True,
            is_empty=True,
            files=[],
            directories=[],
            total_files=0,
            total_directories=0,
            total_size=0,
        )

        assert result.success is True
        assert result.path == Path("/test/empty_dir")
        assert result.exists is True
        assert result.is_empty is True
        assert result.files == []
        assert result.directories == []
        assert result.total_files == 0
        assert result.total_directories == 0
        assert result.total_size == 0

    def test_non_existent_directory(self) -> None:
        """Test creating a result for a non-existent directory."""
        result = DirectoryInfoResult(
            ok=True,
            path=Path("/test/nonexistent_dir"),
            exists=False,
        )

        assert (
            result.success is True
        )  # Operation succeeded, but directory doesn't exist
        assert result.path == Path("/test/nonexistent_dir")
        assert result.exists is False
        assert result.is_empty is True
        assert result.files == []
        assert result.directories == []
        assert result.total_files == 0
        assert result.total_directories == 0
        assert result.total_size == 0


class TestFindResult:
    """Tests for the FindResult class."""

    def test_find_result(self) -> None:
        """Test creating a find result."""
        files = [Path("/test/dir/file1.txt"), Path("/test/dir/file2.txt")]
        directories = [Path("/test/dir/subdir1"), Path("/test/dir/subdir2")]

        result = FindResult(
            ok=True,
            path=Path("/test/dir"),
            pattern="*.txt",
            recursive=True,
            files=files,
            directories=directories,
            total_matches=4,
        )

        assert result.success is True
        assert result.path == Path("/test/dir")
        assert result.pattern == "*.txt"
        assert result.recursive is True
        assert result.files == files
        assert result.directories == directories
        assert result.total_matches == 4

    def test_no_matches(self) -> None:
        """Test creating a result with no matches."""
        result = FindResult(
            ok=True,
            path=Path("/test/dir"),
            pattern="*.nonexistent",
            recursive=True,
            files=[],
            directories=[],
        )

        assert result.success is True
        assert result.pattern == "*.nonexistent"
        assert result.files == []
        assert result.directories == []
        assert result.total_matches == 0


class TestDataResult:
    """Tests for the DataResult class."""

    def test_yaml_data_result(self) -> None:
        """Test creating a YAML data result."""
        data = {"name": "Test", "values": [1, 2, 3]}

        result = DataResult[dict](
            ok=True, path=Path("/test/file.yaml"), data=data, format="yaml"
        )

        assert result.success is True
        assert result.path == Path("/test/file.yaml")
        assert result.data == data
        assert result.format == "yaml"
        assert result.schema_valid is None

    def test_json_data_result(self) -> None:
        """Test creating a JSON data result."""
        data = {"name": "Test", "values": [1, 2, 3]}

        result = DataResult[dict](
            ok=True,
            path=Path("/test/file.json"),
            data=data,
            format="json",
            schema_valid=True,
        )

        assert result.success is True
        assert result.path == Path("/test/file.json")
        assert result.data == data
        assert result.format == "json"
        assert result.schema_valid is True

    def test_failed_data_result(self) -> None:
        """Test creating a failed data result."""
        result = DataResult[dict](
            ok=False,
            path=Path("/test/file.yaml"),
            data={},
            format="yaml",
            error="Failed to parse YAML data",
        )

        assert result.success is False
        assert result.path == Path("/test/file.yaml")
        assert result.data == {}
        assert result.format == "yaml"
        assert result.error == "Failed to parse YAML data"
