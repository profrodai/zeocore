"""Explicit integration loading; initialization does not claim live authentication."""

from __future__ import annotations

import os

from pydantic import SecretStr

from zeo_core.integrations.core import IntegrationResult

from .client import HubSpotClient


class HubSpotIntegration:
    integration_id = "hubspot.marketing"
    name = "HubSpot Marketing"
    version = "1.0.0"

    def __init__(self, client: HubSpotClient | None = None) -> None:
        self._client = client

    @property
    def client(self) -> HubSpotClient:
        if self._client is None:
            raise ValueError("HubSpot marketing integration is not initialized")
        return self._client

    def initialize(self) -> IntegrationResult[object]:
        if self._client is None:
            token = os.environ.get("HUBSPOT_ACCESS_TOKEN", "")
            if not token.strip():
                return IntegrationResult.error_result(
                    "Set HUBSPOT_ACCESS_TOKEN to a private-app or OAuth access token"
                )
            self._client = HubSpotClient(SecretStr(token))
        return IntegrationResult.success_result(
            message=(
                "HubSpot client configured; live scopes and account entitlement "
                "are unverified"
            )
        )

    def is_available(self) -> bool:
        return self._client is not None

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


def create_integration() -> HubSpotIntegration:
    return HubSpotIntegration()
