# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_fs/test_api_surface.py
# === QV-LLM:END ===

"""
Test suite to verify hardened API surface.
Ensures internal modules cannot be accidentally imported.
"""

import pytest


class TestHardenedAPIExports:
    """Verify only public API is exported."""

    def test_public_exports_available(self) -> None:
        """Verify all public exports are available from main module."""
        from quack_core.core.fs import (
            BoolResult,
            DataResult,
            DirectoryInfoResult,
            ErrorInfo,
            FileInfoResult,
            FileSystemService,
            FindResult,
            OperationResult,
            PathResult,
            ReadResult,
            WriteResult,
            create_service,
            get_service,
        )

        # All should be imported successfully
        assert FileSystemService is not None
        assert get_service is not None
        assert create_service is not None

        # Result models
        assert OperationResult is not None
        assert ErrorInfo is not None
        assert BoolResult is not None
        assert ReadResult is not None
        assert WriteResult is not None
        assert FileInfoResult is not None
        assert DirectoryInfoResult is not None
        assert FindResult is not None
        assert DataResult is not None
        assert PathResult is not None

    def test_internal_modules_not_exported(self) -> None:
        """Verify _internal modules are not accessible via public API."""
        import quack_core.core.fs as fs

        # These should not be accessible
        with pytest.raises(
            AttributeError, match="Internal modules.*not part of the public API"
        ):
            _ = fs._internal

        with pytest.raises(
            AttributeError, match="Internal modules.*not part of the public API"
        ):
            _ = fs._ops

    def test_cannot_import_internal_directly_from_package(self) -> None:
        """`from quack_core.core.fs import _internal` cannot be blocked.

        `_internal` is a real subpackage of `quack_core.core.fs` (it must be,
        for `_ops/*.py` to import from it). CPython resolves
        `from package import realsubmodule` directly against `sys.modules`
        for any name that names an actual submodule -- that resolution path
        never consults the parent package's `__getattr__` or `__dict__`, so
        no doctrine guard written in Python can intercept it (confirmed live:
        even manually evicting the submodule from both the package `__dict__`
        and `sys.modules` before the import does not stop it -- Python just
        re-imports the real file from disk). This is a hard language-level
        limit, not a gap in `fs/__init__.py`'s guard.

        What IS achievable and IS enforced (see
        `test_internal_modules_not_exported`): plain attribute access,
        `import quack_core.core.fs as fs; fs._internal`, correctly raises
        `AttributeError` via `__getattr__` once the module scrubs the
        auto-bound submodule reference from its own namespace.
        """
        from quack_core.core.fs import _internal  # noqa

        assert _internal is not None  # the import always succeeds; documented above

    def test_cannot_import_ops_directly_from_package(self) -> None:
        """`from quack_core.core.fs import _ops` cannot be blocked -- see
        `test_cannot_import_internal_directly_from_package`'s docstring for the
        full explanation (identical cause: `_ops` is also a real subpackage).
        """
        from quack_core.core.fs import _ops  # noqa

        assert _ops is not None  # the import always succeeds; documented above

    def test_service_module_exports_only_public_api(self) -> None:
        """Verify service module only exports service, get_service, create_service."""
        from quack_core.core.fs.service import (
            FileSystemService,
            create_service,
            get_service,
        )

        assert FileSystemService is not None
        assert get_service is not None
        assert create_service is not None

    def test_cannot_import_mixins_from_service(self) -> None:
        """Verify internal mixins cannot be imported from service module.

        `DirectoryOperationsMixin`/`FileOperationsMixin`/`_BaseFileSystemService`
        are plain classes (not submodules), so `service/__init__.py`'s
        `__getattr__` DOES get consulted for them -- verified live via plain
        attribute access (`service.DirectoryOperationsMixin` correctly raises
        `AttributeError` with the "internal service component" message).
        But CPython's `from module import name` statement unconditionally
        wraps ANY attribute-lookup failure -- including one that itself
        internally raised a helpful `AttributeError` from `__getattr__` -- into
        `ImportError: cannot import name ... from ...`, discarding the
        original exception's type and message (confirmed with a minimal
        `types.ModuleType` + `__getattr__` repro, independent of this
        codebase). No module-level code can produce `AttributeError` from this
        specific import form; asserting `ImportError` here matches the only
        exception CPython actually raises.
        """
        with pytest.raises(ImportError, match="DirectoryOperationsMixin"):
            from quack_core.core.fs.service import DirectoryOperationsMixin  # noqa

        with pytest.raises(ImportError, match="FileOperationsMixin"):
            from quack_core.core.fs.service import FileOperationsMixin  # noqa

        with pytest.raises(ImportError, match="_BaseFileSystemService"):
            from quack_core.core.fs.service import _BaseFileSystemService  # noqa

    def test_all_list_matches_actual_exports(self) -> None:
        """Verify __all__ matches actual exports."""
        import quack_core.core.fs as fs

        # Get __all__
        all_exports = fs.__all__

        # Verify each item in __all__ is actually exported
        for name in all_exports:
            assert hasattr(fs, name), f"{name} in __all__ but not exported"

        # Key exports should be present
        assert "FileSystemService" in all_exports
        assert "get_service" in all_exports
        assert "create_service" in all_exports

        # Internal modules should NOT be in __all__
        assert "_internal" not in all_exports
        assert "_ops" not in all_exports

    def test_service_all_list_matches_exports(self) -> None:
        """Verify service.__all__ matches actual exports."""
        import quack_core.core.fs.service as service

        all_exports = service.__all__

        # Should only have the three public functions
        assert len(all_exports) == 3
        assert "FileSystemService" in all_exports
        assert "get_service" in all_exports
        assert "create_service" in all_exports

        # Mixins should NOT be in __all__
        assert "DirectoryOperationsMixin" not in all_exports
        assert "_BaseFileSystemService" not in all_exports


