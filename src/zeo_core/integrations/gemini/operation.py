"""Admitted image generation and read-only recovery of an uncertain attempt."""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Callable

from zeo_core.connections.orchestration import (
    DispatchDisposition,
    EffectDispatchRequest,
    EffectDispatchResult,
    ReconciliationDisposition,
    ReconciliationResult,
)
from zeo_core.contracts.common.enums import EffectKind
from zeo_core.contracts.connections import (
    BusinessOperation,
    ConnectorId,
    ConnectorRevision,
    ConnectorRevisionId,
    IdempotencyMode,
    NormalizedError,
    NormalizedErrorCode,
    OperationId,
    RiskClass,
)

from .artifacts import ImageArtifactStore
from .models import (
    ImageGenerationReceipt,
    ImageGenerationRequest,
    InteractionBinding,
    digest_bytes,
)
from .transport import (
    API_PATH,
    ORIGIN,
    GeminiImageTransport,
    ProviderInteraction,
    ProviderRejectedError,
)

OPERATION_ID = OperationId(value="gemini.generate_reference_image")
REVISION_ID = ConnectorRevisionId(value="gemini.reference-image@1")
ProviderFactory = Callable[[str], GeminiImageTransport]


def image_generation_revision() -> ConnectorRevision:
    """The origin and operation are fixed before caller arguments are admitted."""
    return ConnectorRevision(
        connector_id=ConnectorId(value="gemini"),
        revision_id=REVISION_ID,
        provider="google-gemini",
        authentication_profile="project-api-key",
        permitted_upstream_origins=(ORIGIN,),
        external_account_identity_probe="operator-attested-google-project",
        health_probe="models.get",
        operations=(
            BusinessOperation(
                operation_id=OPERATION_ID,
                effect=EffectKind.WRITE,
                request_schema=ImageGenerationRequest.model_json_schema(),
                response_schema=ImageGenerationReceipt.model_json_schema(),
                allowed_origin=ORIGIN,
                method="POST",
                path_template=API_PATH,
                secret_bindings=("google-project-api-key",),
                redaction_paths=("x-goog-api-key", "provider_response"),
                idempotency_mode=IdempotencyMode.KERNEL_MANAGED,
                reconciliation_strategy="local-evidence-or-get-known-interaction",
                resource_argument="project_id",
            ),
        ),
        request_size_limit_bytes=32_768,
        response_size_limit_bytes=48 * 1024 * 1024,
        timeout_seconds=120,
        credential_injection_point="x-goog-api-key-header",
        redaction_policy="artifact-digests-only-no-raw-provider-body",
        risk_class=RiskClass.HIGH,
        reconciliation_method="local-evidence-or-get-known-interaction",
        provider_error_mapping_version="gemini-image-2026-09-08-v1",
        conformance_fixture_ids=("gemini-reference-image-v1",),
    )


def _request(dispatch: EffectDispatchRequest) -> ImageGenerationRequest:
    if (
        dispatch.operation_id != OPERATION_ID
        or dispatch.connector_revision != image_generation_revision()
    ):
        raise ValueError("image generation operation or revision mismatch")
    if digest_bytes(dispatch.request_body) != dispatch.request_digest:
        raise ValueError("image generation request digest mismatch")
    request = ImageGenerationRequest.model_validate_json(dispatch.request_body)
    if request.project_id not in dispatch.connection.selected_business_resources:
        raise ValueError("image project is not selected on this connection")
    return request


def _binding(
    dispatch: EffectDispatchRequest,
    request: ImageGenerationRequest,
    interaction_id: str,
) -> InteractionBinding:
    return InteractionBinding(
        organization_id=str(dispatch.organization_id),
        execution_id=str(dispatch.execution_id),
        request_digest=dispatch.request_digest,
        project_id=request.project_id,
        interaction_id=interaction_id,
    )


def _confirmation(receipt: ImageGenerationReceipt) -> str:
    return hashlib.sha256(receipt.model_dump_json().encode()).hexdigest()


def _matches(
    binding: InteractionBinding,
    dispatch: EffectDispatchRequest,
    request: ImageGenerationRequest,
) -> bool:
    return (
        binding.organization_id == str(dispatch.organization_id)
        and binding.execution_id == str(dispatch.execution_id)
        and binding.request_digest == dispatch.request_digest
        and binding.project_id == request.project_id
    )


