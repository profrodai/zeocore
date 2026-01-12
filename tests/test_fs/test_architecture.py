# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_fs/test_architecture.py
# role: tests
# neighbors: __init__.py, test_atomic_wrapping.py, test_operations.py, test_path_utils.py, test_results.py, test_service.py (+2 more)
# exports: get_imports, test_internal_import_boundary, test_ops_import_boundary
# git_branch: feat/9-make-setup-work
# git_commit: 528aa222
# === QV-LLM:END ===

import ast
import os
from pathlib import Path
import pytest

# Define the package root relative to this test file
PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def get_imports(file_path):
    """Parses a python file and returns a set of imported module names."""
    with open(file_path, "r", encoding="utf-8") as f:
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


def test_internal_import_boundary():
    """
    Enforce doctrine: _internal modules should NOT be imported outside of
    quack_core.core.fs._ops and quack_core.core.fs._internal itself.
    """
    internal_marker = "quack_core.core.fs._internal"

    # Files allowed to import _internal: _ops and tests
    allowed_dirs = [
        PACKAGE_ROOT / "_ops",
        PACKAGE_ROOT / "_internal",
        PACKAGE_ROOT / "tests",
    ]

    for root, dirs, files in os.walk(PACKAGE_ROOT):
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
                        pytest.fail(f"Doctrine Violation: {file_path} imports {imp}. "
                                    f"_internal should only be used by _ops.")


def test_ops_import_boundary():
    """
    Enforce doctrine: _ops modules should NOT be imported outside of
    quack_core.core.fs.service.
    """
    ops_marker = "quack_core.core.fs._ops"

    # Files allowed to import _ops: service and tests
    allowed_dirs = [
        PACKAGE_ROOT / "service",
        PACKAGE_ROOT / "_ops",
        PACKAGE_ROOT / "tests",
    ]

    for root, dirs, files in os.walk(PACKAGE_ROOT):
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
                        pytest.fail(f"Doctrine Violation: {file_path} imports {imp}. "
                                    f"_ops should only be used by service.")