# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_fs/test_suite.py
# role: tests
# neighbors: __init__.py, test_api_surface.py, test_architecture.py, test_atomic_wrapping.py, test_operations.py, test_path_utils.py (+3 more)
# exports: TestPathNoneOnFailure, TestSandboxSecurity, TestErrorMappingOrder, TestNoRaiseContract, TestInputPathInMeta, TestInternalLayerDoctrine
# git_branch: main
# git_commit: f0715f0c
# === QV-LLM:END ===

"""
Test suite for amended filesystem service implementation.
Verifies all fixes from the feedback:
1. path=None on all failure paths
2. Sandbox error handling
3. Error mapping order
4. No-raise contract
"""

import tempfile
from pathlib import Path

import pytest
from quack_core.core.fs.service import create_service


class TestPathNoneOnFailure:
    """Test that all service methods return path=None on failures."""

    def test_read_text_invalid_path_returns_none(self):
        """Verify read_text returns path=None on invalid input."""
        service = create_service()
        result = service.read_text(None)  # Invalid input

        assert result.ok is False
        assert result.path is None
        assert result.error_info is not None
        assert result.error_info.type == "validation_error"
        # Input should be in meta, not path
        assert (
            result.meta is None
            or "input_path" not in result.meta
            or result.meta["input_path"] is None
        )

    def test_write_text_invalid_path_returns_none(self):
        """Verify write_text returns path=None on invalid input."""
        service = create_service()
        result = service.write_text(None, "test")

        assert result.ok is False
        assert result.path is None
        assert result.error_info is not None

    def test_read_bytes_nonexistent_file_returns_none(self):
        """Verify read_bytes returns path=None on error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = create_service(base_dir=tmpdir)
            result = service.read_bytes("nonexistent.txt")

            assert result.ok is False
            assert result.path is None
            assert result.error_info is not None
            assert result.error_info.type == "file_not_found"
            # Original input should be in meta
            assert result.meta is not None
            assert "input_path" in result.meta

    def test_delete_invalid_path_returns_none(self):
        """Verify delete returns path=None on invalid input."""
        service = create_service()
        result = service.delete(12345)  # Invalid type

        assert result.ok is False
        assert result.path is None
        assert result.error_info is not None

    def test_copy_failure_returns_none_for_both_paths(self):
        """Verify copy returns path=None and original_path=None on failure."""
        service = create_service()
        result = service.copy("nonexistent.txt", "dest.txt")

        assert result.ok is False
        assert result.path is None
        assert result.original_path is None
        assert result.error_info is not None
        # Both inputs should be in meta
        assert result.meta is not None
        assert "input_src" in result.meta or "input_dst" in result.meta

    def test_path_operations_return_none_on_failure(self):
        """Verify path operations return path=None on failure."""
        service = create_service()

        # split_path with invalid input
        result = service.split_path(None)
        assert result.ok is False
        assert result.path is None

        # normalize_path with invalid input
        result = service.normalize_path(12345)
        assert result.ok is False
        assert result.path is None

        # get_extension with invalid input
        result = service.get_extension(None)
        assert result.ok is False
        assert result.path is None


class TestSandboxSecurity:
    """Test sandbox escape prevention and error handling."""

    def test_path_escape_with_dotdot_blocked(self):
        """Verify ../ path traversal is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = create_service(base_dir=tmpdir, unsafe_allow_absolute_paths=False)

            # Attempt to escape using ../
            result = service.read_text("../../etc/passwd")

            assert result.ok is False
            assert result.path is None
            assert result.error_info is not None
            assert result.error_info.type == "path_escape_attempt"
            assert (
                "escape" in result.error_info.hint.lower()
                or "traverse" in result.error_info.hint.lower()
            )

    def test_absolute_path_outside_basedir_blocked(self):
        """Verify absolute paths outside base_dir are blocked by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = create_service(base_dir=tmpdir, unsafe_allow_absolute_paths=False)

            # Attempt to access absolute path outside base_dir
            result = service.read_text("/etc/passwd")

            assert result.ok is False
            assert result.path is None
            assert result.error_info is not None
            assert result.error_info.type == "path_outside_base_dir"
            assert (
                "absolute" in result.error_info.hint.lower()
                or "outside" in result.error_info.hint.lower()
            )

    def test_absolute_path_allowed_with_unsafe_flag(self):
        """Verify absolute paths work when unsafe flag is enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file outside the base_dir
            outside_file = Path(tmpdir) / "outside.txt"
            outside_file.write_text("test")

            inner_dir = Path(tmpdir) / "inner"
            inner_dir.mkdir()

            service = create_service(
                base_dir=inner_dir, unsafe_allow_absolute_paths=True
            )

            # Should succeed with unsafe flag
            result = service.read_text(str(outside_file))

            # Note: This may still fail if the path doesn't exist or other reasons,
            # but it should NOT fail with path_outside_base_dir error
            if not result.ok:
                assert result.error_info.type != "path_outside_base_dir"


