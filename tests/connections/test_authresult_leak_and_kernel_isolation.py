"""AuthResult disclosure and connections-kernel isolation proofs.

The original strict xfail banked the credential disclosure defect while its
repair remained outside ZC0 step one's scope. The operator's 2026-09-03
directive and Principal disposition on issue #180 now authorize this repair.
The matrix below replaces that xfail with calibrated, positive conformance:
all 11 ruled paths must redact, while the two structural exclusions remain
visible in the SecretRef control so the gate cannot silently widen itself.
"""

from __future__ import annotations

import copy
import io
import json
import logging
import pickle
import traceback

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

import zeo_core.contracts.connections as connections_pkg
from zeo_core.contracts.connections import SecretRef
from zeo_core.integrations.core.results import AuthResult

CANARY = "CANARY-SECRET-zc0-kernel-seam-9f3a"


def _egress_values(model: BaseModel) -> dict[str, str | bytes]:
    """The 13-path matrix measured by Sparring; 11 are governed."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("authresult-disclosure-probe")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        logger.info("%s", model)
    finally:
        logger.removeHandler(handler)

    try:
        raise RuntimeError(model)
    except RuntimeError:
        rendered_traceback = traceback.format_exc()

    return {
        "repr": repr(model),
        "str": str(model),
        "fstring": f"{model}",
        "format": format(model),
        "percent_s": "%s" % (model,),  # noqa: UP031 -- this path is the proof
        "model_dump": json.dumps(model.model_dump(), default=str),
        "model_dump_json": model.model_dump_json(),
        "model_dump_json_mode": json.dumps(model.model_dump(mode="json"), default=str),
        "logging_percent_s": stream.getvalue(),
        "dict": repr(dict(model)),
        "pickle": pickle.dumps(model),
        "deepcopy_repr": repr(copy.deepcopy(model)),
        "traceback": rendered_traceback,
    }


def _leaks(model: BaseModel, canary: str = CANARY) -> dict[str, bool]:
    return {
        name: (
            canary.encode() in value if isinstance(value, bytes) else canary in value
        )
        for name, value in _egress_values(model).items()
    }


GOVERNED_PATHS = frozenset(
    {
        "repr",
        "str",
        "fstring",
        "format",
        "percent_s",
        "model_dump",
        "model_dump_json",
        "model_dump_json_mode",
        "logging_percent_s",
        "deepcopy_repr",
        "traceback",
    }
)
STRUCTURAL_EXCLUSIONS = frozenset({"dict", "pickle"})


class UnredactedResult(BaseModel):
    """Known-bad positive control for every matrix cell."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    value: object


def test_disclosure_matrix_has_positive_and_ruled_controls() -> None:
    positive = _leaks(UnredactedResult(value=CANARY))
    assert all(positive.values()), f"known-bad result was not detected: {positive}"

    ruled = _leaks(SecretRef(handle=CANARY))
    assert {name for name, leaks in ruled.items() if leaks} == STRUCTURAL_EXCLUSIONS
    assert set(ruled) == GOVERNED_PATHS | STRUCTURAL_EXCLUSIONS


def test_authresult_rejects_bearer_token_as_a_field() -> None:
    assert "token" not in AuthResult.model_fields
    with pytest.raises(ValidationError):
        AuthResult.model_validate({"success": True, "token": CANARY})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("message", CANARY),
        ("credentials_path", CANARY),
        ("content", {"provider_payload": CANARY}),
    ],
)
def test_authresult_fields_are_safe_on_all_11_accidental_paths(
    field: str, value: object
) -> None:
    result = AuthResult(success=True, **{field: value})
    leaks = _leaks(result)
    governed_leaks = {name: leaks[name] for name in GOVERNED_PATHS}
    assert not any(governed_leaks.values()), f"{field} leaked: {governed_leaks}"


def test_authresult_trusted_direct_metadata_access_remains_exact() -> None:
    content = {"identity": "did:example:123"}
    result = AuthResult(
        success=True,
        message="authenticated",
        credentials_path="opaque-local-location",
        content=content,
    )
    assert result.message == "authenticated"
    assert result.credentials_path == "opaque-local-location"
    assert result.content == content


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
