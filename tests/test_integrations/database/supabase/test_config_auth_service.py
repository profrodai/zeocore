"""Configuration, authentication, service, and protocol contracts."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from zeo_core.integrations.database.supabase import (
    SupabaseAuthProvider,
    SupabaseClient,
    SupabaseConfigProvider,
    SupabaseDatabaseProtocol,
    SupabaseFunctionsProtocol,
    SupabaseIntegration,
    SupabaseIntegrationProtocol,
    SupabaseKeyKind,
    SupabaseStorageProtocol,
    SupabaseUserAuthProtocol,
    classify_key,
)


def test_config_contains_no_key_material(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_CANARY")
    provider = SupabaseConfigProvider()
    result = provider.load_config()
    assert result.success
    rendered = str(result.model_dump()) + result.model_dump_json()
    assert "sb_publishable_CANARY" not in rendered
    assert result.content is not None
    assert "key" not in result.content


def test_auth_provider_requires_explicit_privileged_opt_in() -> None:
    provider = SupabaseAuthProvider(
        "sb_secret_CANARY", key_kind=SupabaseKeyKind.PRIVILEGED
    )
    result = provider.authenticate()
    assert not result.success
    assert "CANARY" not in str(result)

    admitted = SupabaseAuthProvider(
        "sb_secret_CANARY",
        key_kind=SupabaseKeyKind.PRIVILEGED,
        allow_privileged_key=True,
    )
    assert admitted.authenticate().success
    assert isinstance(admitted.get_credentials(), SecretStr)
    assert "CANARY" not in repr(admitted)


def test_key_classifier_does_not_decode_or_render_key() -> None:
    assert classify_key("sb_publishable_anything") is SupabaseKeyKind.PUBLISHABLE
    assert classify_key("sb_secret_anything") is SupabaseKeyKind.PRIVILEGED
    assert classify_key("legacy-jwt") is SupabaseKeyKind.UNKNOWN


def test_service_satisfies_all_sync_protocols() -> None:
    sdk = MagicMock()
    client = SupabaseClient(
        "https://example.supabase.co", "sb_publishable_test", sdk_client=sdk
    )
    realtime = MagicMock()
    service = SupabaseIntegration(client=client, realtime_client=realtime)
    assert isinstance(service, SupabaseIntegrationProtocol)
    assert isinstance(service, SupabaseDatabaseProtocol)
    assert isinstance(service, SupabaseUserAuthProtocol)
    assert isinstance(service, SupabaseStorageProtocol)
    assert isinstance(service, SupabaseFunctionsProtocol)
    assert service.integration_id == "supabase"
    assert service.is_available()


def test_service_normalizes_validation_without_secret_echo() -> None:
    sdk = MagicMock()
    client = SupabaseClient(
        "https://example.supabase.co", "sb_publishable_test", sdk_client=sdk
    )
    service = SupabaseIntegration(client=client, realtime_client=MagicMock())
    result = service.invoke_function(
        "bad/name", headers={"Authorization": "CREDENTIAL-CANARY"}
    )
    assert not result.success
    assert "CREDENTIAL-CANARY" not in result.model_dump_json()


def test_factory_initialization_uses_env_without_result_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canary = "sb_publishable_CREDENTIAL_CANARY"
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", canary)
    captured: dict[str, object] = {}

    def factory(**kwargs: object) -> SupabaseClient:
        captured.update(kwargs)
        return SupabaseClient(
            str(kwargs["url"]), str(kwargs["key"]), sdk_client=MagicMock()
        )

    service = SupabaseIntegration(client_factory=factory)
    result = service.initialize()
    assert result.success
    assert captured["key"] == canary
    assert canary not in repr(result)
    assert canary not in result.model_dump_json()


def test_public_surface_has_no_vault_or_raw_sql_escape_hatch() -> None:
    forbidden = {
        "vault",
        "decrypted_secrets",
        "raw_sql",
        "execute_sql",
        "signed_url",
        "service_role",
    }
    public = {
        name.lower() for name in dir(SupabaseIntegration) if not name.startswith("_")
    }
    assert public.isdisjoint(forbidden)
