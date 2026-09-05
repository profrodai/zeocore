"""OAuth credentials enter custody before any public result exists."""

import os
from unittest.mock import MagicMock, patch

import pytest

from zeo_core.contracts.connections import OrganizationId, SecretRef
from zeo_core.integrations.notion import (
    NotionAPIError,
    NotionOAuthBroker,
    NotionOAuthCredentialDispatcher,
    NotionOAuthGrant,
    NotionTokenInspection,
    NotionTokenRevocation,
)


def _broker() -> tuple[NotionOAuthBroker, MagicMock, MagicMock]:
    sdk = MagicMock()
    store = MagicMock()
    store.put.side_effect = [
        SecretRef(handle="access-handle"),
        SecretRef(handle="refresh-handle"),
    ]
    broker = NotionOAuthBroker(
        secret_store=store,
        organization_id=OrganizationId(value="org-course"),
        sdk_client=sdk,
    )
    return broker, sdk, store


def test_default_sdk_wiring_uses_explicit_direct_transport() -> None:
    store = MagicMock()
    sdk = MagicMock()
    transport = MagicMock()
    with (
        patch("notion_client.Client", return_value=sdk) as sdk_factory,
        patch(
            "zeo_core.integrations.notion.oauth.build_notion_http_client",
            return_value=transport,
        ) as transport_factory,
    ):
        broker = NotionOAuthBroker(
            secret_store=store,
            organization_id=OrganizationId(value="org-course"),
        )

    assert broker._sdk is sdk
    transport_factory.assert_called_once_with(trust_env=False)
    assert sdk_factory.call_args.kwargs["client"] is transport


def test_exchange_custodies_both_tokens_and_public_grant_cannot_leak() -> None:
    broker, sdk, store = _broker()
    access, refresh = "ntn_ACCESS_CANARY", "ntn_REFRESH_CANARY"
    sdk.oauth.token.return_value = {
        "access_token": access,
        "refresh_token": refresh,
        "bot_id": "bot-1",
        "workspace_id": "ws-1",
        "workspace_name": "Course",
    }

    with patch.dict(
        os.environ,
        {
            "NOTION_OAUTH_CLIENT_ID": "client-id",
            "NOTION_OAUTH_CLIENT_SECRET": "client-secret",
        },
    ):
        grant = broker.exchange(code="one-use-code")

    assert store.put.call_count == 2
    assert store.put.call_args_list[0].kwargs["material"] == access
    assert store.put.call_args_list[1].kwargs["material"] == refresh
    rendered = repr(grant) + str(grant) + grant.model_dump_json()
    assert access not in rendered
    assert refresh not in rendered
    assert grant.access_ref.handle == "access-handle"


def test_exchange_custody_failure_deletes_already_stored_access_ref() -> None:
    broker, sdk, store = _broker()
    store.put.side_effect = [SecretRef(handle="access-handle"), RuntimeError("no")]
    sdk.oauth.token.return_value = {
        "access_token": "access",
        "refresh_token": "refresh",
        "bot_id": "bot-1",
        "workspace_id": "ws-1",
    }

    with (
        patch.dict(
            os.environ,
            {
                "NOTION_OAUTH_CLIENT_ID": "client-id",
                "NOTION_OAUTH_CLIENT_SECRET": "client-secret",
            },
        ),
        pytest.raises(NotionAPIError, match="custody"),
    ):
        broker.exchange(code="code")

    store.delete.assert_called_once()


def test_refresh_reads_environment_and_custodies_replacement_grant() -> None:
    broker, sdk, store = _broker()
    canary = "ntn_REFRESH_INPUT_CANARY"
    sdk.oauth.token.return_value = {
        "access_token": "replacement-access",
        "refresh_token": "replacement-refresh",
        "bot_id": "bot-1",
        "workspace_id": "ws-1",
    }

    with patch.dict(
        os.environ,
        {
            "NOTION_OAUTH_CLIENT_ID": "client-id",
            "NOTION_OAUTH_CLIENT_SECRET": "client-secret",
            "NOTION_OAUTH_REFRESH_TOKEN": canary,
        },
    ):
        grant = broker.refresh_environment_grant()

    sdk.oauth.token.assert_called_once_with(
        "client-id",
        "client-secret",
        grant_type="refresh_token",
        refresh_token=canary,
    )
    assert store.put.call_count == 2
    assert canary not in repr(grant) + str(grant) + grant.model_dump_json()


