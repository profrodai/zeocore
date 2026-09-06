"""Local-only service resolution across fake, local, hosted, and governed profiles."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

from zeo_core.integrations.hosted.client import HostedConnectionClient
from zeo_core.integrations.hosted.pairing import SecureSessionStore, SecureStoreError
from zeo_core.integrations.hosted.profile import (
    ConnectionRequired,
    ConnectionSelectionRequired,
    ExecutionProfile,
    HostedConnectionStatus,
    HostedConnectionSummary,
    OpaqueConnectionHandle,
    Ready,
    RepairRequired,
    ResolutionResult,
    ResourceSelectionRequired,
    Revoked,
    ServiceRequirement,
    Unavailable,
    UnavailableCode,
)
from zeo_core.integrations.hosted.services import (
    HostedGoogleDriveService,
    HostedServiceBinding,
)


@runtime_checkable
class GovernedExecutionPort(Protocol):
    """ZEO Go-owned placement; it must never expose a hosted device session."""

    def resolve_service(self, requirement: ServiceRequirement) -> object: ...


class ServiceResolver:
    """Resolve services from local configuration without performing network I/O."""

    def __init__(
        self,
        *,
        profile: ExecutionProfile,
        fake_services: Mapping[str, object] | None = None,
        local_services: Mapping[str, object] | None = None,
        hosted_client: HostedConnectionClient | None = None,
        session_store: SecureSessionStore | None = None,
        hosted_connections: Sequence[HostedConnectionSummary] | None = None,
        governed_port: GovernedExecutionPort | None = None,
    ) -> None:
        self._profile = profile
        self._fake_services = dict(fake_services or {})
        self._local_services = dict(local_services or {})
        self._hosted_client = hosted_client
        self._session_store = session_store
        self._catalog_loaded = hosted_connections is not None
        self._hosted_connections = tuple(hosted_connections or ())
        self._governed_port = governed_port

    def replace_hosted_connections(
        self, connections: Sequence[HostedConnectionSummary]
    ) -> None:
        """Install a catalog obtained by an explicit pairing/list action."""

        self._catalog_loaded = True
        self._hosted_connections = tuple(connections)

    def resolve(
        self,
        requirement: ServiceRequirement,
        *,
        connection: OpaqueConnectionHandle | None = None,
    ) -> ResolutionResult:
        if self._profile is ExecutionProfile.FAKE:
            return self._resolve_registered(requirement, self._fake_services)
        if self._profile is ExecutionProfile.LOCAL:
            return self._resolve_registered(requirement, self._local_services)
        if self._profile is ExecutionProfile.GOVERNED:
            return self._resolve_governed(requirement)
        return self._resolve_hosted(requirement, connection=connection)

    def _resolve_registered(
        self, requirement: ServiceRequirement, services: Mapping[str, object]
    ) -> ResolutionResult:
        service = services.get(requirement.service)
        if service is None:
            return Unavailable(
                service=requirement.service,
                operations=requirement.operations,
                code=UnavailableCode.SERVICE_NOT_AVAILABLE,
            )
        return Ready(service=service)

    def _resolve_governed(self, requirement: ServiceRequirement) -> ResolutionResult:
        if self._governed_port is None:
            return Unavailable(
                service=requirement.service,
                operations=requirement.operations,
                code=UnavailableCode.GOVERNED_PORT_REQUIRED,
            )
        service = self._governed_port.resolve_service(requirement)
        return Ready(service=service)

    def _resolve_hosted(
        self,
        requirement: ServiceRequirement,
        *,
        connection: OpaqueConnectionHandle | None,
    ) -> ResolutionResult:
        if self._session_store is None:
            return self._unavailable(requirement, UnavailableCode.SECURE_STORE_REQUIRED)
        try:
            session = self._session_store.load()
        except SecureStoreError:
            return self._unavailable(requirement, UnavailableCode.SECURE_STORE_REQUIRED)
        if session is None:
            return ConnectionRequired(
                service=requirement.service, operations=requirement.operations
            )
        if self._hosted_client is None:
            return self._unavailable(
                requirement, UnavailableCode.PROFILE_NOT_CONFIGURED
            )
        if not self._catalog_loaded:
            return self._unavailable(
                requirement, UnavailableCode.CONNECTION_CATALOG_REQUIRED
            )

        candidates = tuple(
            item for item in self._hosted_connections if item.satisfies(requirement)
        )
        if not candidates:
            return ConnectionRequired(
                service=requirement.service, operations=requirement.operations
            )
        selected = self._select(candidates, connection)
        if selected is None:
            return ConnectionSelectionRequired(
                service=requirement.service,
                operations=requirement.operations,
                candidates=candidates,
            )
        state = self._connection_state(requirement, selected)
        if state is not None:
            return state
        service = self._hosted_service(requirement, selected)
        if service is None:
            return self._unavailable(requirement, UnavailableCode.SERVICE_NOT_AVAILABLE)
        return Ready(service=service, connection=selected)

    def _connection_state(
        self,
        requirement: ServiceRequirement,
        selected: HostedConnectionSummary,
    ) -> ResolutionResult | None:
        if selected.status is HostedConnectionStatus.REVOKED:
            return Revoked(
                service=requirement.service,
                operations=requirement.operations,
                connection=selected,
            )
        if selected.status is HostedConnectionStatus.REPAIR_REQUIRED:
            return RepairRequired(
                service=requirement.service,
                operations=requirement.operations,
                connection=selected,
            )
        if selected.status is HostedConnectionStatus.UNAVAILABLE:
            return self._unavailable(requirement, UnavailableCode.SERVICE_NOT_AVAILABLE)
        if self._requires_selected_resource(requirement) and not any(
            set(requirement.operations).intersection(resource.operations)
            for resource in selected.resources
        ):
            return ResourceSelectionRequired(
                service=requirement.service,
                operations=requirement.operations,
                connection=selected,
            )
        return None

    @staticmethod
    def _select(
        candidates: tuple[HostedConnectionSummary, ...],
        connection: OpaqueConnectionHandle | None,
    ) -> HostedConnectionSummary | None:
        if connection is not None:
            return next(
                (item for item in candidates if item.handle == connection), None
            )
        return candidates[0] if len(candidates) == 1 else None

    @staticmethod
    def _requires_selected_resource(requirement: ServiceRequirement) -> bool:
        return "google.drive.file.download" in requirement.operations

    def _hosted_service(
        self,
        requirement: ServiceRequirement,
        connection: HostedConnectionSummary,
    ) -> object | None:
        if requirement.service != "google.drive" or self._hosted_client is None:
            return None
        return HostedGoogleDriveService(
            client=self._hosted_client,
            binding=HostedServiceBinding(connection_id=connection.handle.value),
        )

    @staticmethod
    def _unavailable(
        requirement: ServiceRequirement, code: UnavailableCode
    ) -> Unavailable:
        return Unavailable(
            service=requirement.service,
            operations=requirement.operations,
            code=code,
        )


__all__ = ["GovernedExecutionPort", "ServiceResolver"]
