"""Remote service proxies matching ZeoCore's narrow public protocols."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass

from zeo_core.core.fs.service import standalone
from zeo_core.integrations.core import IntegrationResult
from zeo_core.integrations.google.docs import DocsReadProtocol, GoogleDocsService
from zeo_core.integrations.google.drive import DriveDownloadProtocol, GoogleDriveService
from zeo_core.integrations.hosted.client import (
    HostedClientError,
    HostedConnectionClient,
    HostedOperationRequest,
    HostedOperationResponse,
    HostedOperationStatus,
)
from zeo_core.integrations.social.bluesky import (
    BlueskyIntegration,
    BlueskyIntegrationProtocol,
    LinkSpan,
    MentionSpan,
)


@dataclass(frozen=True)
class HostedServiceBinding:
    """One selected remote connection and immutable connector revision."""

    connection_id: str
    connector_revision: str


@dataclass(frozen=True)
class HostedServiceBindings:
    """Bindings required by the alpha connection-bearing service set."""

    google_drive: HostedServiceBinding
    google_docs: HostedServiceBinding
    bluesky: HostedServiceBinding


@dataclass(frozen=True)
class ConnectionServices:
    """Protocol-typed services consumed identically in local and hosted profiles."""

    google_drive: DriveDownloadProtocol
    google_docs: DocsReadProtocol
    bluesky: BlueskyIntegrationProtocol


class _HostedService:
    def __init__(
        self,
        *,
        client: HostedConnectionClient,
        binding: HostedServiceBinding,
        idempotency_factory: Callable[[], str] | None = None,
    ) -> None:
        self._client = client
        self._binding = binding
        self._idempotency_factory = idempotency_factory or (
            lambda: f"zc-hosted-{uuid.uuid4()}"
        )
        self._initialized = False

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def integration_id(self) -> str:
        return self.name.lower().replace(" ", ".")

    def initialize(self) -> IntegrationResult[None]:
        self._initialized = True
        return IntegrationResult.success_result(message=f"{self.name} proxy ready")

    def is_available(self) -> bool:
        return self._initialized

    @property
    def name(self) -> str:
        raise NotImplementedError

    def _invoke(
        self,
        *,
        operation_id: str,
        arguments: dict[str, object],
        idempotency_key: str | None = None,
    ) -> HostedOperationResponse:
        if not self._initialized:
            raise HostedClientError("hosted service is not initialized")
        return self._client.invoke(
            HostedOperationRequest(
                connection_id=self._binding.connection_id,
                connector_revision=self._binding.connector_revision,
                operation_id=operation_id,
                arguments=arguments,
                idempotency_key=idempotency_key or self._idempotency_factory(),
            )
        )


class HostedGoogleDriveService(_HostedService):
    """Selected-file download proxy; local paths never cross the network."""

    @property
    def name(self) -> str:
        return "HostedGoogleDrive"

    def download_file(
        self, remote_id: str, local_path: str | None = None
    ) -> IntegrationResult[str]:
        try:
            response = self._invoke(
                operation_id="google.drive.file.download",
                arguments={"file_id": remote_id},
            )
            if response.status is not HostedOperationStatus.CONFIRMED:
                return _nonconfirmed(response)
            if response.artifact is None:
                return IntegrationResult.error_result(
                    "Hosted Drive response did not contain an artifact"
                )
            content = self._client.download_artifact(response.artifact)
            destination = local_path or response.artifact.filename
            write = standalone.write_bytes(destination, content)
            if not write.success:
                return IntegrationResult.error_result("Failed to write hosted artifact")
            return IntegrationResult.success_result(content=destination)
        except Exception:
            return IntegrationResult.error_result("Hosted Drive download failed safely")


class HostedGoogleDocsService(_HostedService):
    """Selected-document plain-text read proxy."""

    @property
    def name(self) -> str:
        return "HostedGoogleDocs"

    def get_document_text(self, document_id: str) -> IntegrationResult[str]:
        try:
            response = self._invoke(
                operation_id="google.docs.document.read",
                arguments={"document_id": document_id},
            )
            if response.status is not HostedOperationStatus.CONFIRMED:
                return _nonconfirmed(response)
            if not isinstance(response.result, str):
                return IntegrationResult.error_result(
                    "Hosted Docs response did not contain text"
                )
            return IntegrationResult.success_result(content=response.result)
        except Exception:
            return IntegrationResult.error_result("Hosted Docs read failed safely")


class HostedBlueskyService(_HostedService):
    """Confirmed public-post proxy retaining one idempotency key through approval."""

    def __init__(
        self,
        *,
        client: HostedConnectionClient,
        binding: HostedServiceBinding,
        idempotency_factory: Callable[[], str] | None = None,
    ) -> None:
        super().__init__(
            client=client,
            binding=binding,
            idempotency_factory=idempotency_factory,
        )
        self._pending_keys: dict[str, str] = {}

    @property
    def name(self) -> str:
        return "HostedBluesky"

    def post(
        self,
        text: str,
        links: list[LinkSpan] | None = None,
        mentions: list[MentionSpan] | None = None,
    ) -> IntegrationResult[dict[str, object]]:
        arguments: dict[str, object] = {
            "text": text,
            "links": [asdict(item) for item in links or ()],
            "mentions": [asdict(item) for item in mentions or ()],
        }
        canonical_arguments = json.dumps(
            arguments, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        digest = hashlib.sha256(canonical_arguments).hexdigest()
        key = self._pending_keys.setdefault(digest, self._idempotency_factory())
        try:
            response = self._invoke(
                operation_id="bluesky.post.create",
                arguments=arguments,
                idempotency_key=key,
            )
        except Exception:
            return IntegrationResult.error_result("Hosted Bluesky post failed safely")
        if response.status is HostedOperationStatus.APPROVAL_REQUIRED:
            return IntegrationResult(
                success=False,
                error="Browser approval required",
                message="Open the exact preview before publishing",
                content={
                    "status": response.status.value,
                    "execution_id": response.execution_id,
                    "approval_url": str(response.approval_url),
                },
            )
        self._pending_keys.pop(digest, None)
        if response.status is not HostedOperationStatus.CONFIRMED:
            return _nonconfirmed(response)
        if not isinstance(response.result, dict):
            return IntegrationResult.error_result(
                "Hosted Bluesky response did not contain a receipt"
            )
        return IntegrationResult.success_result(content=dict(response.result))


def build_services(
    *,
    profile: str | None = None,
    hosted_client: HostedConnectionClient | None = None,
    hosted_bindings: HostedServiceBindings | None = None,
) -> ConnectionServices:
    """Build the maintained connection-bearing service profile."""

    selected_profile = profile or os.getenv("ZEOCORE_CONNECTION_PROFILE", "local")
    if selected_profile == "local":
        return ConnectionServices(
            google_drive=GoogleDriveService(),
            google_docs=GoogleDocsService(),
            bluesky=BlueskyIntegration(),
        )
    if selected_profile != "hosted":
        raise ValueError("connection profile must be 'local' or 'hosted'")
    if hosted_client is None or hosted_bindings is None:
        raise ValueError("hosted profile requires a client and service bindings")
    return ConnectionServices(
        google_drive=HostedGoogleDriveService(
            client=hosted_client, binding=hosted_bindings.google_drive
        ),
        google_docs=HostedGoogleDocsService(
            client=hosted_client, binding=hosted_bindings.google_docs
        ),
        bluesky=HostedBlueskyService(
            client=hosted_client, binding=hosted_bindings.bluesky
        ),
    )


def _nonconfirmed(response: HostedOperationResponse) -> IntegrationResult:
    return IntegrationResult.error_result(
        f"Hosted operation ended {response.status.value}"
    )


__all__ = [
    "ConnectionServices",
    "HostedBlueskyService",
    "HostedGoogleDocsService",
    "HostedGoogleDriveService",
    "HostedServiceBinding",
    "HostedServiceBindings",
    "build_services",
]