def _complete(
    store: ImageArtifactStore,
    dispatch: EffectDispatchRequest,
    request: ImageGenerationRequest,
    response: ProviderInteraction,
) -> ImageGenerationReceipt:
    if response.status != "completed":
        raise RuntimeError("Image interaction is not complete")
    images = []
    for step in response.steps:
        if step.type != "model_output":
            continue
        for content in step.content:
            if content.get("type") != "image":
                continue
            encoded = content.get("data")
            if content.get("mime_type") != request.output_mime_type or not isinstance(
                encoded, str
            ):
                raise ValueError("Generated image format is not admitted")
            value = base64.b64decode(encoded, validate=True)
            images.append(
                store.put_image(
                    dispatch.organization_id,
                    request.project_id,
                    value,
                    request.output_mime_type,
                )
            )
            if len(images) > 4:
                raise ValueError("Generated image count exceeds contract")
    receipt = ImageGenerationReceipt(
        **_binding(dispatch, request, response.id).model_dump(), images=tuple(images)
    )
    store.complete(receipt)
    return receipt


def _failed(message: str) -> EffectDispatchResult:
    return EffectDispatchResult(
        disposition=DispatchDisposition.FAILED_SAFE,
        normalized_error=NormalizedError(
            code=NormalizedErrorCode.REQUEST_REFUSED, message=message
        ),
    )


class ImageGenerationDispatcher:
    """One provider POST inside KeychainEffectDispatcher after durable admission."""

    def __init__(
        self,
        store: ImageArtifactStore,
        provider_factory: ProviderFactory = GeminiImageTransport,
    ) -> None:
        self._store = store
        self._provider_factory = provider_factory

    def __call__(
        self, material: str, dispatch: EffectDispatchRequest
    ) -> EffectDispatchResult:
        try:
            request = _request(dispatch)
            references = tuple(
                self._store.read_image(
                    dispatch.organization_id, request.project_id, ref
                )
                for ref in request.references
            )
        except Exception:
            return _failed("Image request or pinned references refused before dispatch")
        existing = self._store.receipt(
            dispatch.organization_id, str(dispatch.execution_id)
        )
        if existing is not None:
            if not _matches(existing, dispatch, request):
                raise RuntimeError(
                    "Existing image evidence conflicts with this dispatch"
                )
            return EffectDispatchResult(
                disposition=DispatchDisposition.CONFIRMED,
                confirmation_digest=_confirmation(existing),
            )
        if (
            self._store.interaction(
                dispatch.organization_id, str(dispatch.execution_id)
            )
            is not None
        ):
            raise RuntimeError("Existing provider attempt requires reconciliation")
        try:
            response = self._provider_factory(material).create(request, references)
        except ProviderRejectedError as rejection:
            return _failed(
                f"Image provider rejected the request with HTTP {rejection.status}"
            )
        self._store.bind_interaction(_binding(dispatch, request, response.id))
        if response.status in {"failed", "cancelled"}:
            return _failed(
                "Image provider reported a terminal unsuccessful interaction"
            )
        receipt = _complete(self._store, dispatch, request, response)
        return EffectDispatchResult(
            disposition=DispatchDisposition.CONFIRMED,
            confirmation_digest=_confirmation(receipt),
        )


class ImageGenerationReconciler:
    """Never POST: read local evidence or GET the already-recorded interaction ID."""

    def __init__(
        self,
        store: ImageArtifactStore,
        provider_factory: ProviderFactory = GeminiImageTransport,
    ) -> None:
        self._store = store
        self._provider_factory = provider_factory

    def __call__(
        self, material: str, dispatch: EffectDispatchRequest
    ) -> ReconciliationResult:
        receipt = None
        try:
            request = _request(dispatch)
            receipt = self._store.receipt(
                dispatch.organization_id, str(dispatch.execution_id)
            )
            if receipt is not None and not _matches(receipt, dispatch, request):
                raise ValueError("image evidence mismatch")
            if receipt is None:
                binding = self._store.interaction(
                    dispatch.organization_id, str(dispatch.execution_id)
                )
                if binding is None or not _matches(binding, dispatch, request):
                    raise ValueError("provider identifier unavailable")
                response = self._provider_factory(material).get(binding.interaction_id)
                if response.id != binding.interaction_id:
                    raise ValueError("provider identifier changed")
                if response.status in {"failed", "cancelled"}:
                    return ReconciliationResult(
                        disposition=ReconciliationDisposition.FAILED_SAFE,
                        evidence_digest=hashlib.sha256(
                            (binding.model_dump_json() + response.status).encode()
                        ).hexdigest(),
                        normalized_error=NormalizedError(
                            code=NormalizedErrorCode.REQUEST_REFUSED,
                            message="Provider confirmed unsuccessful interaction",
                        ),
                    )
                receipt = _complete(self._store, dispatch, request, response)
        except Exception:
            receipt = None
        if receipt is None:
            return ReconciliationResult(
                disposition=ReconciliationDisposition.UNRESOLVED,
                evidence_digest=hashlib.sha256(
                    (dispatch.request_digest + "/no-confirmed-image-evidence").encode()
                ).hexdigest(),
            )
        confirmation = _confirmation(receipt)
        return ReconciliationResult(
            disposition=ReconciliationDisposition.CONFIRMED,
            evidence_digest=confirmation,
            confirmation_digest=confirmation,
        )
