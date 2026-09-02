"""
Must-NOT: no adapter imports into contracts/connections.

ZC0-KERNEL-SEAM-01 step 1 requirement, verbatim: "Add frozen pure contracts
and transition table. No adapter imports into contracts." This is checked
two ways:

1. `test_no_adapter_imports_today` walks the real
   `src/zeo_core/contracts/connections/` tree with the same AST-import
   technique as `tests/test_contracts/test_dependency_boundaries.py` and
   asserts zero violations against the actual shipped files.
2. `TestProbeCanFail` proves the checker itself is a working must-NOT probe,
   not a checker that would pass no matter what: it runs the identical
   checking function against a deliberately broken synthetic file (written
   to a temp directory, never to the real source tree) that imports
   `zeo_core.integrations` and `zeo_core.connections.adapters.macos_keychain`
   directly, and asserts the checker catches it. A must-NOT test that has
   never been observed failing is not known to be a test (doctrine section 6,
   RULING-415 section 3c) -- this second test is that observation, made
   permanent and reproducible rather than a one-off manual demonstration.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

#: Forbidden import roots for anything under contracts/connections.
#: zeo_core.connections.adapters is the concrete adapter package named by
#: the packet (macos_keychain.py, sqlite.py); zeo_core.integrations is the
#: existing adapter-shaped package family (google/, github/, database/,
#: etc.) that already carries the AuthResult leak this stream must not
#: import or re-export. Both are adapters relative to contracts.
FORBIDDEN_IMPORT_ROOTS: tuple[str, ...] = (
    "zeo_core.connections.adapters",
    "zeo_core.integrations",
    "zeo_core.tools",
    "zeo_core.adapters",
)


def find_forbidden_imports(source: str, filename: str) -> list[str]:
    """
    Parse `source` and return every imported module path that starts with
    one of FORBIDDEN_IMPORT_ROOTS.

    Pure function: no filesystem access beyond what the caller already did
    to produce `source`, so it can be run against either a real file's
    contents or a synthetic in-memory string with identical behavior. That
    is what makes the RED-then-GREEN proof in TestProbeCanFail meaningful --
    the exact same function is doing the checking in both cases.
    """
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        pytest.fail(f"{filename}: could not parse as Python: {exc}")

    violations: list[str] = []
    for node in ast.walk(tree):
        module: str | None = None
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                if module.startswith(FORBIDDEN_IMPORT_ROOTS):
                    violations.append(module)
        elif isinstance(node, ast.ImportFrom):
            module = node.module
            if module and module.startswith(FORBIDDEN_IMPORT_ROOTS):
                violations.append(module)
    return violations


def _connections_contracts_root() -> Path:
    test_dir = Path(__file__).parent  # tests/connections/
    repo_root = test_dir.parent.parent  # zeocore/
    return repo_root / "src" / "zeo_core" / "contracts" / "connections"


class TestNoAdapterImportsToday:
    """Runs the real probe against the real, shipped connections contracts."""

    def test_connections_contracts_root_exists(self) -> None:
        root = _connections_contracts_root()
        assert root.exists(), f"expected contracts/connections at {root}"
        assert root.is_dir()

    def test_no_adapter_imports_today(self) -> None:
        root = _connections_contracts_root()
        py_files = [p for p in root.rglob("*.py") if "__pycache__" not in str(p)]
        assert py_files, "no Python files found under contracts/connections"

        all_violations: dict[str, list[str]] = {}
        for path in py_files:
            violations = find_forbidden_imports(path.read_text(), str(path))
            if violations:
                all_violations[str(path.relative_to(root))] = violations

        assert not all_violations, (
            "contracts/connections must not import any adapter module, "
            f"found: {all_violations}"
        )


class TestProbeCanFail:
    """
    Proves find_forbidden_imports is a real probe by observing it fail
    against deliberately broken synthetic sources.

    None of this touches the real source tree -- these are strings
    constructed in-test, parsed directly by the same function the previous
    class runs against real files.
    """

    def test_probe_catches_integrations_import(self) -> None:
        broken_source = textwrap.dedent(
            """
            from zeo_core.integrations.google.auth import get_credentials

            def leaky() -> None:
                get_credentials()
            """
        )
        violations = find_forbidden_imports(broken_source, "synthetic_broken.py")
        assert violations == ["zeo_core.integrations.google.auth"]

    def test_probe_catches_connections_adapters_import(self) -> None:
        broken_source = textwrap.dedent(
            """
            import zeo_core.connections.adapters.macos_keychain
            """
        )
        violations = find_forbidden_imports(broken_source, "synthetic_broken.py")
        assert violations == ["zeo_core.connections.adapters.macos_keychain"]

    def test_probe_catches_tools_import(self) -> None:
        broken_source = "from zeo_core.tools.registry import ToolRegistry\n"
        violations = find_forbidden_imports(broken_source, "synthetic_broken.py")
        assert violations == ["zeo_core.tools.registry"]

    def test_probe_passes_clean_source(self) -> None:
        clean_source = textwrap.dedent(
            """
            from __future__ import annotations
            from datetime import datetime
            from pydantic import BaseModel, ConfigDict, Field
            from zeo_core.contracts.connections.identity import ConnectionId

            class Foo(BaseModel):
                model_config = ConfigDict(frozen=True, extra="forbid")
                connection_id: ConnectionId
            """
        )
        violations = find_forbidden_imports(clean_source, "synthetic_clean.py")
        assert violations == []
