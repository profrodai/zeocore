"""Tests for CapabilityId, definitions, effects, and manifests."""

from __future__ import annotations

import json

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import BaseModel, ValidationError

from zeo_core.contracts import (
    CapabilityDefinition,
    CapabilityEffects,
    CapabilityExample,
    CapabilityId,
    CapabilityManifest,
    CapabilityOutcome,
    CapabilityResult,
    CapabilityStatus,
    ConcurrencyMode,
    EffectKind,
    schemas_from_models,
)


class _Req(BaseModel):
    x: int
    y: str | None = None


class _Res(BaseModel):
    z: int


def _example() -> CapabilityExample:
    return CapabilityExample(request={"x": 1}, response={"z": 2})


def _definition(**kwargs: object) -> CapabilityDefinition:
    req, res = schemas_from_models(_Req, _Res)
    defaults: dict[str, object] = {
        "id": CapabilityId.parse("math.add@1.0.0"),
        "description": "Add numbers.",
        "request_schema": req,
        "response_schema": res,
        "examples": (_example(),),
        "effects": CapabilityEffects(kinds=frozenset({EffectKind.READ})),
    }
    defaults.update(kwargs)
    return CapabilityDefinition(**defaults)


def test_canonical_id_roundtrip() -> None:
    ident = CapabilityId.parse("google.calendar.event.create@1.0.0")
    assert ident.namespace == "google.calendar.event"
    assert ident.name == "create"
    assert ident.version == "1.0.0"
    assert ident.canonical() == "google.calendar.event.create@1.0.0"
    assert CapabilityId.parse(ident.canonical()) == ident


def test_identity_is_frozen() -> None:
    ident = CapabilityId.parse("math.add@1.0.0")
    with pytest.raises(ValidationError):
        ident.name = "sub"  # type: ignore[misc]


def test_rejects_empty_description_and_examples() -> None:
    with pytest.raises(ValidationError):
        _definition(description="  ")
    with pytest.raises(ValidationError):
        _definition(examples=())


def test_rejects_duplicate_examples() -> None:
    with pytest.raises(ValidationError):
        _definition(examples=(_example(), _example()))


def test_serial_per_resource_requires_key_fields() -> None:
    with pytest.raises(ValidationError):
        CapabilityEffects(
            kinds=frozenset({EffectKind.WRITE}),
            concurrency=ConcurrencyMode.SERIAL_PER_RESOURCE,
        )


def test_manifest_omits_availability() -> None:
    manifest = CapabilityManifest.from_definition(_definition())
    dumped = manifest.model_dump()
    assert "available" not in dumped
    assert dumped["id"]["name"] == "add"


def test_definition_json_roundtrip_stable() -> None:
    definition = _definition(tags=frozenset({"math"}))
    first = json.dumps(definition.model_dump(mode="json"), sort_keys=True)
    second = json.dumps(
        CapabilityDefinition.model_validate_json(
            definition.model_dump_json()
        ).model_dump(mode="json"),
        sort_keys=True,
    )
    assert first == second


def test_result_outcome_defaults() -> None:
    ok = CapabilityResult.ok(data=1, msg="ok")
    assert ok.outcome == CapabilityOutcome.success
    skip: CapabilityResult[object] = CapabilityResult.skip(
        reason="nope", code="ZEO_VAL_SKIP"
    )
    assert skip.outcome == CapabilityOutcome.policy_skipped
    assert skip.status == CapabilityStatus.skipped
    fail: CapabilityResult[object] = CapabilityResult.fail(msg="x", code="ZEO_IO_ERROR")
    assert fail.outcome == CapabilityOutcome.integration_failure
    unavail: CapabilityResult[object] = CapabilityResult.unavailable("missing")
    assert unavail.outcome == CapabilityOutcome.unavailable
    assert unavail.status == CapabilityStatus.skipped


@given(
    ns=st.sampled_from(["math", "google.calendar", "github.repository.file"]),
    name=st.sampled_from(["add", "create", "read"]),
    major=st.integers(0, 9),
    minor=st.integers(0, 20),
    patch=st.integers(0, 20),
)
def test_identity_canonical_property(
    ns: str, name: str, major: int, minor: int, patch: int
) -> None:
    version = f"{major}.{minor}.{patch}"
    raw = f"{ns}.{name}@{version}"
    ident = CapabilityId.parse(raw)
    assert ident.canonical() == raw
    assert CapabilityId.parse(ident.canonical()) == ident
    assert str(ident) == raw


def test_identity_rejects_malformed_values() -> None:
    with pytest.raises(ValidationError):
        CapabilityId(namespace="Math", name="add", version="1.0.0")
    with pytest.raises(ValidationError):
        CapabilityId(namespace="math", name="ADD", version="1.0.0")
    with pytest.raises(ValidationError):
        CapabilityId(namespace="math", name="add", version="1")
    with pytest.raises(ValueError):
        CapabilityId.parse("not-an-id")
    with pytest.raises(ValueError):
        CapabilityId.parse("math.add@not-a-semver")
    from zeo_core.contracts.capabilities.identity import parse_semver

    assert parse_semver("1.2.3-alpha+build") == (1, 2, 3)


def test_bad_error_code_and_non_json_metadata() -> None:
    with pytest.raises(ValidationError):
        _definition(error_codes=frozenset({"NOT_A_CODE"}))
    with pytest.raises(ValidationError):
        _definition(metadata={"fn": object()})
