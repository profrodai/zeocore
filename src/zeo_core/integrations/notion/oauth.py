"""Custody-first access to Notion's public OAuth endpoints."""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from zeo_core.contracts.connections import OrganizationId, SecretRef, SecretStore

from .client import NOTION_API_VERSION, NotionAPIError
from .transport import build_notion_http_client


class NotionOAuthGrant(BaseModel):
    """Non-secret OAuth exchange result; credential material is already in custody."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    access_ref: SecretRef
    refresh_ref: SecretRef | None = None
    bot_id: str
    workspace_id: str
    workspace_name: str | None = None
    duplicated_template_id: str | None = None
    request_id: str | None = None


class NotionTokenInspection(BaseModel):
    """Bounded, credential-free result of inspecting a custodial token."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    active: bool
    bot_id: str | None = None
    workspace_id: str | None = None


class NotionTokenRevocation(BaseModel):
    """Credential-free acknowledgement of a custodial token revocation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    revoked: bool


@runtime_checkable
class NotionOAuthCredentialDispatcher(Protocol):
    """High-level hosted custody port; raw token material never crosses it."""

    def refresh(
        self, *, organization_id: OrganizationId, refresh_ref: SecretRef
    ) -> NotionOAuthGrant: ...

    def introspect(
        self, *, organization_id: OrganizationId, access_ref: SecretRef
    ) -> NotionTokenInspection: ...

    def revoke(
        self, *, organization_id: OrganizationId, access_ref: SecretRef
    ) -> NotionTokenRevocation: ...


class NotionOAuthBroker:
    """Run OAuth calls without returning newly issued credentials as data."""

    def __init__(
        self,
        *,
        secret_store: SecretStore,
        organization_id: OrganizationId,
        sdk_client: Any = None,  # noqa: ANN401
        trust_env: bool = False,
        credential_dispatcher: NotionOAuthCredentialDispatcher | None = None,
    ) -> None:
        self._secret_store = secret_store
        self._organization_id = organization_id
        self._credential_dispatcher = credential_dispatcher
        if sdk_client is not None:
            self._sdk = sdk_client
        else:
            from notion_client import Client

            self._sdk = Client(
                notion_version=NOTION_API_VERSION,
                client=build_notion_http_client(trust_env=trust_env),
            )

    def _credentials(self) -> tuple[str, str]:
        client_id = os.environ.get("NOTION_OAUTH_CLIENT_ID")
        client_secret = os.environ.get("NOTION_OAUTH_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise NotionAPIError(
                "Notion OAuth client credentials are not configured",
                code="oauth_not_configured",
            )
        return client_id, client_secret

    def exchange(
        self, *, code: str, redirect_uri: str | None = None
    ) -> NotionOAuthGrant:
        """Exchange a one-use code and put returned tokens directly in custody."""
        client_id, client_secret = self._credentials()
        request: dict[str, Any] = {
            "grant_type": "authorization_code",
            "code": code,
        }
        if redirect_uri is not None:
            request["redirect_uri"] = redirect_uri
        try:
            response = dict(self._sdk.oauth.token(client_id, client_secret, **request))
        except Exception:
            raise NotionAPIError(
                "Notion OAuth exchange failed", code="oauth_exchange_failed"
            ) from None

        return self._custody_grant(response)

    def refresh_environment_grant(self) -> NotionOAuthGrant:
        """Refresh an environment-injected credential and custody its replacement.

        SecretStore intentionally exposes no public reveal operation. Automated
        rotation should therefore inject the prior refresh credential from the
        deployment secret manager instead of resolving a SecretRef in app code.
        """
        client_id, client_secret = self._credentials()
        refresh_token = os.environ.get("NOTION_OAUTH_REFRESH_TOKEN")
        if not refresh_token:
            raise NotionAPIError(
                "NOTION_OAUTH_REFRESH_TOKEN is not configured",
                code="oauth_refresh_missing",
            )
        try:
            response = dict(
                self._sdk.oauth.token(
                    client_id,
                    client_secret,
                    grant_type="refresh_token",
                    refresh_token=refresh_token,
                )
            )
        except Exception:
            raise NotionAPIError(
                "Notion OAuth refresh failed", code="oauth_refresh_failed"
            ) from None
        finally:
            del refresh_token

        return self._custody_grant(response)

    def refresh_custodied_grant(self, *, refresh_ref: SecretRef) -> NotionOAuthGrant:
        """Refresh through a tenant-bound custody implementation, never raw material."""

        dispatcher = self._require_credential_dispatcher()
        return dispatcher.refresh(
            organization_id=self._organization_id, refresh_ref=refresh_ref
        )

    def _custody_grant(self, response: dict[str, Any]) -> NotionOAuthGrant:
        """Remove credentials from a provider response and store them atomically."""

        access = response.pop("access_token", None)
        refresh = response.pop("refresh_token", None)
        if not isinstance(access, str) or not access:
            raise NotionAPIError(
                "Notion OAuth response did not contain an access credential",
                code="invalid_oauth_response",
            )

        access_ref: SecretRef | None = None
        try:
            access_ref = self._secret_store.put(
                organization_id=self._organization_id, material=access
            )
            refresh_ref = (
                self._secret_store.put(
                    organization_id=self._organization_id, material=refresh
                )
                if isinstance(refresh, str) and refresh
                else None
            )
        except Exception:
            if access_ref is not None:
                self._secret_store.delete(
                    ref=access_ref, organization_id=self._organization_id
                )
            raise NotionAPIError(
                "Notion OAuth credentials could not be placed in custody",
                code="oauth_custody_failed",
            ) from None
        finally:
            del access, refresh

        return NotionOAuthGrant(
            access_ref=access_ref,
            refresh_ref=refresh_ref,
            bot_id=str(response.get("bot_id", "")),
            workspace_id=str(response.get("workspace_id", "")),
            workspace_name=response.get("workspace_name"),
            duplicated_template_id=response.get("duplicated_template_id"),
            request_id=response.get("request_id"),
        )

    def introspect_environment_token(self) -> dict[str, Any]:
        """Introspect NOTION_TOKEN without accepting it as a public argument."""
        client_id, client_secret = self._credentials()
        token = os.environ.get("NOTION_TOKEN")
        if not token:
            raise NotionAPIError(
                "NOTION_TOKEN is not configured", code="oauth_token_missing"
            )
        try:
            response: dict[str, Any] = self._sdk.oauth.introspect(
                client_id, client_secret, token=token
            )
            return response
        except Exception:
            raise NotionAPIError(
                "Notion OAuth introspection failed", code="oauth_introspection_failed"
            ) from None

    def revoke_environment_token(self) -> dict[str, Any]:
        """Explicitly revoke NOTION_TOKEN without returning or logging it."""
        client_id, client_secret = self._credentials()
        token = os.environ.get("NOTION_TOKEN")
        if not token:
            raise NotionAPIError(
                "NOTION_TOKEN is not configured", code="oauth_token_missing"
            )
        try:
            response: dict[str, Any] = self._sdk.oauth.revoke(
                client_id, client_secret, token=token
            )
            return response
        except Exception:
            raise NotionAPIError(
                "Notion OAuth revocation failed", code="oauth_revocation_failed"
            ) from None

    def introspect_custodied_token(
        self, *, access_ref: SecretRef
    ) -> NotionTokenInspection:
        """Inspect one tenant-bound access reference without exposing its material."""

        return self._require_credential_dispatcher().introspect(
            organization_id=self._organization_id, access_ref=access_ref
        )

    def revoke_custodied_token(self, *, access_ref: SecretRef) -> NotionTokenRevocation:
        """Revoke one tenant-bound access reference without exposing its material."""

        return self._require_credential_dispatcher().revoke(
            organization_id=self._organization_id, access_ref=access_ref
        )

    def _require_credential_dispatcher(self) -> NotionOAuthCredentialDispatcher:
        dispatcher = self._credential_dispatcher
        if dispatcher is None:
            raise NotionAPIError(
                "Notion hosted credential dispatcher is not configured",
                code="oauth_custody_dispatcher_missing",
            )
        return dispatcher