def test_oauth_provider_failure_has_no_secret_bearing_cause() -> None:
    broker, sdk, _store = _broker()
    canary = "ntn_PROVIDER_ERROR_CANARY"
    sdk.oauth.token.side_effect = RuntimeError(canary)

    with (
        patch.dict(
            os.environ,
            {
                "NOTION_OAUTH_CLIENT_ID": "client-id",
                "NOTION_OAUTH_CLIENT_SECRET": "client-secret",
            },
        ),
        pytest.raises(NotionAPIError) as caught,
    ):
        broker.exchange(code="code")

    assert caught.value.__cause__ is None
    assert canary not in repr(caught.value) + str(caught.value)


def test_introspect_and_revoke_read_secrets_only_from_environment() -> None:
    broker, sdk, _store = _broker()
    sdk.oauth.introspect.return_value = {"active": True}
    sdk.oauth.revoke.return_value = {"revoked": True}
    fake_token = "token"  # noqa: S105 -- inert SDK-double fixture
    environment = {
        "NOTION_OAUTH_CLIENT_ID": "client-id",
        "NOTION_OAUTH_CLIENT_SECRET": "client-secret",
        "NOTION_TOKEN": fake_token,
    }

    with patch.dict(os.environ, environment):
        assert broker.introspect_environment_token() == {"active": True}
        assert broker.revoke_environment_token() == {"revoked": True}

    sdk.oauth.introspect.assert_called_once_with(
        "client-id", "client-secret", token=fake_token
    )
    sdk.oauth.revoke.assert_called_once_with(
        "client-id", "client-secret", token=fake_token
    )


def test_oauth_missing_configuration_fails_without_echoing_values() -> None:
    broker, _sdk, _store = _broker()

    with (
        patch.dict(os.environ, {}, clear=True),
        pytest.raises(NotionAPIError, match="not configured"),
    ):
        broker.exchange(code="code")


class RecordingCredentialDispatcher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, OrganizationId, SecretRef]] = []

    def refresh(
        self, *, organization_id: OrganizationId, refresh_ref: SecretRef
    ) -> NotionOAuthGrant:
        self.calls.append(("refresh", organization_id, refresh_ref))
        return NotionOAuthGrant(
            access_ref=SecretRef(handle="new-access-ref"),
            refresh_ref=SecretRef(handle="new-refresh-ref"),
            bot_id="bot-1",
            workspace_id="workspace-1",
        )

    def introspect(
        self, *, organization_id: OrganizationId, access_ref: SecretRef
    ) -> NotionTokenInspection:
        self.calls.append(("introspect", organization_id, access_ref))
        return NotionTokenInspection(
            active=True, bot_id="bot-1", workspace_id="workspace-1"
        )

    def revoke(
        self, *, organization_id: OrganizationId, access_ref: SecretRef
    ) -> NotionTokenRevocation:
        self.calls.append(("revoke", organization_id, access_ref))
        return NotionTokenRevocation(revoked=True)


def test_hosted_dispatcher_receives_only_bound_refs_and_returns_safe_models() -> None:
    sdk = MagicMock()
    store = MagicMock()
    dispatcher = RecordingCredentialDispatcher()
    organization_id = OrganizationId(value="org-hosted")
    broker = NotionOAuthBroker(
        secret_store=store,
        organization_id=organization_id,
        sdk_client=sdk,
        credential_dispatcher=dispatcher,
    )
    refresh_ref = SecretRef(handle="INPUT_REFRESH_CANARY")
    access_ref = SecretRef(handle="INPUT_ACCESS_CANARY")

    grant = broker.refresh_custodied_grant(refresh_ref=refresh_ref)
    inspection = broker.introspect_custodied_token(access_ref=access_ref)
    revocation = broker.revoke_custodied_token(access_ref=access_ref)

    assert dispatcher.calls == [
        ("refresh", organization_id, refresh_ref),
        ("introspect", organization_id, access_ref),
        ("revoke", organization_id, access_ref),
    ]
    assert grant.access_ref.handle == "new-access-ref"
    assert inspection.active
    assert revocation.revoked
    assert isinstance(dispatcher, NotionOAuthCredentialDispatcher)
    sdk.oauth.token.assert_not_called()
    disclosure = "\n".join(
        (
            repr(grant),
            grant.model_dump_json(),
            inspection.model_dump_json(),
            revocation.model_dump_json(),
        )
    )
    assert "INPUT_REFRESH_CANARY" not in disclosure
    assert "INPUT_ACCESS_CANARY" not in disclosure


def test_hosted_methods_refuse_when_no_custody_dispatcher_exists() -> None:
    broker, _sdk, _store = _broker()

    with pytest.raises(NotionAPIError, match="not configured"):
        broker.refresh_custodied_grant(refresh_ref=SecretRef(handle="opaque-ref"))
