"""
Must-NOT: no public model in contracts/connections carries a raw credential
field.

ZC0-KERNEL-SEAM-01 section 3 / packet section 21.5 acceptance check,
verbatim: "no public model has a `token`, `password`, `secret_value`,
auth-header or raw credential field." The banned field names checked here
are `token`, `password`, `secret_value`, `auth_header`, `authorization`,
`bearer_token`, `api_key`, `secret`, `credential`, `credentials` -- the
literal four named in the SOW plus the near-synonyms an author reaching for
"the field that holds the secret" would plausibly type. `secret_handle` and
`secret_ref` are the one sanctioned exception (an opaque SecretRef, not
material) and are excluded explicitly, by name, rather than by a substring
rule that would also swallow them.

`TestProbeCanFail` proves this checker is a real probe by constructing a
deliberately broken Pydantic model inline -- shaped exactly like the known
AuthResult hazard at
`src/zeo_core/integrations/core/results.py:61` (`token: str | None`) -- and
showing the same field-introspection function catches it. That model is
built in-test only; it is never written into contracts/connections.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

import zeo_core.contracts.connections as connections_pkg

#: Field names that would carry raw credential material. Matched exactly
#: against a model's field name (case-insensitive), not by substring --
#: `secret_handle` and `secret_ref` contain "secret" but are the sanctioned
#: opaque-reference shape, not banned material, so this must not be a
#: substring check or it would flag its own solution.
BANNED_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "token",
        "password",
        "secret_value",
        "auth_header",
        "authorization",
        "bearer_token",
        "api_key",
        "secret",
        "credential",
        "credentials",
    }
)

#: Field names that are the sanctioned opaque-reference shape and must never
#: be flagged even though they contain "secret".
ALLOWED_SECRET_REF_FIELDS: frozenset[str] = frozenset({"secret_handle", "secret_ref"})


def find_banned_credential_fields(model: type[BaseModel]) -> list[str]:
    """
    Return the banned field names present on `model`, if any.

    Pure introspection over `model.model_fields` -- no instances are
    constructed, so this works even for models whose other fields would
    require elaborate fixtures to instantiate.
    """
    found: list[str] = []
    for field_name in model.model_fields:
        if field_name in ALLOWED_SECRET_REF_FIELDS:
            continue
        if field_name.lower() in BANNED_FIELD_NAMES:
            found.append(field_name)
    return found


def _all_public_models() -> list[type[BaseModel]]:
    models: list[type[BaseModel]] = []
    for name in connections_pkg.__all__:
        obj = getattr(connections_pkg, name)
        if isinstance(obj, type) and issubclass(obj, BaseModel):
            models.append(obj)
    return models


class TestNoRawCredentialFieldsToday:
    """Runs the real probe against every public model this package exports."""

    def test_found_at_least_one_model(self) -> None:
        models = _all_public_models()
        assert models, "expected at least one public BaseModel export"

    def test_no_banned_fields_on_any_public_model(self) -> None:
        models = _all_public_models()
        violations: dict[str, list[str]] = {}
        for model in models:
            banned = find_banned_credential_fields(model)
            if banned:
                violations[model.__name__] = banned

        assert not violations, (
            "public connections models must not carry raw credential "
            f"fields, found: {violations}"
        )

    def test_secret_ref_itself_carries_no_material_field(self) -> None:
        # SecretRef is the one model allowed to have "secret"-shaped
        # vocabulary in its name; assert directly that its only field is
        # the opaque handle, not a broader allow-by-name exemption than
        # that.
        secret_ref_model = connections_pkg.SecretRef
        assert set(secret_ref_model.model_fields) == {"handle"}


class TestProbeCanFail:
    """
    Proves find_banned_credential_fields is a real probe by observing it
    fail against a deliberately broken synthetic model shaped like the
    known AuthResult hazard.
    """

    def test_probe_catches_token_field(self) -> None:
        class BrokenLikeAuthResult(BaseModel):
            # Mirrors src/zeo_core/integrations/core/results.py:61 exactly:
            # a plain optional string field named `token`.
            model_config = ConfigDict(extra="forbid")
            success: bool = True
            token: str | None = None

        assert find_banned_credential_fields(BrokenLikeAuthResult) == ["token"]

    def test_probe_catches_password_and_api_key(self) -> None:
        class BrokenMultiField(BaseModel):
            model_config = ConfigDict(extra="forbid")
            password: str
            api_key: str

        found = find_banned_credential_fields(BrokenMultiField)
        assert set(found) == {"password", "api_key"}

    def test_probe_passes_clean_secret_ref_shaped_model(self) -> None:
        class CleanRefOnly(BaseModel):
            model_config = ConfigDict(frozen=True, extra="forbid")
            secret_handle: str

        assert find_banned_credential_fields(CleanRefOnly) == []
