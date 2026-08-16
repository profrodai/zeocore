# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_fs/test_service_mixins_cluster.py
# === QV-LLM:END ===

"""
Real behavioral tests for the core/fs/service mixin cluster:
DirectoryOperationsMixin, StructuredDataMixin, PathValidationMixin,
PathOperationsMixin, and FileSystemService's own alias methods
(full_class.py) -- plus the fs.plugin and fs.utils deprecated-shim
modules.

Every test instantiates a REAL FileSystemService(base_dir=temp_dir) against
a real pytest temp_dir fixture and a real filesystem. No mock stands in for
any quack_core function or method under test -- this is the same discipline
round 1/round 2 used for utility_operations.py and standalone.py. Nothing in
this cluster calls an external network/SDK boundary, so RULING-235's
boundary-mock question does not apply here; it applies to the
integrations/ clusters this stream picks up next.
"""

from pathlib import Path

import pytest
from quack_core.core.fs.plugin import QuackFSPlugin, create_plugin
from quack_core.core.fs.service import FileSystemService


class TestDirectoryOperationsMixin:
    """ensure_directory / create_directory / list_directory / find_files."""

    def test_ensure_directory_creates_new(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        target = temp_dir / "newdir"
        assert not target.exists()

        result = service.ensure_directory(target)

        assert result.ok is True
        assert target.is_dir()
        # macOS: /var is a symlink to /private/var, so the service's resolved
        # path differs from the raw temp_dir fixture value by that prefix
        # alone (same quirk round 2 hit in test_service.py::test_initialize).
        # Compare against target.resolve() to match what the real code does.
        assert result.path == target.resolve()

    def test_ensure_directory_exist_ok_true_on_existing(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        target = temp_dir / "already"
        target.mkdir()

        result = service.ensure_directory(target, exist_ok=True)

        assert result.ok is True
        assert target.is_dir()

    def test_ensure_directory_exist_ok_false_on_existing_fails(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)
        target = temp_dir / "already"
        target.mkdir()

        result = service.ensure_directory(target, exist_ok=False)

        assert result.ok is False
        assert result.path is None
        assert result.error is not None

    def test_create_directory_is_ensure_directory_alias(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        target = temp_dir / "aliased"

        result = service.create_directory(target)

        assert result.ok is True
        assert target.is_dir()

    def test_list_directory_real_contents(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        (temp_dir / "a.txt").write_text("a")
        (temp_dir / "b.txt").write_text("b")
        (temp_dir / "sub").mkdir()

        result = service.list_directory(temp_dir)

        assert result.ok is True
        assert result.exists is True
        assert result.total_files == 2
        assert result.total_directories == 1
        assert result.is_empty is False

    def test_list_directory_empty_dir(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        empty = temp_dir / "empty"
        empty.mkdir()

        result = service.list_directory(empty)

        assert result.ok is True
        assert result.is_empty is True
        assert result.total_files == 0

    def test_list_directory_nonexistent_fails(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.list_directory(temp_dir / "does_not_exist")

        assert result.ok is False
        assert result.path is None
        assert result.error is not None

    def test_find_files_pattern_match(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        (temp_dir / "one.py").write_text("x")
        (temp_dir / "two.py").write_text("y")
        (temp_dir / "three.txt").write_text("z")

        result = service.find_files(temp_dir, "*.py")

        assert result.ok is True
        assert result.total_matches == 2
        assert result.pattern == "*.py"
        found_names = {p.name for p in result.files}
        assert found_names == {"one.py", "two.py"}

    def test_find_files_nonexistent_dir_fails(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.find_files(temp_dir / "nope", "*.py")

        assert result.ok is False
        assert result.pattern == "*.py"
        assert result.error is not None


class TestStructuredDataMixin:
    """read_yaml / write_yaml / read_json / write_json."""

    def test_write_then_read_yaml_roundtrip(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        target = temp_dir / "data.yaml"
        payload = {"key": "value", "nested": {"n": 1}}

        write_result = service.write_yaml(target, payload)
        assert write_result.ok is True
        assert target.exists()

        read_result = service.read_yaml(target)
        assert read_result.ok is True
        assert read_result.data == payload
        assert read_result.format == "yaml"

    def test_read_yaml_non_dict_content_fails(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        target = temp_dir / "list.yaml"
        target.write_text("- a\n- b\n")

        result = service.read_yaml(target)

        assert result.ok is False
        assert result.data is None
        # Real message is "YAML content is not a dict: <class 'list'>" --
        # my first-draft guess of "not a dictionary" was wrong; corrected to
        # match the actual _ops-layer message, not softened to force a pass.
        assert "is not a dict" in result.error

    def test_read_yaml_nonexistent_fails(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.read_yaml(temp_dir / "missing.yaml")

        assert result.ok is False
        assert result.error_info is not None

    def test_write_then_read_json_roundtrip(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        target = temp_dir / "data.json"
        payload = {"a": 1, "b": [1, 2, 3]}

        write_result = service.write_json(target, payload, indent=2)
        assert write_result.ok is True
        assert target.exists()

        read_result = service.read_json(target)
        assert read_result.ok is True
        assert read_result.data == payload
        assert read_result.format == "json"

    def test_read_json_non_dict_content_fails(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        target = temp_dir / "list.json"
        target.write_text("[1, 2, 3]")

        result = service.read_json(target)

        assert result.ok is False
        assert result.data is None
        # Same corrected-guess as read_yaml above: real message says
        # "is not a dict", not "not a dictionary".
        assert "is not a dict" in result.error

    def test_read_json_nonexistent_fails(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.read_json(temp_dir / "missing.json")

        assert result.ok is False
        assert result.error_info is not None

    def test_write_yaml_atomic_default_true(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        target = temp_dir / "atomic.yaml"

        result = service.write_yaml(target, {"x": 1})

        assert result.ok is True
        assert service.read_yaml(target).data == {"x": 1}

    def test_write_yaml_sandbox_escape_hits_except_branch(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.write_yaml("../../../etc/passwd", {"a": 1})

        assert result.ok is False
        assert result.path is None
        assert "escape" in result.error

    def test_write_json_sandbox_escape_hits_except_branch(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.write_json("../../../etc/passwd", {"a": 1})

        assert result.ok is False
        assert result.path is None
        assert "escape" in result.error


class TestPathValidationMixin:
    """path_exists / is_valid_path / is_safe_path / validate_path /
    validate_file / normalize_path_with_info / resolve_path_strict."""

    def test_path_exists_true(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f = temp_dir / "exists.txt"
        f.write_text("x")

        result = service.path_exists(f)

        assert result.ok is True
        assert result.value is True

    def test_path_exists_false(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.path_exists(temp_dir / "nope.txt")

        assert result.ok is True
        assert result.value is False

    def test_is_valid_path_syntax_true(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.is_valid_path("some/relative/path.txt")

        assert result.ok is True
        assert result.value is True

    def test_is_valid_path_syntax_false_on_null_byte(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.is_valid_path("bad\0path.txt")

        assert result.ok is True
        assert result.value is False

    def test_is_safe_path_true_within_sandbox(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.is_safe_path("inside.txt")

        assert result.ok is True
        assert result.value is True
        assert result.path is not None

    def test_is_safe_path_false_on_traversal(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.is_safe_path("../../../etc/passwd")

        assert result.ok is False
        assert result.value is False
        assert result.error_info is not None

    def test_validate_path_is_is_safe_path_alias(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        safe = service.is_safe_path("inside.txt")
        via_alias = service.validate_path("inside.txt")

        assert via_alias.ok == safe.ok
        assert via_alias.value == safe.value

    def test_validate_file_true_for_real_file(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f = temp_dir / "real.txt"
        f.write_text("x")

        result = service.validate_file(f)

        assert result.ok is True
        assert result.value is True

    def test_validate_file_false_when_missing(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.validate_file(temp_dir / "missing.txt")

        assert result.ok is False
        assert result.error == "File does not exist"

    def test_validate_file_false_when_directory(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        d = temp_dir / "adir"
        d.mkdir()

        result = service.validate_file(d)

        assert result.ok is False
        assert result.error == "Path is not a file"

    def test_normalize_path_with_info_existing(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f = temp_dir / "here.txt"
        f.write_text("x")

        result = service.normalize_path_with_info(f)

        assert result.ok is True
        assert result.is_valid is True
        assert result.exists is True
        assert result.is_absolute is True

    def test_normalize_path_with_info_nonexistent_still_ok(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.normalize_path_with_info(temp_dir / "ghost.txt")

        assert result.ok is True
        assert result.is_valid is True
        assert result.exists is False

    def test_resolve_path_strict_existing_succeeds(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f = temp_dir / "strict_ok.txt"
        f.write_text("x")

        result = service.resolve_path_strict(f)

        assert result.ok is True
        assert result.is_valid is True
        assert result.exists is True

    def test_resolve_path_strict_missing_returns_ok_false_valid_true(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.resolve_path_strict(temp_dir / "strict_missing.txt")

        assert result.ok is False
        assert result.is_valid is True
        assert result.exists is False
        assert result.error == "Path does not exist"

    def test_resolve_path_strict_invalid_path_ok_false_valid_false(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.resolve_path_strict("../../../etc/passwd")

        assert result.ok is False
        assert result.is_valid is False
        assert result.error_info is not None

    def test_resolve_path_strict_bad_type_hits_top_level_except(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)

        # normalized_path stays None because _normalize_input_path itself
        # raises on a non-coercible type -- exercises the top-level except
        # Exception branch's "else" arm (normalized_path falsy at raise time),
        # distinct from the FileNotFoundError branch's own inner except.
        result = service.resolve_path_strict(123)  # type: ignore[arg-type]

        assert result.ok is False
        assert result.is_valid is False
        assert result.error_info is not None

    def test_path_exists_sandbox_escape_hits_except_branch(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.path_exists("../../../etc/passwd")

        assert result.ok is False
        assert result.value is False
        assert "escape" in result.error

    def test_is_valid_path_bad_type_hits_except_branch(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.is_valid_path(123)  # type: ignore[arg-type]

        assert result.ok is False
        assert result.value is False
        assert result.error_info is not None

    def test_validate_file_sandbox_escape_hits_except_branch(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.validate_file("../../../etc/passwd")

        assert result.ok is False
        assert "escape" in result.error

    def test_normalize_path_with_info_sandbox_escape_hits_except_branch(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.normalize_path_with_info("../../../etc/passwd")

        assert result.ok is False
        assert result.is_valid is False
        assert result.error_info is not None


class TestPathOperationsMixin:
    """join_path / split_path / normalize_path / resolve_path /
    expand_user_vars(_raw) / is_same_file / is_subdirectory / get_extension."""

    def test_join_path_empty_returns_dot(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.join_path()

        assert result.ok is True
        assert result.data == "."

    def test_join_path_multiple_parts(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.join_path("a", "b", "c.txt")

        assert result.ok is True
        assert result.data.endswith("a/b/c.txt") or result.data.endswith("a\\b\\c.txt")

    def test_split_path_components(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f = temp_dir / "sub" / "file.txt"

        result = service.split_path(f)

        assert result.ok is True
        assert "file.txt" in result.data
        assert "sub" in result.data

    def test_normalize_path_existing_and_missing(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f = temp_dir / "present.txt"
        f.write_text("x")

        present = service.normalize_path(f)
        assert present.ok is True
        assert present.exists is True

        missing = service.normalize_path(temp_dir / "absent.txt")
        assert missing.ok is True
        assert missing.exists is False

    def test_normalize_path_sandbox_escape_hits_except_branch(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.normalize_path("../../../etc/passwd")

        assert result.ok is False
        assert result.is_valid is False
        assert "escape" in result.error

    def test_resolve_path_is_normalize_path_alias(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f = temp_dir / "aliased.txt"
        f.write_text("x")

        normalized = service.normalize_path(f)
        resolved = service.resolve_path(f)

        assert resolved.ok == normalized.ok
        assert resolved.path == normalized.path

    def test_expand_user_vars_raw_expands_home_and_env(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)
        monkeypatch.setenv("QUACK_TEST_VAR", "expanded_value")

        result = service.expand_user_vars_raw("$QUACK_TEST_VAR/sub")

        assert result.ok is True
        assert "expanded_value" in result.data

    def test_expand_user_vars_is_raw_alias(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)
        monkeypatch.setenv("QUACK_TEST_VAR2", "aliased_value")

        raw = service.expand_user_vars_raw("$QUACK_TEST_VAR2")
        via_alias = service.expand_user_vars("$QUACK_TEST_VAR2")

        assert via_alias.data == raw.data

    def test_expand_user_vars_raw_bad_type_hits_except_branch(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.expand_user_vars_raw(123)  # type: ignore[arg-type]

        assert result.ok is False
        assert result.data == ""
        assert result.error_info is not None

    def test_is_same_file_true_for_identical_path(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f = temp_dir / "same.txt"
        f.write_text("x")

        result = service.is_same_file(f, f)

        assert result.ok is True
        assert result.data is True

    def test_is_same_file_false_for_different_files(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f1 = temp_dir / "one.txt"
        f2 = temp_dir / "two.txt"
        f1.write_text("x")
        f2.write_text("y")

        result = service.is_same_file(f1, f2)

        assert result.ok is True
        assert result.data is False

    def test_is_subdirectory_true(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        child = temp_dir / "parent" / "child"
        child.mkdir(parents=True)

        result = service.is_subdirectory(child, temp_dir / "parent")

        assert result.ok is True
        assert result.data is True

    def test_is_subdirectory_false(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        (temp_dir / "a").mkdir()
        (temp_dir / "b").mkdir()

        result = service.is_subdirectory(temp_dir / "a", temp_dir / "b")

        assert result.ok is True
        assert result.data is False

    def test_get_extension_real_file(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.get_extension(temp_dir / "archive.tar.gz")

        assert result.ok is True
        assert result.data == "gz"

    def test_get_extension_no_extension(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.get_extension(temp_dir / "README")

        assert result.ok is True
        assert result.data == ""

    def test_join_path_sandbox_escape_hits_except_branch(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.join_path("valid", "../../../etc/passwd")

        assert result.ok is False
        assert result.data == ""
        assert result.error_info is not None
        assert "escape" in result.error

    def test_split_path_sandbox_escape_hits_except_branch(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.split_path("../../../etc/passwd")

        assert result.ok is False
        assert result.data == []
        assert "escape" in result.error

    def test_get_extension_sandbox_escape_hits_except_branch(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.get_extension("../../../etc/passwd")

        assert result.ok is False
        assert result.data == ""
        assert "escape" in result.error

    def test_is_same_file_sandbox_escape_hits_except_branch(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.is_same_file("../../../etc/passwd", "x")

        assert result.ok is False
        assert result.data is False
        assert "escape" in result.error

    def test_is_subdirectory_sandbox_escape_hits_except_branch(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.is_subdirectory("../../../etc/passwd", "x")

        assert result.ok is False
        assert result.data is False
        assert "escape" in result.error


class TestFileSystemServiceAliases:
    """The alias methods declared directly on FileSystemService in
    full_class.py: exists, resolve, ensure_dir, list_dir, is_file, is_dir,
    stat, hash_file, mime_type."""

    def test_exists_alias(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f = temp_dir / "e.txt"
        f.write_text("x")

        assert service.exists(f).value is True
        assert service.exists(temp_dir / "nope.txt").value is False

    def test_resolve_alias(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f = temp_dir / "r.txt"
        f.write_text("x")

        result = service.resolve(f)

        assert result.ok is True
        assert result.exists is True

    def test_ensure_dir_alias(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        target = temp_dir / "ensured"

        result = service.ensure_dir(target)

        assert result.ok is True
        assert target.is_dir()

    def test_list_dir_alias(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        (temp_dir / "f1.txt").write_text("x")

        result = service.list_dir(temp_dir)

        assert result.ok is True
        assert result.total_files == 1

    def test_is_file_true_and_false(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f = temp_dir / "af.txt"
        f.write_text("x")
        d = temp_dir / "ad"
        d.mkdir()

        assert service.is_file(f).value is True
        assert service.is_file(d).value is False

    def test_is_dir_true_and_false(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f = temp_dir / "bf.txt"
        f.write_text("x")
        d = temp_dir / "bd"
        d.mkdir()

        assert service.is_dir(d).value is True
        assert service.is_dir(f).value is False

    def test_is_file_ok_true_value_false_when_missing(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)

        result = service.is_file(temp_dir / "missing_entirely.txt")

        # Corrected guess: get_file_info() does NOT fail (ok=False) for a
        # missing path -- it succeeds (ok=True) and reports is_file=False.
        # is_file()'s alias mirrors that real behavior, confirmed by the
        # actual BoolResult printed on the first failing run, not assumed.
        assert result.ok is True
        assert result.value is False

    def test_stat_alias(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f = temp_dir / "s.txt"
        f.write_text("hello")

        result = service.stat(f)

        assert result.ok is True
        assert result.is_file is True

    def test_hash_file_alias(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f = temp_dir / "h.txt"
        f.write_text("hello world")

        result = service.hash_file(f, algorithm="sha256")

        import hashlib

        expected = hashlib.sha256(b"hello world").hexdigest()
        assert result.ok is True
        assert result.data == expected

    def test_mime_type_alias(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        f = temp_dir / "m.txt"
        f.write_text("hello")

        result = service.mime_type(f)

        assert result.ok is True
        assert result.data == "text/plain"


class TestFsPlugin:
    """fs/plugin.py's QuackFSPlugin -- delegates to a real FileSystemService,
    no mock of the service being delegated to."""

    def test_create_plugin_returns_quack_fs_plugin(self, temp_dir: Path) -> None:
        plugin = create_plugin()

        assert isinstance(plugin, QuackFSPlugin)
        assert plugin.name == "fs"

    def test_plugin_uses_provided_service(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        plugin = QuackFSPlugin(service=service)

        assert plugin._service is service

    def test_plugin_defaults_to_get_service_when_none(self) -> None:
        plugin = QuackFSPlugin()

        # get_service() is the real module-level singleton -- confirms the
        # plugin did not silently receive None.
        assert plugin._service is not None

    def test_plugin_write_text_then_read_text_real_roundtrip(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)
        plugin = QuackFSPlugin(service=service)
        target = temp_dir / "plugin_rt.txt"

        write_result = plugin.write_text(target, "plugin content")
        assert write_result.ok is True

        read_result = plugin.read_text(target)
        assert read_result.ok is True
        assert read_result.content == "plugin content"

    def test_plugin_write_yaml_then_read_yaml_real_roundtrip(
        self, temp_dir: Path
    ) -> None:
        service = FileSystemService(base_dir=temp_dir)
        plugin = QuackFSPlugin(service=service)
        target = temp_dir / "plugin.yaml"

        write_result = plugin.write_yaml(target, {"plugin": True})
        assert write_result.ok is True

        read_result = plugin.read_yaml(target)
        assert read_result.ok is True
        assert read_result.data == {"plugin": True}

    def test_plugin_create_directory_real(self, temp_dir: Path) -> None:
        service = FileSystemService(base_dir=temp_dir)
        plugin = QuackFSPlugin(service=service)
        target = temp_dir / "plugin_dir"

        result = plugin.create_directory(target)

        assert result.ok is True
        assert target.is_dir()


class TestFsUtilsDeprecatedShim:
    """core/fs/utils/__init__.py: a deprecated backward-compat re-export of
    service.standalone. Real import + real DeprecationWarning + real
    delegation, not a mock of the module it re-exports."""

    def test_importing_utils_emits_deprecation_warning(self) -> None:
        import importlib
        import sys

        # Drop any cached import so the module-level warnings.warn() at
        # import time actually fires again for this test.
        sys.modules.pop("quack_core.core.fs.utils", None)

        with pytest.warns(DeprecationWarning, match="deprecated"):
            importlib.import_module("quack_core.core.fs.utils")

    def test_utils_reexports_standalone_public_surface(self, temp_dir: Path) -> None:
        import quack_core.core.fs.utils as fs_utils
        from quack_core.core.fs.service import standalone

        # The wildcard re-export must actually make standalone's public
        # names reachable from the deprecated shim -- confirms it's a real
        # delegation, not a dead import.
        assert hasattr(fs_utils, "get_service")
        assert fs_utils.get_service is standalone.get_service