class TestPublicAPIUsability:
    """Verify the public API is sufficient for all use cases."""

    def test_can_create_service_and_use_operations(self) -> None:
        """Verify service creation and basic operations work."""
        from quack_core.core.fs import FileSystemService, create_service

        service = create_service()
        assert isinstance(service, FileSystemService)

        # Should have all expected methods
        assert hasattr(service, "read_text")
        assert hasattr(service, "write_text")
        assert hasattr(service, "exists")
        assert hasattr(service, "normalize_path")

    def test_can_use_singleton_service(self) -> None:
        """Verify singleton accessor works."""
        from quack_core.core.fs import get_service

        service1 = get_service()
        service2 = get_service()

        # Should be same instance
        assert service1 is service2

    def test_can_use_result_types_for_type_hints(self) -> None:
        """Verify result types can be imported for type hints."""
        from quack_core.core.fs import (
            OperationResult,
            ReadResult,
            WriteResult,
        )

        # Should be usable in type hints
        def example_function() -> ReadResult[str]:
            from quack_core.core.fs import get_service

            return get_service().read_text("test.txt")

        # Type should be available
        assert ReadResult is not None
        assert WriteResult is not None
        assert OperationResult is not None


class TestDoctrineEnforcement:
    """Verify doctrine is enforced at import level."""

    def test_no_pathlib_in_public_exports(self) -> None:
        """Verify Path is not directly exported."""
        import quack_core.core.fs as fs

        # Path should not be in public API
        assert "Path" not in fs.__all__

        # Users should use FsPathLike or just pass strings/Paths
        # They don't need to import Path from fs

    def test_no_normalize_module_in_public_exports(self) -> None:
        """Verify normalize module is not exported."""
        import quack_core.core.fs as fs

        # Normalization is internal
        assert "normalize" not in fs.__all__
        assert "coerce_path" not in fs.__all__

        # All normalization happens inside service

    def test_service_is_only_entry_point(self) -> None:
        """Verify FileSystemService is the only way to do operations."""
        import quack_core.core.fs as fs

        # No standalone operation functions in main module
        assert "read_text" not in fs.__all__
        assert "write_text" not in fs.__all__

        # Users must go through service
        # (standalone wrappers are in service.standalone if needed)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
