"""Pairing is explicit and reusable device authority stays in secure custody."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from zeo_core.connections.adapters.subprocess_runner import CompletedSubprocess
from zeo_core.integrations.google.drive import DriveDownloadProtocol
from zeo_core.integrations.hosted import (
    ConnectionRequired,
    DeviceSession,
    HostedArtifactDescriptor,
    HostedConnectionManager,
    HostedConnectionStatus,
    HostedConnectionSummary,
    HostedOperationRequest,
    HostedOperationResponse,
    HostedOperationStatus,
    HostedResourceSummary,
    InMemorySecureSessionStore,
    KeychainSecureSessionStore,
    OpaqueConnectionHandle,
    PairingChallenge,
    Ready,
    SecureStoreError,
    ServiceRequirement,
    build_hosted_runtime,
)

CANARY_ACCESS = "access-authority-canary"
CANARY_REFRESH = "refresh-authority-canary"
NOW = datetime(2026, 9, 6, 3, 0, tzinfo=UTC)


def session(now: datetime = NOW) -> DeviceSession:
    return DeviceSession(
        device_id="dev_12345678-1234-4234-9234-123456789012",
        access_token=SecretStr(CANARY_ACCESS),
        refresh_token=SecretStr(CANARY_REFRESH),
        access_expires_at=now + timedelta(minutes=15),
        refresh_expires_at=now + timedelta(days=30),
    )


class KeychainRunner:
    def __init__(self) -> None:
        self.material: str | None = None
        self.argv: list[list[str]] = []
        self.secret_calls: list[tuple[list[str], list[str]]] = []

    def run(self, args: list[str]) -> CompletedSubprocess:
        self.argv.append(args)
        if "find-generic-password" in args:
            if self.material is None:
                return CompletedSubprocess(44, "", "not found")
            return CompletedSubprocess(0, self.material, "")
        if "delete-generic-password" in args:
            self.material = None
            return CompletedSubprocess(0, "", "")
        raise AssertionError(args)

    def run_with_secret_stdin(
        self, args: list[str], *, secret_lines: list[str]
    ) -> CompletedSubprocess:
        self.argv.append(args)
        self.secret_calls.append((args, secret_lines))
        assert secret_lines[0] == secret_lines[1]
        self.material = secret_lines[0]
        return CompletedSubprocess(0, "", "")


class PairingTransportFake:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.challenge = PairingChallenge(
            pairing_id="pair_12345678",
            device_code=SecretStr("device-code-canary"),
            verification_url="https://connect.zeroemployee.org/device",
            user_code="ABCD-EFGH",
            expires_at=NOW + timedelta(minutes=10),
            polling_interval_seconds=5,
        )
        self.session = session(NOW)
        self.invocations = 0
        self.content = b"sku,value\nA,1\n"
        self.connection = HostedConnectionSummary(
            handle=OpaqueConnectionHandle(value="con_google_12345678"),
            service="google.drive",
            external_identity="member@example.com",
            status=HostedConnectionStatus.ACTIVE,
            operations=("google.drive.file.download",),
            resources=(
                HostedResourceSummary(
                    external_id="file-selected",
                    display_name="selected.csv",
                    media_type="text/csv",
                    operations=("google.drive.file.download",),
                ),
            ),
        )

    def invoke(self, request: HostedOperationRequest) -> HostedOperationResponse:
        self.invocations += 1
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

    def begin_pairing(self, *, device_name: str) -> PairingChallenge:
        self.calls.append(f"begin:{device_name}")
        return self.challenge

    def poll_pairing(self, challenge: PairingChallenge) -> DeviceSession:
        self.calls.append(f"poll:{challenge.pairing_id}")
        return self.session

    def refresh_session(self, current: DeviceSession) -> DeviceSession:
        self.calls.append(f"refresh:{current.device_id}")
        return current.model_copy(
            update={"access_token": SecretStr("rotated-access-authority")}
        )

    def list_connections(
        self, current: DeviceSession
    ) -> tuple[HostedConnectionSummary, ...]:
        self.calls.append(f"list:{current.device_id}")
        return (self.connection,)

    def revoke_device(self, current: DeviceSession) -> None:
        self.calls.append(f"revoke:{current.device_id}")


def test_session_and_challenge_redact_every_ordinary_serializer() -> None:
    challenge = PairingTransportFake().challenge
    current = session(NOW)
    rendered = "\n".join(
        (
            repr(challenge),
            str(challenge),
            challenge.model_dump_json(),
            repr(challenge.model_dump()),
            repr(current),
            str(current),
            current.model_dump_json(),
            repr(current.model_dump()),
        )
    )
    assert "device-code-canary" not in rendered
    assert CANARY_ACCESS not in rendered
    assert CANARY_REFRESH not in rendered


def test_keychain_round_trip_uses_stdin_and_never_argv() -> None:
    runner = KeychainRunner()
    store = KeychainSecureSessionStore(runner=runner)
    current = session(NOW)

    assert store.load() is None
    store.save(current)
    restored = store.load()

    assert restored is not None
    assert restored.access_token.get_secret_value() == CANARY_ACCESS
    assert restored.refresh_token.get_secret_value() == CANARY_REFRESH
    assert all(CANARY_ACCESS not in " ".join(argv) for argv in runner.argv)
    assert all(CANARY_REFRESH not in " ".join(argv) for argv in runner.argv)
    assert runner.secret_calls[0][0][-1] == "-w"
    store.delete()
    assert store.load() is None


def test_unsupported_platform_requires_an_explicit_secure_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("zeo_core.integrations.hosted.pairing.sys.platform", "linux")
    with pytest.raises(SecureStoreError, match="secure session storage"):
        KeychainSecureSessionStore()


def test_pairing_and_refresh_are_explicit_actions_then_revocation_clears() -> None:
    transport = PairingTransportFake()
    store = InMemorySecureSessionStore()
    manager = HostedConnectionManager(transport=transport, session_store=store)
    requirement = ServiceRequirement(
        service="google.drive", operations=("google.drive.file.download",)
    )

    assert transport.calls == []
    challenge = manager.begin_pairing(requirement, device_name="Member Mac")
    assert transport.calls == ["begin:Member Mac"]
    assert manager.complete_pairing(challenge) == (transport.connection,)
    assert store.load() == transport.session
    refreshed = manager.refresh_session()
    assert refreshed.access_token.get_secret_value() == "rotated-access-authority"
    manager.revoke_device()
    assert store.load() is None
    assert manager.connections == ()


def test_first_drive_read_resumes_once_after_explicit_pairing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def write_selected(path: str, body: bytes) -> SimpleNamespace:
        Path(path).write_bytes(body)
        return SimpleNamespace(success=True)

    monkeypatch.setattr(
        "zeo_core.core.fs.service.standalone.write_bytes", write_selected
    )
    transport = PairingTransportFake()
    store = InMemorySecureSessionStore()
    runtime = build_hosted_runtime(transport=transport, session_store=store)
    requirement = ServiceRequirement(
        service="google.drive", operations=("google.drive.file.download",)
    )

    before = runtime.services.resolve(requirement)
    assert isinstance(before, ConnectionRequired)
    assert transport.calls == []

    challenge = runtime.connections.begin_pairing(requirement, device_name="Member Mac")
    runtime.connections.complete_pairing(challenge)
    after = runtime.services.resolve(requirement)
    assert isinstance(after, Ready)
    assert isinstance(after.service, DriveDownloadProtocol)
    assert after.service.initialize().success
    destination = tmp_path / "selected.csv"
    result = after.service.download_file("file-selected", str(destination))

    assert result.success
    assert destination.read_bytes() == transport.content
    assert transport.invocations == 1
