"""Conformance tests for the credential-free ZEOconnect service profile."""

from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from zeo_core.integrations.google.docs import DocsReadProtocol, GoogleDocsService
from zeo_core.integrations.google.drive import DriveDownloadProtocol, GoogleDriveService
from zeo_core.integrations.hosted import (
    HostedArtifactDescriptor,
    HostedAuthorizedTransport,
    HostedBlueskyService,
    HostedClientError,
    HostedConnectionClient,
    HostedGoogleDocsService,
    HostedGoogleDriveService,
    HostedOperationRequest,
    HostedOperationResponse,
    HostedOperationStatus,
    HostedServiceBinding,
    HostedServiceBindings,
    build_services,
)
from zeo_core.integrations.social.bluesky import BlueskyIntegration
from zeo_core.integrations.social.bluesky.protocols import BlueskyIntegrationProtocol


class RecordingTransport:
    def __init__(
        self, responses: list[HostedOperationResponse], artifact_content: bytes = b""
    ) -> None:
        self.responses = responses
        self.artifact_content = artifact_content
        self.requests: list[HostedOperationRequest] = []
        self.fetches: list[tuple[str, int]] = []

    def invoke(self, request: HostedOperationRequest) -> HostedOperationResponse:
        self.requests.append(request)
        return self.responses.pop(0)

    def fetch_artifact(self, *, artifact_id: str, max_bytes: int) -> bytes:
        self.fetches.append((artifact_id, max_bytes))
        return self.artifact_content


def _artifact(content: bytes) -> HostedArtifactDescriptor:
    return HostedArtifactDescriptor(
        artifact_id="art_selected_csv",
        content_sha256="sha256:" + hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        media_type="text/csv",
        filename="selected.csv",
    )


def _response(
    *,
    status: HostedOperationStatus,
    result: object | None = None,
    artifact: HostedArtifactDescriptor | None = None,
    approval_url: str | None = None,
) -> HostedOperationResponse:
    return HostedOperationResponse.model_validate(
        {
            "status": status,
            "execution_id": "execution-1",
            "result": result,
            "artifact": artifact,
            "approval_url": approval_url,
        }
    )


def test_hosted_response_rejects_secret_fields_and_unsafe_filenames() -> None:
    with pytest.raises(ValidationError, match="secret-bearing"):
        _response(
            status=HostedOperationStatus.CONFIRMED,
            result={"nested": {"access_token": "CANARY"}},
        )
    with pytest.raises(ValidationError, match="path segment"):
        HostedArtifactDescriptor(
            artifact_id="art_selected_csv",
            content_sha256="sha256:" + hashlib.sha256(b"csv").hexdigest(),
            size_bytes=3,
            media_type="text/csv",
            filename="../escape.csv",
        )


def test_client_verifies_artifact_bytes_in_both_directions() -> None:
    content = b"sku,value\nA,1\n"
    descriptor = _artifact(content)
    good = HostedConnectionClient(
        transport=RecordingTransport([], artifact_content=content)
    )
    bad = HostedConnectionClient(
        transport=RecordingTransport([], artifact_content=b"tampered")
    )

    assert good.download_artifact(descriptor) == content
    with pytest.raises(HostedClientError, match="size"):
        bad.download_artifact(descriptor)
    same_size_bad = HostedConnectionClient(
        transport=RecordingTransport([], artifact_content=b"x" * len(content))
    )
    with pytest.raises(HostedClientError, match="digest"):
        same_size_bad.download_artifact(descriptor)


