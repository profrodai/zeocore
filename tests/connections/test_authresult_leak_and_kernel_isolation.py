"""
Sparring condition 1 (SOW-01 section 3b): "The AuthResult leak is shown RED
before it is shown fixed -- a test that FAILS on today's bytes and passes
after."

Scope note, load-bearing: fixing `AuthResult` itself is explicitly OUT OF
SCOPE for this stream (SOW-01 section 7: "It is a legacy surface; the
packet rules legacy surfaces inadmissible for ZEOconnect but does not
authorize their rewrite in ZC0. Recorded, not fixed... It does mean the new
kernel must not import or re-export it, which the last acceptance check
already covers"). So this file does two separate things, deliberately kept
apart:

1. `test_authresult_leak_is_real_and_reachable` DEMONSTRATES the leak against
   today's bytes at `src/zeo_core/integrations/core/results.py:61` with a
   synthetic canary, exactly as the Principal packet, Master's SOW, and
   Sparring's review each independently reproduced it. This test is
   EXPECTED TO STAY RED forever, on purpose -- it documents a live legacy
   defect this stream does not fix (Chesterton's fence / circle of control:
   fixing it is a legacy API change, which the packet's escalation boundary
   sends back for a ruling, not something a step-1 stream does unilaterally).
   It is marked `xfail(strict=True)` so it shows as an expected failure in
   the gate: if it ever unexpectedly passes, that means someone fixed
   AuthResult, and `strict=True` turns that into a loud signal to update
   this file's status, not a silent green that hides a scope change.
2. `TestKernelDoesNotImportOrReexportAuthResult` is the part that DOES pass
   and IS this stream's actual acceptance evidence: it proves the new
   `contracts/connections` package (this step's deliverable) never imports,
   re-exports, or subclasses `AuthResult`, which is the concrete, in-scope
   half of Sparring's condition per SOW-01 section 7's own resolution.
"""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

import zeo_core.contracts.connections as connections_pkg
from zeo_core.integrations.core.results import AuthResult

CANARY = "CANARY-SECRET-zc0-kernel-seam-9f3a"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "documents a live legacy defect (AuthResult.token leaks through "
        "repr/str/model_dump/model_dump_json); fixing AuthResult is "
        "explicitly out of ZC0 scope per SOW-01 section 7. If this ever "
        "passes, AuthResult was fixed elsewhere -- update this test's "
        "status, do not delete it silently (append-don't-revert)."
    ),
)
def test_authresult_leak_is_real_and_reachable() -> None:
    """
    Reproduces the exact finding from the Principal packet, Master's SOW-01
    section 0, and Sparring's review section 3b(a): a synthetic canary
    passed as `token` survives all four serialization paths.

    This assertion is written as "the leak does NOT happen" -- i.e. it
    states the SECURE property this stream wants to eventually be true --
    so that `xfail` reads naturally as "this secure property does not hold
    yet" rather than inverting the logic to assert the bug positively.
    """
    result = AuthResult(success=True, token=CANARY)

    leaks_via_model_dump = CANARY in json.dumps(
        result.model_dump(mode="json"), default=str
    )
    leaks_via_model_dump_json = CANARY in result.model_dump_json()
    leaks_via_repr = CANARY in repr(result)
    leaks_via_str = CANARY in str(result)

    assert not (
        leaks_via_model_dump
        or leaks_via_model_dump_json
        or leaks_via_repr
        or leaks_via_str
    ), (
        "AuthResult.token leaked the canary via at least one serialization "
        f"path: model_dump={leaks_via_model_dump} "
        f"model_dump_json={leaks_via_model_dump_json} "
        f"repr={leaks_via_repr} str={leaks_via_str}"
    )


class TestKernelDoesNotImportOrReexportAuthResult:
    """
    The in-scope half of Sparring's condition: the new connections kernel
    must not import, re-export, or subclass AuthResult. This is what
    SOW-01 section 7 names as the acceptance check this stream actually
    owns, and section 21.5's last acceptance check ("full-tree search ->
    no ... import from ZEO Go/ZEOconnect into the public kernel") is the
    general form this specializes.
    """

    def test_authresult_not_in_connections_exports(self) -> None:
        assert "AuthResult" not in connections_pkg.__all__
        assert not hasattr(connections_pkg, "AuthResult")

    def test_no_connections_model_subclasses_authresult(self) -> None:
        violations = []
        for name in connections_pkg.__all__:
            obj = getattr(connections_pkg, name)
            if isinstance(obj, type) and issubclass(obj, AuthResult):
                violations.append(name)
        assert violations == [], (
            f"connections models must not subclass AuthResult: {violations}"
        )

    def test_no_connections_module_imports_integrations_core_results(self) -> None:
        # Complements test_no_adapter_imports.py's broader
        # zeo_core.integrations sweep with a check named specifically for
        # this hazard, so a reader searching for "AuthResult" finds a test
        # that mentions it by name, not only a generic adapter-import ban.
        import ast
        from pathlib import Path

        root = (
            Path(__file__).parent.parent.parent
            / "src"
            / "zeo_core"
            / "contracts"
            / "connections"
        )
        violations: dict[str, list[str]] = {}
        for path in root.rglob("*.py"):
            if "__pycache__" in str(path):
                continue
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.ImportFrom) and node.module:
                    if "integrations.core.results" in node.module or any(
                        alias.name == "AuthResult" for alias in node.names
                    ):
                        names.append(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if "integrations.core.results" in alias.name:
                            names.append(alias.name)
                if names:
                    violations.setdefault(str(path.name), []).extend(names)
        assert not violations, (
            f"contracts/connections must not import integrations.core.results: "
            f"{violations}"
        )

    def test_public_models_are_pydantic_basemodel_not_authresult_family(self) -> None:
        for name in connections_pkg.__all__:
            obj = getattr(connections_pkg, name)
            if isinstance(obj, type) and issubclass(obj, BaseModel):
                assert not issubclass(obj, AuthResult), (
                    f"{name} must not derive from the legacy AuthResult family"
                )
