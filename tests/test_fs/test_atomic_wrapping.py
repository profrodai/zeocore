# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_fs/test_atomic_wrapping.py
# role: tests
# neighbors: __init__.py, test_operations.py, test_path_utils.py, test_results.py, test_service.py, test_utils.py
# exports: TestAtomicWrapping, temp_test_dir
# git_branch: refactor/toolkitWorkflow
# git_commit: e4fa88d
# === QV-LLM:END ===

"""
Tests to ensure that the write_text and write_binary operations wrap
their return values correctly in a WriteResult object—even when using atomic writes.

The error we encountered in production (i.e. "PosixPath object has no attribute 'success'")
suggests that under some conditions a raw Path is returned instead of a proper
WriteResult. These tests will detect such scenarios.
"""

from pathlib import Path

import pytest

from quack_core.lib.fs import WriteResult
from quack_core.lib.fs.service import FileSystemService


# A helper function to create a temporary directory for testing.
@pytest.fixture
def temp_test_dir(tmp_path: Path) -> Path:
    # Use the built-in tmp_path fixture from pytest.
    return tmp_path


class TestAtomicWrapping:
    """Tests to verify that write operations return a WriteResult wrapper."""

    @pytest.fixture
    def fs_service(self) -> FileSystemService:
        # Initialize the filesystem service with the current temporary directory
        return FileSystemService()

    def test_write_text_atomic(
        self, temp_test_dir: Path, fs_service: FileSystemService
    ) -> None:
        """Test that write_text returns a WriteResult when atomic=True."""
        file_path = temp_test_dir / "atomic_text.txt"
        content = "Hello, world with atomic write!"

        # Call the write_text method with atomic=True
        result = fs_service.write_text(file_path, content, atomic=True)

        # Verify the return type and attributes
        assert isinstance(result, WriteResult), (
            "The result must be an instance of WriteResult."
        )
        assert hasattr(result, "success"), (
            "The result object must have a 'success' attribute."
        )
        assert result.success is True, "The write operation should succeed."
        # The 'path' attribute in the result should be a Path instance equal to file_path
        assert isinstance(result.path, Path), (
            "The 'path' attribute should be a Path object."
        )
        assert result.bytes_written == len(content.encode('utf-8')), (
            "The bytes_written should match the content length."
        )
        # Read the file and verify contents
        assert file_path.read_text() == content, "File content does not match expected."

    def test_write_text_nonatomic(
        self, temp_test_dir: Path, fs_service: FileSystemService
    ) -> None:
        """Test that write_text returns a WriteResult when atomic=False."""
        file_path = temp_test_dir / "nonatomic_text.txt"
        content = "Hello, world with non-atomic write!"

        # Call the write_text method with atomic=False
        result = fs_service.write_text(file_path, content, atomic=False)

        # Verify the return type and attributes
        assert isinstance(result, WriteResult)
        assert result.success is True
        assert isinstance(result.path, Path)
        assert result.bytes_written == len(content.encode('utf-8'))
        assert file_path.read_text() == content, "File content does not match expected."

    def test_write_binary_atomic(
        self, temp_test_dir: Path, fs_service: FileSystemService
    ) -> None:
        """Test that write_binary returns a WriteResult when atomic=True."""
        file_path = temp_test_dir / "atomic_binary.bin"
        content = b"\x00\x01\x02\x03\x04"

        # Call the write_binary method with atomic=True
        result = fs_service.write_binary(file_path, content, atomic=True)

        # Verify the return type and attributes
        assert isinstance(result, WriteResult)
        assert result.success is True
        assert isinstance(result.path, Path)
        assert result.bytes_written == len(content)
        assert file_path.read_bytes() == content, (
            "Binary file content does not match expected."
        )

    def test_write_binary_nonatomic(
        self, temp_test_dir: Path, fs_service: FileSystemService
    ) -> None:
        """Test that write_binary returns a WriteResult when atomic=False."""
        file_path = temp_test_dir / "nonatomic_binary.bin"
        content = b"\x05\x06\x07\x08"

        # Call the write_binary method with atomic=False
        result = fs_service.write_binary(file_path, content, atomic=False)

        # Verify the return type and attributes
        assert isinstance(result, WriteResult)
        assert result.success is True
        assert isinstance(result.path, Path)
        assert result.bytes_written == len(content)
        assert file_path.read_bytes() == content, (
            "Binary file content does not match expected."
        )

    def test_write_text_checksum(
        self, temp_test_dir: Path, fs_service: FileSystemService
    ) -> None:
        """Test that write_text with calculate_checksum returns a WriteResult with a valid checksum."""
        file_path = temp_test_dir / "checksum_test.txt"
        content = "Content for checksum test."

        result = fs_service.write_text(
            file_path, content, atomic=True, calculate_checksum=True
        )

        assert isinstance(result, WriteResult)
        assert result.success is True
        # The checksum should not be None and should be a non-empty string
        assert result.checksum is not None, "Checksum should be calculated."
        assert isinstance(result.checksum, str) and len(result.checksum) > 0
        # Optionally, manually compute the checksum to cross-check (using sha256 here)
        import hashlib

        expected_checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert result.checksum == expected_checksum, (
            "Calculated checksum does not match expected."
        )

    def test_write_binary_checksum(
        self, temp_test_dir: Path, fs_service: FileSystemService
    ) -> None:
        """Test that write_binary with calculate_checksum returns a WriteResult with a valid checksum."""
        file_path = temp_test_dir / "checksum_bin.bin"
        content = b"\x0a\x0b\x0c\x0d"

        result = fs_service.write_binary(
            file_path, content, atomic=True, calculate_checksum=True
        )

        assert isinstance(result, WriteResult)
        assert result.success is True
        assert result.checksum is not None
        # Manually compute expected checksum for cross-check
        import hashlib

        expected_checksum = hashlib.sha256(content).hexdigest()
        assert result.checksum == expected_checksum, (
            "Calculated binary checksum does not match expected."
        )
