"""Kit credential configuration without implicit network or authentication claims."""

from __future__ import annotations

import os

from pydantic import SecretStr

from zeo_core.integrations.core import IntegrationResult

from .client import KitClient


class KitIntegration:
    integration_id = "kit.marketing"
    name = "Kit Marketing"
    version = "1.0.0"

    def __init__(self, client: KitClient | None = None) -> None:
        self._client = client

    @property
    def client(self) -> KitClient:
        if self._client is None:
            raise ValueError("Kit integration is not initialized")
        return self._client

    def initialize(self) -> IntegrationResult[object]:
        if self._client is None:
            key, token = (
                os.environ.get("KIT_API_KEY", ""),
                os.environ.get("KIT_ACCESS_TOKEN", ""),
            )
            if bool(key.strip()) == bool(token.strip()):
                return IntegrationResult.error_result(
                    "Set exactly one of KIT_API_KEY or KIT_ACCESS_TOKEN"
                )
            self._client = KitClient(
                SecretStr(key) if key.strip() else None,
                access_token=SecretStr(token) if token.strip() else None,
            )
        return IntegrationResult.success_result(
            message=(
                "Kit client configured; live account entitlement and "
                "authentication unverified"
            )
        )

    def is_available(self) -> bool:
        return self._client is not None

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


def create_integration() -> KitIntegration:
    return KitIntegration()
