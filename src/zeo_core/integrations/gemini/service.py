"""Runtime entry point: exact authority, durable broker, custody, then provider."""

from __future__ import annotations

from zeo_core.connections.adapters.macos_keychain import (
    KeychainEffectDispatcher,
    KeychainEffectReconciler,
    KeychainSecretStore,
)
from zeo_core.connections.orchestration import EffectExecutionResult, EffectOrchestrator
from zeo_core.contracts.connections import (
    ConnectionId,
    EffectAuthorization,
    ExecutionId,
    OrganizationId,
)

from .artifacts import ImageArtifactStore
from .models import ImageGenerationRequest
from .operation import (
    OPERATION_ID,
    REVISION_ID,
    ImageGenerationDispatcher,
    ImageGenerationReconciler,
    ProviderFactory,
)
from .transport import GeminiImageTransport


class ImageGenerationService:
    """Does not mint authority or enroll a connection on a caller's behalf.

    The host supplies its configured broker and trusted Keychain store. Sign
    ``request.model_dump_json().encode()`` exactly; no prompt or reference can
    change between authorization and this operation.
    """

    def __init__(
        self,
        *,
        orchestrator: EffectOrchestrator,
        secrets: KeychainSecretStore,
        artifacts: ImageArtifactStore,
        provider_factory: ProviderFactory = GeminiImageTransport,
    ) -> None:
        self._orchestrator = orchestrator
        self._dispatcher = KeychainEffectDispatcher(
            store=secrets,
            invoke=ImageGenerationDispatcher(artifacts, provider_factory),
        )
        self._reconciler = KeychainEffectReconciler(
            store=secrets,
            invoke=ImageGenerationReconciler(artifacts, provider_factory),
        )

    def generate(
        self,
        *,
        organization_id: OrganizationId,
        connection_id: ConnectionId,
        execution_id: ExecutionId,
        authorization: EffectAuthorization | None,
        request: ImageGenerationRequest,
    ) -> EffectExecutionResult:
        """Dispatch at most once; replay/recovery uses the same execution ID."""
        return self._orchestrator.execute(
            organization_id=organization_id,
            connection_id=connection_id,
            execution_id=execution_id,
            connector_revision=REVISION_ID,
            operation_id=OPERATION_ID,
            authorization=authorization,
            request_body=request.model_dump_json().encode(),
            dispatcher=self._dispatcher,
            reconciler=self._reconciler,
        )
