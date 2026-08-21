"""
Tests for zeo_core.core.fs.service.standalone — the module-level convenience
wrappers that delegate to the process-wide `get_service()` singleton.

quackverse-coverage-90: this module carried 57% coverage (43/100 stmts missed)
before this file, with no dedicated test anywhere despite being a real, used
public-surface module (every function here is a one-line delegation to the
FileSystemService singleton, not dead code or a re-export shim).

get_service() is `functools.lru_cache`d and defaults `base_dir` to CWD — so
every test here uses `monkeypatch.chdir(tmp_path)` to point the singleton at
an isolated real directory, and clears the cache before/after so no test
leaks its chdir'd singleton into another test or another test module. No
mocking of the service itself: the singleton is real, the filesystem calls
are real, only the *directory* is redirected.
"""

import os
import platform
import stat
from collections.abc import Generator
from pathlib import Path

import pytest

from zeo_core.core.fs.service import standalone
from zeo_core.core.fs.service.factory import create_service


@pytest.fixture(autouse=True)
def _isolated_singleton(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[None]:
    """Point the get_service() singleton at a fresh tmp_path for every test."""
    from zeo_core.core.fs.service import get_service

    monkeypatch.chdir(tmp_path)
    get_service.cache_clear()
    yield
    get_service.cache_clear()


class TestReadWriteText:
    def test_write_then_read_text(self, tmp_path: Path) -> None:
        target = tmp_path / "note.txt"
        write_result = standalone.write_text(target, "hello standalone")
        assert write_result.success is True
        read_result = standalone.read_text(target)
        assert read_result.success is True
        assert read_result.content == "hello standalone"


class TestReadWriteBytes:
    def test_write_then_read_bytes(self, tmp_path: Path) -> None:
        target = tmp_path / "data.bin"
        payload = b"\x00\x01binarydata"
        write_result = standalone.write_bytes(target, payload)
        assert write_result.success is True
        read_result = standalone.read_bytes(target)
        assert read_result.success is True
        assert read_result.content == payload

    def test_legacy_aliases_point_at_same_functions(self) -> None:
        assert standalone.read_binary is standalone.read_bytes
        assert standalone.write_binary is standalone.write_bytes


class TestReadWriteLines:
    def test_write_then_read_lines(self, tmp_path: Path) -> None:
        target = tmp_path / "lines.txt"
        write_result = standalone.write_lines(target, ["one", "two", "three"])
        assert write_result.success is True
        read_result = standalone.read_lines(target)
        assert read_result.success is True
        assert read_result.content == ["one", "two", "three"]


class TestCopyMove:
    def test_copy_creates_second_file_with_same_content(self, tmp_path: Path) -> None:
        src = tmp_path / "src.txt"
        src.write_text("copy me")
        dst = tmp_path / "dst.txt"
        result = standalone.copy(src, dst)
        assert result.success is True
        assert dst.read_text() == "copy me"
        assert src.exists()  # copy leaves the source in place

    def test_move_relocates_file(self, tmp_path: Path) -> None:
        src = tmp_path / "src.txt"
        src.write_text("move me")
        dst = tmp_path / "moved.txt"
        result = standalone.move(src, dst)
        assert result.success is True
        assert dst.read_text() == "move me"
        assert not src.exists()

    def test_copy_safely_delegates_to_copy(self, tmp_path: Path) -> None:
        src = tmp_path / "src.txt"
        src.write_text("safe copy")
        dst = tmp_path / "dst_safe.txt"
        result = standalone.copy_safely(src, dst)
        assert result.success is True
        assert dst.read_text() == "safe copy"

    def test_move_safely_delegates_to_move(self, tmp_path: Path) -> None:
        src = tmp_path / "src.txt"
        src.write_text("safe move")
        dst = tmp_path / "dst_safe_move.txt"
        result = standalone.move_safely(src, dst)
        assert result.success is True
        assert dst.read_text() == "safe move"
        assert not src.exists()


class TestDelete:
    def test_delete_removes_existing_file(self, tmp_path: Path) -> None:
        target = tmp_path / "gone.txt"
        target.write_text("x")
        result = standalone.delete(target)
        assert result.success is True
        assert not target.exists()

    def test_delete_safely_delegates_to_delete(self, tmp_path: Path) -> None:
        target = tmp_path / "gone2.txt"
        target.write_text("x")
        result = standalone.delete_safely(target)
        assert result.success is True
        assert not target.exists()


class TestDirectoryOperations:
    def test_create_directory_then_list(self, tmp_path: Path) -> None:
        new_dir = tmp_path / "subdir"
        create_result = standalone.create_directory(new_dir)
        assert create_result.success is True
        assert new_dir.is_dir()

        (new_dir / "a.txt").write_text("a")
        (new_dir / "b.txt").write_text("b")
        list_result = standalone.list_directory(new_dir)
        assert list_result.success is True

    def test_ensure_directory_is_idempotent(self, tmp_path: Path) -> None:
        target = tmp_path / "ensured"
        r1 = standalone.ensure_directory(target)
        r2 = standalone.ensure_directory(target)
        assert r1.success is True
        assert r2.success is True
        assert target.is_dir()

    def test_find_files_by_pattern(self, tmp_path: Path) -> None:
        (tmp_path / "match.txt").write_text("x")
        (tmp_path / "skip.md").write_text("x")
        result = standalone.find_files(tmp_path, "*.txt")
        assert result.success is True


class TestFileInfo:
    def test_get_file_info_for_real_file(self, tmp_path: Path) -> None:
        target = tmp_path / "info.txt"
        target.write_text("info content")
        result = standalone.get_file_info(target)
        assert result.success is True


class TestYamlJsonRoundtrip:
    def test_write_then_read_yaml(self, tmp_path: Path) -> None:
        target = tmp_path / "conf.yaml"
        data = {"a": 1, "b": [1, 2, 3]}
        write_result = standalone.write_yaml(target, data)
        assert write_result.success is True
        read_result = standalone.read_yaml(target)
        assert read_result.success is True
        assert read_result.data == data

    def test_write_then_read_json(self, tmp_path: Path) -> None:
        target = tmp_path / "conf.json"
        data = {"x": "y", "n": 42}
        write_result = standalone.write_json(target, data)
        assert write_result.success is True
        read_result = standalone.read_json(target)
        assert read_result.success is True
        assert read_result.data == data


@pytest.mark.skipif(platform.system() == "Windows", reason="POSIX file modes only")
class TestWriteJsonMode:
    """Regression coverage for the `mode:` parameter added to the fs write
    path (config-secrets-hardening charter item 3 / RULING-356 s4.4 item 4).

    The real defect: `_atomic_write` preserved a pre-existing loose file mode
    forever and never tightened it, and the non-atomic branch (`open()`) was
    umask-governed and could land a new file at 0644. `mode=` closes both --
    covered here via `standalone.write_json`, the entry point the three
    credential writers (google/notion/github auth.py) actually call. All
    writes land inside `tmp_path`, which `_isolated_singleton` above points
    the fs service's `base_dir` at, so `allow_absolute=False` never fires.
    """

    def test_mode_none_preserves_default_atomic_new_file_mode(
        self, tmp_path: Path
    ) -> None:
        """Regression guard: omitting `mode` must not change existing
        behaviour -- a brand-new file written atomically is already born
        0600 by construction (mkstemp), with no explicit mode passed."""
        target = tmp_path / "no_mode.json"
        result = standalone.write_json(target, {"token": "x"}, atomic=True)
        assert result.success is True
        assert stat.S_IMODE(target.stat().st_mode) == 0o600

    def test_mode_0600_applied_on_atomic_write(self, tmp_path: Path) -> None:
        target = tmp_path / "creds_atomic.json"
        result = standalone.write_json(
            target, {"token": "secret"}, atomic=True, mode=0o600
        )
        assert result.success is True
        assert stat.S_IMODE(target.stat().st_mode) == 0o600

    def test_mode_0600_applied_on_non_atomic_write(self, tmp_path: Path) -> None:
        """Covers the branch the charter calls out explicitly: atomic=False
        routes through plain open() and is umask-governed (probed at 0644
        under umask 0o022 with no explicit mode) -- a fix covering only the
        atomic branch ships with this hole open."""
        old_umask = os.umask(0o022)
        try:
            target = tmp_path / "creds_nonatomic.json"
            result = standalone.write_json(
                target, {"token": "secret"}, atomic=False, mode=0o600
            )
        finally:
            os.umask(old_umask)
        assert result.success is True
        assert stat.S_IMODE(target.stat().st_mode) == 0o600

    def test_mode_0600_tightens_a_preexisting_loose_file(self, tmp_path: Path) -> None:
        """The actual bug fixed: _atomic_write used to PRESERVE a pre-existing
        loose mode forever on every overwrite. A credential file that somehow
        landed at 0644 (e.g. written before this fix, or copied in) must be
        tightened to 0600 the next time a credential writer saves to it --
        not have its looseness re-blessed."""
        target = tmp_path / "loose_creds.json"
        target.write_text("{}")
        os.chmod(target, 0o644)
        assert stat.S_IMODE(target.stat().st_mode) == 0o644

        result = standalone.write_json(
            target, {"token": "refreshed"}, atomic=True, mode=0o600
        )
        assert result.success is True
        assert stat.S_IMODE(target.stat().st_mode) == 0o600

    def test_mode_none_still_preserves_a_preexisting_loose_file(
        self, tmp_path: Path
    ) -> None:
        """Control for the above: general-purpose callers that never pass
        `mode` (pandoc/jupytext/gmail output) must keep the OLD
        preserve-current semantics unchanged -- this fix must not become a
        blanket 0600 floor."""
        target = tmp_path / "unrelated_output.json"
        target.write_text("{}")
        os.chmod(target, 0o644)

        result = standalone.write_json(target, {"data": "not a secret"}, atomic=True)
        assert result.success is True
        assert stat.S_IMODE(target.stat().st_mode) == 0o644


class TestPathHelpers:
    def test_split_path(self, tmp_path: Path) -> None:
        result = standalone.split_path(tmp_path / "a" / "b")
        assert result.success is True
        assert result.data is not None
        assert "a" in result.data
        assert "b" in result.data

    def test_join_path(self, tmp_path: Path) -> None:
        # Real behavior: join_path resolves relative parts against the
        # service's base_dir (sandboxing), not a bare os.path.join -- the
        # _isolated_singleton fixture already chdir'd to tmp_path.
        result = standalone.join_path("a", "b", "c")
        assert result.success is True
        assert result.data == str(tmp_path.resolve() / "a" / "b" / "c")

    def test_normalize_path(self, tmp_path: Path) -> None:
        result = standalone.normalize_path(tmp_path)
        assert result.success is True

    def test_normalize_path_with_info(self, tmp_path: Path) -> None:
        result = standalone.normalize_path_with_info(tmp_path)
        assert result.success is True

    def test_get_path_info_delegates_to_normalize_path_with_info(
        self, tmp_path: Path
    ) -> None:
        result = standalone.get_path_info(tmp_path)
        assert result.success is True

    def test_expand_user_vars(self) -> None:
        result = standalone.expand_user_vars("~/somewhere")
        assert result.success is True

    def test_get_extension(self, tmp_path: Path) -> None:
        result = standalone.get_extension(tmp_path / "file.tar.gz")
        assert result.success is True
        assert result.data == "gz"

    def test_resolve_path(self, tmp_path: Path) -> None:
        result = standalone.resolve_path(tmp_path / "x")
        assert result.success is True

    def test_is_same_file_true_for_identical_path(self, tmp_path: Path) -> None:
        f = tmp_path / "same.txt"
        f.write_text("x")
        result = standalone.is_same_file(f, f)
        assert result.success is True
        assert result.data is True

    def test_is_subdirectory_true_case(self, tmp_path: Path) -> None:
        child = tmp_path / "child"
        child.mkdir()
        result = standalone.is_subdirectory(child, tmp_path)
        assert result.success is True
        assert result.data is True

    def test_path_exists_true_and_false(self, tmp_path: Path) -> None:
        # BoolResult carries its payload on .value, not .data (DataResult's
        # field name) -- confirmed against the real pydantic model shape.
        existing = tmp_path / "here.txt"
        existing.write_text("x")
        assert standalone.path_exists(existing).value is True
        assert standalone.path_exists(tmp_path / "not-here.txt").value is False

    def test_is_valid_path(self, tmp_path: Path) -> None:
        result = standalone.is_valid_path(tmp_path / "anything.txt")
        assert result.success is True

    def test_is_safe_path(self, tmp_path: Path) -> None:
        result = standalone.is_safe_path(tmp_path / "safe.txt")
        assert result.success is True


class TestUtilityDelegations:
    """
    Every one of these mirrors a UtilityOperationsMixin method already given
    deep behavioral coverage in test_utility_operations.py -- here the
    assertion is specifically that the STANDALONE wrapper reaches the real
    singleton service and gets a real result back, not re-proving each
    method's full internal behavior a second time.
    """

    def test_get_unique_filename(self, tmp_path: Path) -> None:
        result = standalone.get_unique_filename(tmp_path, "x.txt")
        assert result.success is True

    def test_create_temp_file(self, tmp_path: Path) -> None:
        result = standalone.create_temp_file(directory=tmp_path)
        assert result.success is True
        assert result.data is not None
        assert Path(result.data).exists()

    def test_create_temp_directory(self, tmp_path: Path) -> None:
        result = standalone.create_temp_directory()
        assert result.success is True
        assert result.data is not None
        assert Path(result.data).is_dir()

    def test_find_files_by_content(self, tmp_path: Path) -> None:
        (tmp_path / "needle.txt").write_text("has the needle in it")
        result = standalone.find_files_by_content(tmp_path, "needle")
        assert result.success is True
        assert result.data is not None
        assert any("needle.txt" in p for p in result.data)

    def test_get_disk_usage(self, tmp_path: Path) -> None:
        result = standalone.get_disk_usage(tmp_path)
        assert result.success is True

    def test_get_file_type(self, tmp_path: Path) -> None:
        result = standalone.get_file_type(tmp_path)
        assert result.success is True
        assert result.data == "directory"

    def test_get_file_size_str(self) -> None:
        result = standalone.get_file_size_str(2048)
        assert result.success is True

    def test_get_file_timestamp(self, tmp_path: Path) -> None:
        f = tmp_path / "t.txt"
        f.write_text("x")
        result = standalone.get_file_timestamp(f)
        assert result.success is True

    def test_get_mime_type(self, tmp_path: Path) -> None:
        f = tmp_path / "t.txt"
        f.write_text("x")
        result = standalone.get_mime_type(f)
        assert result.success is True
        assert result.data == "text/plain"

    def test_compute_checksum(self, tmp_path: Path) -> None:
        f = tmp_path / "t.txt"
        f.write_text("checksum content")
        result = standalone.compute_checksum(f)
        assert result.success is True

    def test_is_path_writeable(self, tmp_path: Path) -> None:
        result = standalone.is_path_writeable(tmp_path)
        assert result.success is True

    def test_is_file_locked(self, tmp_path: Path) -> None:
        f = tmp_path / "t.txt"
        f.write_text("x")
        result = standalone.is_file_locked(f)
        assert result.success is True

    def test_atomic_write(self, tmp_path: Path) -> None:
        target = tmp_path / "atomic_standalone.txt"
        result = standalone.atomic_write(target, "atomic content")
        assert result.success is True
        assert target.read_text() == "atomic content"


class TestCreateServiceFactory:
    """create_service() itself (service/factory.py) — exercised here since a
    standalone-wrapper test file is exactly where its real usage pattern
    (constructing a service without the singleton) belongs."""

    def test_create_service_with_explicit_base_dir(self, tmp_path: Path) -> None:
        service = create_service(base_dir=tmp_path)
        assert service.base_dir == tmp_path.resolve()

    def test_create_service_defaults_to_cwd(self, tmp_path: Path) -> None:
        # _isolated_singleton already chdir'd to tmp_path for this test.
        service = create_service()
        assert service.base_dir == tmp_path.resolve()