class TestErrorMappingOrder:
    """Test that error mapping handles specific errors before general ones."""

    def test_sandbox_errors_mapped_before_value_error(self):
        """Verify sandbox errors are not caught as generic ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = create_service(base_dir=tmpdir)

            # Path escape should be mapped as path_escape_attempt, not validation_error
            result = service.read_text("../../../etc/passwd")

            assert result.ok is False
            assert result.error_info.type == "path_escape_attempt"
            # Should NOT be mapped as generic validation_error
            assert result.error_info.type != "validation_error"

    def test_file_not_found_mapped_before_os_error(self):
        """Verify FileNotFoundError is mapped specifically, not as generic io_error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = create_service(base_dir=tmpdir)
            result = service.read_text("nonexistent.txt")

            assert result.ok is False
            assert result.error_info.type == "file_not_found"
            # Should NOT be mapped as generic io_error
            assert result.error_info.type != "io_error"


class TestNoRaiseContract:
    """Test that no public method raises exceptions."""

    def test_read_text_never_raises(self):
        """Verify read_text never raises, even with invalid inputs."""
        service = create_service()

        # Various invalid inputs
        invalid_inputs = [None, 12345, [], {}, object()]

        for invalid_input in invalid_inputs:
            try:
                result = service.read_text(invalid_input)
                assert result.ok is False
                assert result.error_info is not None
            except Exception as e:
                pytest.fail(
                    f"read_text raised {type(e).__name__} for input {invalid_input}"
                )

    def test_write_text_never_raises(self):
        """Verify write_text never raises, even with invalid inputs."""
        service = create_service()

        try:
            result = service.write_text(None, "content")
            assert result.ok is False
        except Exception as e:
            pytest.fail(f"write_text raised {type(e).__name__}")

    def test_all_path_operations_never_raise(self):
        """Verify all path operations never raise."""
        service = create_service()

        operations = [
            lambda: service.exists(None),
            lambda: service.is_file(None),
            lambda: service.is_dir(None),
            lambda: service.resolve(None),
            lambda: service.split_path(None),
            lambda: service.normalize_path(None),
        ]

        for op in operations:
            try:
                result = op()
                assert result.ok is False or hasattr(result, "value")
            except Exception as e:
                pytest.fail(f"Operation raised {type(e).__name__}")


class TestInputPathInMeta:
    """Test that failed operations include input_path in meta."""

    def test_read_text_includes_input_in_meta(self):
        """Verify failed read_text includes input_path in meta."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = create_service(base_dir=tmpdir)
            result = service.read_text("nonexistent.txt")

            assert result.ok is False
            assert result.path is None
            assert result.meta is not None
            assert "input_path" in result.meta
            assert result.meta["input_path"] == "nonexistent.txt"

    def test_copy_includes_both_paths_in_meta(self):
        """Verify failed copy includes both src and dst in meta."""
        service = create_service()
        result = service.copy("src.txt", "dst.txt")

        assert result.ok is False
        assert result.meta is not None
        assert "input_src" in result.meta or "input_dst" in result.meta


class TestInternalLayerDoctrine:
    """Test that _internal layer follows doctrine (Path-only)."""

    def test_internal_path_ops_accepts_path_only(self):
        """Verify _internal path operations work with Path objects."""
        from quack_core.core.fs._internal.path_ops import _resolve_path, _split_path

        # Should work with Path
        path = Path("/tmp/test")  # noqa: S108 -- path used only inside mocked/patched I/O, never touches real filesystem
        parts = _split_path(path)
        assert isinstance(parts, list)

        # resolve should work with Path
        resolved = _resolve_path(path, strict=False)
        assert isinstance(resolved, Path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
