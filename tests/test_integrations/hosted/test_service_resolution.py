"""Profile resolution is local, closed-state, and authority preserving."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from zeo_core.integrations.google.drive import DriveDownloadProtocol
from zeo_core.integrations.hosted import (
    ConnectionRequired,
    ConnectionSelectionRequired,
    DeviceSession,
    ExecutionProfile,
    FakeGoogleDriveService,
    HostedArtifactDescriptor,
    HostedConnectionClient,
    HostedConnectionStatus,
    HostedConnectionSummary,
    HostedOperationRequest,
    HostedOperationResponse,
    HostedOperationStatus,
    HostedResourceSummary,
    InMemorySecureSessionStore,
    OpaqueConnectionHandle,
    Ready,
    RepairRequired,
    ResourceSelectionRequired,
    Revoked,
    ServiceRequirement,
    ServiceResolutionStatus,
    ServiceResolver,
    Unavailable,
    UnavailableCode,
)

DRIVE_OPERATION = "google.drive.file.download"
NOW = datetime(2026, 9, 6, 3, 0, tzinfo=UTC)
REQUIREMENT = ServiceRequirement(service="google.drive", operations=(DRIVE_OPERATION,))


def session(now: datetime = NOW) -> DeviceSession:
    return DeviceSession(
        device_id="dev_12345678-1234-4234-9234-123456789012",
        access_token=SecretStr("access-authority-canary"),
        refresh_token=SecretStr("refresh-authority-canary"),
        access_expires_at=now + timedelta(minutes=15),
        refresh_expires_at=now + timedelta(days=30),
    )


class ArtifactTransport:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.requests: list[HostedOperationRequest] = []

    def invoke(self, request: HostedOperationRequest) -> HostedOperationResponse:
        self.requests.append(request)
        return HostedOperationResponse(
            status=HostedOperationStatus.CONFIRMED,
            execution_id="execution-drive",
            artifact=HostedArtifactDescriptor(
                artifact_id="art_selected_file",
                content_sha256="sha256:" + hashlib.sha256(self.content).hexdigest(),
                size_bytes=len(self.content),
                media_type="text/csv",
                filename="selected.csv",
            ),
        )

    def fetch_artifact(self, *, artifact_id: str, max_bytes: int) -> bytes:
        assert artifact_id == "art_selected_file"
        assert max_bytes == len(self.content)
        return self.content


class ExplodingSessionStore:
    def load(self) -> DeviceSession | None:
        raise AssertionError("governed resolution touched paired-device storage")

    def save(self, session: DeviceSession) -> None:
        raise AssertionError(session)

    def delete(self) -> None:
        raise AssertionError("delete called")


class GovernedPort:
    def __init__(self, service: object) -> None:
        self.service = service
        self.calls: list[ServiceRequirement] = []

    def resolve_service(self, requirement: ServiceRequirement) -> object:
        self.calls.append(requirement)
        return self.service


def connection(
    suffix: str = "12345678",
    *,
    status: HostedConnectionStatus = HostedConnectionStatus.ACTIVE,
    resources: bool = True,
) -> HostedConnectionSummary:
    selected = (
        HostedResourceSummary(
            external_id="file-selected",
            display_name="selected.csv",
            media_type="text/csv",
            operations=(DRIVE_OPERATION,),
        ),
    )
    return HostedConnectionSummary(
        handle=OpaqueConnectionHandle(value=f"con_google_{suffix}"),
        service="google.drive",
        external_identity="member@example.com",
        status=status,
        operations=(DRIVE_OPERATION,),
        resources=selected if resources else (),
    )


def run_drive(service: DriveDownloadProtocol, destination: Path) -> str:
    """The business function is identical for every execution placement."""

    assert service.initialize().success
    result = service.download_file("file-selected", str(destination))
    assert result.success
    assert result.content is not None
    return result.content


def test_requirement_uses_the_existing_operation_identity_only() -> None:
    assert REQUIREMENT.operations == ("google.drive.file.download",)
    with pytest.raises(ValueError, match="service identity prefix"):
        ServiceRequirement(
            service="google.drive", operations=("google.drive/files.read@1",)
        )
    assert set(ServiceResolutionStatus) == {
        ServiceResolutionStatus.READY,
        ServiceResolutionStatus.CONNECTION_REQUIRED,
        ServiceResolutionStatus.CONNECTION_SELECTION_REQUIRED,
        ServiceResolutionStatus.RESOURCE_SELECTION_REQUIRED,
        ServiceResolutionStatus.REPAIR_REQUIRED,
        ServiceResolutionStatus.REVOKED,
        ServiceResolutionStatus.UNAVAILABLE,
    }
    assert "ambiguous" not in ServiceResolutionStatus
    assert "approval_required" not in ServiceResolutionStatus


def test_fake_drive_reports_initialization_selection_and_write_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FakeGoogleDriveService({"selected": b"content"})
    assert not service.is_available()
    assert not service.download_file("selected", "out.csv").success
    assert service.initialize().success
    assert service.is_available()
    assert not service.download_file("missing", "out.csv").success
    monkeypatch.setattr(
        "zeo_core.core.fs.service.standalone.write_bytes",
        lambda path, body: SimpleNamespace(success=False),
    )
    assert not service.download_file("selected", "out.csv").success


def test_fake_local_and_hosted_run_the_same_business_function(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = b"sku,value\nA,1\n"
    writes: list[tuple[str, bytes]] = []

    def record_write(path: str, body: bytes) -> SimpleNamespace:
        writes.append((path, body))
        return SimpleNamespace(success=True)

    monkeypatch.setattr("zeo_core.core.fs.service.standalone.write_bytes", record_write)
    fake = FakeGoogleDriveService({"file-selected": content})
    local = FakeGoogleDriveService({"file-selected": content})
    transport = ArtifactTransport(content)
    store = InMemorySecureSessionStore()
    store.save(session(NOW))
    resolvers = (
        ServiceResolver(
            profile=ExecutionProfile.FAKE,
            fake_services={"google.drive": fake},
        ),
        ServiceResolver(
            profile=ExecutionProfile.LOCAL,
            local_services={"google.drive": local},
        ),
        ServiceResolver(
            profile=ExecutionProfile.HOSTED,
            hosted_client=HostedConnectionClient(transport=transport),
            session_store=store,
            hosted_connections=(connection(),),
        ),
    )

    for index, resolver in enumerate(resolvers):
        result = resolver.resolve(REQUIREMENT)
        assert isinstance(result, Ready)
        assert isinstance(result.service, DriveDownloadProtocol)
        destination = f"selected-{index}.csv"
        assert run_drive(result.service, Path(destination)) == destination

    assert writes == [(f"selected-{index}.csv", content) for index in range(3)]
    assert transport.requests[0].connector_revision is None
    assert transport.requests[0].operation_id == DRIVE_OPERATION


def test_hosted_resolution_is_zero_network_and_pairing_state_has_no_challenge() -> None:
    calls = 0

    class NoNetworkTransport(ArtifactTransport):
        def invoke(self, request: HostedOperationRequest) -> HostedOperationResponse:
            nonlocal calls
            calls += 1
            return super().invoke(request)

    store = InMemorySecureSessionStore()
    resolver = ServiceResolver(
        profile=ExecutionProfile.HOSTED,
        hosted_client=HostedConnectionClient(transport=NoNetworkTransport(b"x")),
        session_store=store,
    )

    result = resolver.resolve(REQUIREMENT)

    assert isinstance(result, ConnectionRequired)
    assert result.model_dump() == {
        "service": "google.drive",
        "operations": (DRIVE_OPERATION,),
        "status": ServiceResolutionStatus.CONNECTION_REQUIRED,
    }
    assert "user_code" not in result.model_dump_json()
    assert "verification_url" not in result.model_dump_json()
    assert calls == 0


def test_hosted_resolution_distinguishes_selection_resource_and_health() -> None:
    store = InMemorySecureSessionStore()
    store.save(session(NOW))
    client = HostedConnectionClient(transport=ArtifactTransport(b"x"))

    multiple = ServiceResolver(
        profile=ExecutionProfile.HOSTED,
        hosted_client=client,
        session_store=store,
        hosted_connections=(connection("12345678"), connection("87654321")),
    ).resolve(REQUIREMENT)
    assert isinstance(multiple, ConnectionSelectionRequired)
    selected = ServiceResolver(
        profile=ExecutionProfile.HOSTED,
        hosted_client=client,
        session_store=store,
        hosted_connections=(connection(resources=False),),
    ).resolve(REQUIREMENT)
    assert isinstance(selected, ResourceSelectionRequired)
    repair = ServiceResolver(
        profile=ExecutionProfile.HOSTED,
        hosted_client=client,
        session_store=store,
        hosted_connections=(connection(status=HostedConnectionStatus.REPAIR_REQUIRED),),
    ).resolve(REQUIREMENT)
    assert isinstance(repair, RepairRequired)
    revoked = ServiceResolver(
        profile=ExecutionProfile.HOSTED,
        hosted_client=client,
        session_store=store,
        hosted_connections=(connection(status=HostedConnectionStatus.REVOKED),),
    ).resolve(REQUIREMENT)
    assert isinstance(revoked, Revoked)


def test_secure_store_and_governed_profiles_fail_closed_without_fallback() -> None:
    no_store = ServiceResolver(profile=ExecutionProfile.HOSTED).resolve(REQUIREMENT)
    assert isinstance(no_store, Unavailable)
    assert no_store.code is UnavailableCode.SECURE_STORE_REQUIRED

    paired_store = InMemorySecureSessionStore()
    paired_store.save(session(NOW))
    no_catalog = ServiceResolver(
        profile=ExecutionProfile.HOSTED,
        session_store=paired_store,
        hosted_client=HostedConnectionClient(transport=ArtifactTransport(b"x")),
    ).resolve(REQUIREMENT)
    assert isinstance(no_catalog, Unavailable)
    assert no_catalog.code is UnavailableCode.CONNECTION_CATALOG_REQUIRED

    missing_port = ServiceResolver(
        profile=ExecutionProfile.GOVERNED,
        session_store=ExplodingSessionStore(),
        hosted_client=HostedConnectionClient(transport=ArtifactTransport(b"x")),
    ).resolve(REQUIREMENT)
    assert isinstance(missing_port, Unavailable)
    assert missing_port.code is UnavailableCode.GOVERNED_PORT_REQUIRED

    service = object()
    port = GovernedPort(service)
    governed = ServiceResolver(
        profile=ExecutionProfile.GOVERNED,
        governed_port=port,
        session_store=ExplodingSessionStore(),
        hosted_client=HostedConnectionClient(transport=ArtifactTransport(b"x")),
    ).resolve(REQUIREMENT)
    assert isinstance(governed, Ready)
    assert governed.service is service
    assert port.calls == [REQUIREMENT]
