"""Adapter-neutral Google credential and API-client construction ports."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class GoogleCredentialSource(Protocol):
    """Supply one in-memory credential object inside a trusted provider boundary."""

    def get_credentials(self) -> object: ...


@runtime_checkable
class GoogleApiClientFactory(Protocol):
    """Build one fixed Google API client from an in-memory credential object."""

    def build(self, service: str, version: str, *, credentials: object) -> object: ...


class DiscoveryGoogleApiClientFactory:
    """Local default backed by ``googleapiclient.discovery.build``."""

    def build(self, service: str, version: str, *, credentials: object) -> object:
        from googleapiclient.discovery import build

        return build(service, version, credentials=credentials)


__all__ = [
    "DiscoveryGoogleApiClientFactory",
    "GoogleApiClientFactory",
    "GoogleCredentialSource",
]
