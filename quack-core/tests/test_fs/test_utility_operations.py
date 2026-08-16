# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_fs/test_utility_operations.py
# === QV-LLM:END ===

"""
Tests for quack_core.core.fs.service.utility_operations.UtilityOperationsMixin,
exercised through the real FileSystemService (the concrete class that mixes it
in — see service/full_class.py).

quackverse-coverage-90: this module carried 23% coverage (97/126 stmts missed)
before this file, despite FileSystemService already being exercised elsewhere
in tests/test_fs/ — none of its dedicated *utility* methods (get_unique_filename,
create_temp_file, create_temp_directory, find_files_by_content, get_disk_usage,
get_file_type, get_file_size_str, get_mime_type, get_file_timestamp,
compute_checksum, is_path_writeable, is_file_locked, atomic_write) had a
dedicated test anywhere. Every assertion below operates on a real FileSystemService
against real files on a real temp directory (the shared `temp_dir`/`test_file`
conftest fixtures) — no mocks standing in for the filesystem or the service.
"""

from pathlib import Path

from quack_core.core.fs.service import FileSystemService


class TestGetUniqueFilename:
    def test_returns_original_name_when_no_collision(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        result = service.get_unique_filename(temp_dir, "new_file.txt")
        assert result.success is True
        assert result.data == "new_file.txt"

    def test_disambiguates_on_collision(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        (temp_dir / "taken.txt").write_text("x")
        result = service.get_unique_filename(temp_dir, "taken.txt")
        assert result.success is True
        assert result.data != "taken.txt"

    def test_error_path_returns_failed_result(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        # Real, reachable error: _get_unique_filename raises ValueError on an
        # empty filename (core/fs/_internal/file_ops.py) -- no faking required.
        result = service.get_unique_filename(temp_dir, "")
        assert result.success is False
        assert result.error


class TestCreateTempFile:
    def test_creates_file_in_explicit_directory(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        result = service.create_temp_file(suffix=".log", directory=temp_dir)
        assert result.success is True
        assert result.data is not None
        created = Path(result.data)
        assert created.exists()
        assert created.suffix == ".log"
        assert created.parent == temp_dir.resolve()

    def test_defaults_to_quack_tmp_under_base_dir(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        result = service.create_temp_file()
        assert result.success is True
        assert result.data is not None
        created = Path(result.data)
        assert created.exists()
        assert created.parent == (temp_dir.resolve() / ".quack" / "tmp")

    def test_error_path_directory_is_a_file_not_a_dir(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        blocker = temp_dir / "im_a_file"
        blocker.write_text("x")
        # tempfile.mkstemp(dir=<a regular file>) raises NotADirectoryError --
        # a real, reachable OS-level failure, not a faked one.
        result = service.create_temp_file(directory=blocker)
        assert result.success is False
        assert result.error


class TestCreateTempDirectory:
    def test_creates_directory_in_explicit_directory(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        result = service.create_temp_directory(prefix="mytest_", directory=temp_dir)
        assert result.success is True
        assert result.data is not None
        created = Path(result.data)
        assert created.is_dir()
        assert created.name.startswith("mytest_")

    def test_defaults_to_quack_tmp_under_base_dir(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        result = service.create_temp_directory()
        assert result.success is True
        assert result.data is not None
        created = Path(result.data)
        assert created.is_dir()
        assert created.parent == (temp_dir.resolve() / ".quack" / "tmp")

    def test_error_path_directory_is_a_file_not_a_dir(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        blocker = temp_dir / "im_a_file"
        blocker.write_text("x")
        # tempfile.mkdtemp(dir=<a regular file>) raises NotADirectoryError --
        # a real, reachable OS-level failure, not a faked one.
        result = service.create_temp_directory(directory=blocker)
        assert result.success is False
        assert result.error


class TestFindFilesByContent:
    def test_finds_matching_file(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        (temp_dir / "hit.txt").write_text("contains needle here")
        (temp_dir / "miss.txt").write_text("nothing relevant")
        result = service.find_files_by_content(temp_dir, "needle")
        assert result.success is True
        assert result.data is not None
        assert any("hit.txt" in p for p in result.data)
        assert not any("miss.txt" in p for p in result.data)

    def test_no_matches_returns_empty_list(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        (temp_dir / "plain.txt").write_text("plain content")
        result = service.find_files_by_content(temp_dir, "not-present-anywhere")
        assert result.success is True
        assert result.data == []

    def test_error_path_returns_failed_result(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        missing = temp_dir / "does-not-exist-dir"
        result = service.find_files_by_content(missing, "x")
        assert result.success is False
        assert result.error


class TestGetDiskUsage:
    def test_returns_usage_dict(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        result = service.get_disk_usage(temp_dir)
        assert result.success is True
        assert isinstance(result.data, dict)
        assert "total" in result.data
        assert "used" in result.data
        assert "free" in result.data


class TestGetFileType:
    def test_regular_file(self, test_file: Path) -> None:
        service = FileSystemService(base_dir=test_file.parent)
        result = service.get_file_type(test_file)
        assert result.success is True
        assert result.data == "file"

    def test_directory(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        result = service.get_file_type(temp_dir)
        assert result.success is True
        assert result.data == "directory"

    def test_error_path_sandbox_escape_returns_failed_result(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)
        # _normalize_input_path enforces sandboxing (service/base.py) -- a
        # real absolute path outside base_dir raises a real sandbox error,
        # not a faked one.
        result = service.get_file_type(Path("/etc/passwd"))
        assert result.success is False
        assert result.error


class TestGetFileSizeStr:
    def test_bytes_formatted_human_readable(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        result = service.get_file_size_str(1536)
        assert result.success is True
        assert isinstance(result.data, str)
        assert result.data  # non-empty formatted string

    def test_zero_bytes(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        result = service.get_file_size_str(0)
        assert result.success is True

    def test_negative_bytes_real_defensive_branch(self, temp_dir: Path) -> None:
        # _get_file_size_str's own real (non-exceptional) defensive branch:
        # size_bytes < 0 returns "0 B" rather than raising.
        service = FileSystemService(base_dir=temp_dir)
        result = service.get_file_size_str(-5)
        assert result.success is True
        assert result.data == "0 B"


class TestGetMimeType:
    def test_text_file(self, test_file: Path) -> None:
        service = FileSystemService(base_dir=test_file.parent)
        result = service.get_mime_type(test_file)
        assert result.success is True
        # text/plain is the expected real mimetypes.guess_type() result for .txt
        assert result.data == "text/plain"

    def test_error_path_sandbox_escape_returns_failed_result(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)
        result = service.get_mime_type(Path("/etc/passwd"))
        assert result.success is False
        assert result.error


class TestGetFileTimestamp:
    def test_returns_positive_float(self, test_file: Path) -> None:
        service = FileSystemService(base_dir=test_file.parent)
        result = service.get_file_timestamp(test_file)
        assert result.success is True
        assert isinstance(result.data, float)
        assert result.data > 0

    def test_error_path_returns_failed_result(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        result = service.get_file_timestamp(temp_dir / "nonexistent.txt")
        assert result.success is False
        assert result.error


class TestComputeChecksum:
    def test_sha256_matches_known_value(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f = temp_dir / "checksum_me.txt"
        f.write_text("hello world")
        result = service.compute_checksum(f, algorithm="sha256")
        assert result.success is True
        # Real, independently-known SHA-256 of the literal bytes "hello world"
        # (verified via stdlib hashlib.sha256(b"hello world").hexdigest()).
        assert (
            result.data
            == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        )

    def test_error_path_returns_failed_result(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        result = service.compute_checksum(temp_dir / "nonexistent.txt")
        assert result.success is False
        assert result.error


class TestIsPathWriteable:
    def test_existing_writeable_directory(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        result = service.is_path_writeable(temp_dir)
        assert result.success is True
        assert result.data is True
        assert result.meta is not None
        assert result.meta.get("side_effect") == "write_probe"


class TestIsFileLocked:
    def test_regular_unlocked_file(self, test_file: Path) -> None:
        service = FileSystemService(base_dir=test_file.parent)
        result = service.is_file_locked(test_file)
        assert result.success is True
        assert result.data is False


class TestAtomicWrite:
    def test_writes_text_content(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        target = temp_dir / "atomic.txt"
        result = service.atomic_write(target, "hello atomic world")
        assert result.success is True
        assert target.read_text() == "hello atomic world"
        assert result.bytes_written == len(b"hello atomic world")

    def test_writes_binary_content(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        target = temp_dir / "atomic.bin"
        payload = b"\x00\x01\x02binary"
        result = service.atomic_write(target, payload)
        assert result.success is True
        assert target.read_bytes() == payload
        assert result.bytes_written == len(payload)

    def test_error_path_returns_failed_result(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        # Writing to a path whose parent doesn't exist and can't be created
        # (parent is itself a file, not a directory) forces the except branch.
        blocker = temp_dir / "im_a_file"
        blocker.write_text("x")
        target = blocker / "cant_write_here.txt"
        result = service.atomic_write(target, "content")
        assert result.success is False
        assert result.error
