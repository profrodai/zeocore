import ast
import os
from pathlib import Path

import pytest

import zeo_core.core.fs as _fs_pkg

# Define the package root as the real `zeo_core.core.fs` source directory
# this checker means to validate against. `Path(__file__).resolve().parent.parent`
# (this test file lives at zeocore/tests/test_fs/test_architecture.py) resolves
# to zeocore/tests/ -- one directory too shallow, and not even on the source
# side of the repo -- so the old computation's allowed_dirs list (`tests/_ops`,
# `tests/_internal`, `tests/tests`) never matched anything real and the walk below
# silently scanned the tests/ tree instead of fs/'s actual source tree. Anchored on
# the imported package's own __file__ so it can never drift from the real module
# location again, regardless of future reorganization.
PACKAGE_ROOT = Path(_fs_pkg.__file__).resolve().parent

# Where the test files themselves live -- tests are allowed to import _internal/
# _ops directly by full path (confirmed doctrine per
# quackverse-fs-internals-fix-SOW-01: test_operations.py's entire purpose is
# testing _ops.base.FileSystemOperations directly).
TESTS_ROOT = Path(__file__).resolve().parent


def get_imports(file_path: Path) -> set[str]:
    """Parses a python file and returns a set of imported module names."""
    with open(file_path, encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports


def test_internal_import_boundary() -> None:
    """
    Enforce doctrine: _internal modules should NOT be imported outside of
    zeo_core.core.fs._ops and zeo_core.core.fs._internal itself.
    """
    internal_marker = "zeo_core.core.fs._internal"

    # Files allowed to import _internal: _ops, _internal itself, and tests
    allowed_dirs = [
        PACKAGE_ROOT / "_ops",
        PACKAGE_ROOT / "_internal",
        TESTS_ROOT,
    ]

    for root, _dirs, files in list(os.walk(PACKAGE_ROOT)) + list(os.walk(TESTS_ROOT)):
        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = Path(root) / file

            # Check if this file is in an allowed directory
            is_allowed = any(str(file_path).startswith(str(d)) for d in allowed_dirs)

            if not is_allowed:
                imports = get_imports(file_path)
                for imp in imports:
                    if imp.startswith(internal_marker):
                        pytest.fail(
                            f"Doctrine Violation: {file_path} imports {imp}. "
                            f"_internal should only be used by _ops."
                        )


def test_ops_import_boundary() -> None:
    """
    Enforce doctrine: _ops modules should NOT be imported outside of
    zeo_core.core.fs.service.
    """
    ops_marker = "zeo_core.core.fs._ops"

    # Files allowed to import _ops: service, _ops itself, and tests
    allowed_dirs = [
        PACKAGE_ROOT / "service",
        PACKAGE_ROOT / "_ops",
        TESTS_ROOT,
    ]

    for root, _dirs, files in list(os.walk(PACKAGE_ROOT)) + list(os.walk(TESTS_ROOT)):
        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = Path(root) / file

            # Check if this file is in an allowed directory
            is_allowed = any(str(file_path).startswith(str(d)) for d in allowed_dirs)

            if not is_allowed:
                imports = get_imports(file_path)
                for imp in imports:
                    if imp.startswith(ops_marker):
                        pytest.fail(
                            f"Doctrine Violation: {file_path} imports {imp}. "
                            f"_ops should only be used by service."
                        )