def test_drive_download_sends_no_local_path_and_writes_verified_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = b"sku,value\nA,1\n"
    transport = RecordingTransport(
        [
            _response(
                status=HostedOperationStatus.CONFIRMED,
                artifact=_artifact(content),
            )
        ],
        artifact_content=content,
    )
    writes: list[tuple[str, bytes]] = []

    def record_write(path: str, body: bytes) -> SimpleNamespace:
        writes.append((str(path), body))
        return SimpleNamespace(success=True)

    monkeypatch.setattr(
        "zeo_core.integrations.hosted.services.standalone.write_bytes",
        record_write,
    )
    service = HostedGoogleDriveService(
        client=HostedConnectionClient(transport=transport),
        binding=HostedServiceBinding("connection-drive", "drive@1"),
        idempotency_factory=lambda: "idem-drive",
    )
    service.initialize()

    result = service.download_file("file-selected", "/local/lesson.csv")

    assert result.success
    assert writes == [("/local/lesson.csv", content)]
    assert transport.requests[0].arguments == {"file_id": "file-selected"}
    assert "/local/lesson.csv" not in transport.requests[0].model_dump_json()
    assert isinstance(service, DriveDownloadProtocol)


def test_docs_proxy_returns_only_typed_text() -> None:
    transport = RecordingTransport(
        [_response(status=HostedOperationStatus.CONFIRMED, result="Lesson text")]
    )
    service = HostedGoogleDocsService(
        client=HostedConnectionClient(transport=transport),
        binding=HostedServiceBinding("connection-docs", "docs@1"),
        idempotency_factory=lambda: "idem-docs",
    )
    service.initialize()

    result = service.get_document_text("document-selected")

    assert result.success and result.content == "Lesson text"
    assert transport.requests[0].operation_id == "google.docs.document.read"
    assert isinstance(service, DocsReadProtocol)


def test_bluesky_approval_retry_reuses_idempotency_then_confirms() -> None:
    transport = RecordingTransport(
        [
            _response(
                status=HostedOperationStatus.APPROVAL_REQUIRED,
                approval_url="https://connect.zeroemployee.org/approvals/approval-1",
            ),
            _response(
                status=HostedOperationStatus.CONFIRMED,
                result={"uri": "at://did:plc:test/app.bsky.feed.post/1"},
            ),
        ]
    )
    service = HostedBlueskyService(
        client=HostedConnectionClient(transport=transport),
        binding=HostedServiceBinding("connection-bluesky", "bluesky@1"),
        idempotency_factory=lambda: "idem-post",
    )
    service.initialize()

    pending = service.post("A deliberate test post")
    confirmed = service.post("A deliberate test post")

    assert not pending.success
    assert pending.content is not None
    assert pending.content["status"] == "approval_required"
    assert confirmed.success
    assert [item.idempotency_key for item in transport.requests] == [
        "idem-post",
        "idem-post",
    ]
    assert isinstance(service, BlueskyIntegrationProtocol)


def test_factory_builds_protocol_equivalent_local_and_hosted_profiles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ZEOCORE_CONNECTION_PROFILE", raising=False)
    local = build_services()
    transport = RecordingTransport([])
    hosted = build_services(
        profile="hosted",
        hosted_client=HostedConnectionClient(transport=transport),
        hosted_bindings=HostedServiceBindings(
            google_drive=HostedServiceBinding("drive", "drive@1"),
            google_docs=HostedServiceBinding("docs", "docs@1"),
            bluesky=HostedServiceBinding("bluesky", "bluesky@1"),
        ),
    )

    assert isinstance(local.google_drive, GoogleDriveService)
    assert isinstance(local.google_docs, GoogleDocsService)
    assert isinstance(local.bluesky, BlueskyIntegration)
    assert isinstance(hosted.google_drive, DriveDownloadProtocol)
    assert isinstance(hosted.google_docs, DocsReadProtocol)
    assert isinstance(hosted.bluesky, BlueskyIntegrationProtocol)
    assert isinstance(transport, HostedAuthorizedTransport)
    monkeypatch.setenv("ZEOCORE_CONNECTION_PROFILE", "hosted")
    with pytest.raises(ValueError, match="requires"):
        build_services()
    with pytest.raises(ValueError, match="local.*hosted"):
        build_services(profile="unknown")
    with pytest.raises(ValueError, match="requires"):
        build_services(profile="hosted")
