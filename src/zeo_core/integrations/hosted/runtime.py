"""Small composition root for the native managed execution profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from zeo_core.integrations.hosted.client import (
    HostedAuthorizedTransport,
    HostedConnectionClient,
)
from zeo_core.integrations.hosted.pairing import (
    HostedConnectionManager,
    PairingTransport,
    SecureSessionStore,
)
from zeo_core.integrations.hosted.profile import ExecutionProfile
from zeo_core.integrations.hosted.resolution import ServiceResolver


@runtime_checkable
class ManagedHostedTransport(HostedAuthorizedTransport, PairingTransport, Protocol):
    """One client-side transport implementing the frozen member API."""


@dataclass(frozen=True)
class HostedRuntime:
    """The two explicit surfaces: inert resolution and networked connection actions."""

    services: ServiceResolver
    connections: HostedConnectionManager


def build_hosted_runtime(
    *, transport: ManagedHostedTransport, session_store: SecureSessionStore
) -> HostedRuntime:
    """Compose a hosted runtime without contacting ZEOconnect."""

    resolver = ServiceResolver(
        profile=ExecutionProfile.HOSTED,
        hosted_client=HostedConnectionClient(transport=transport),
        session_store=session_store,
    )
    connections = HostedConnectionManager(
        transport=transport,
        session_store=session_store,
        catalog_sink=resolver.replace_hosted_connections,
    )
    return HostedRuntime(services=resolver, connections=connections)


__all__ = ["HostedRuntime", "ManagedHostedTransport", "build_hosted_runtime"]
