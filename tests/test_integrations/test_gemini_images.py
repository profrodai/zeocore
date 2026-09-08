"""Real broker/custody/artifact flow against an offline provider boundary."""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from tests.connections.adapters.fake_subprocess_runner import FakeSubprocessRunner
from tests.connections.test_effect_orchestration import AcceptingSignatureVerifier
from zeo_core.connections import (
    EffectExecutionResult,
    EffectOrchestrator,
    ExactAuthorizationVerifier,
    KeychainSecretStore,
    SQLiteConnectionStore,
)
from zeo_core.contracts.connections import (
    AuthorizationId,
    Connection,
    ConnectionId,
    ConnectionStatus,
    EffectAuthorization,
    ExecutionId,
    ExecutionState,
    IdempotencyKey,
    OrganizationId,
)
from zeo_core.integrations.gemini import (
    OPERATION_ID,
    REVISION_ID,
    ImageArtifactStore,
    ImageGenerationRequest,
    ImageGenerationService,
    image_generation_revision,
)
from zeo_core.integrations.gemini.models import digest_bytes
from zeo_core.integrations.gemini.transport import (
    API_PATH,
    ORIGIN,
    GeminiImageTransport,
)

# Real one-pixel PNG, fixed independently of the implementation under test.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8A"
    "AwMCAO+/l9sAAAAASUVORK5CYII="
)
NOW = datetime(2026, 9, 8, 12, tzinfo=UTC)
ORG = OrganizationId(value="org-image-test")
CONNECTION = ConnectionId(value="connection-image-test")
EXECUTION = ExecutionId(value="execution-image-test")


class Harness:
    """Synthetic authorization verifier is confined to tests, never live use."""

    def __init__(self, root: Path, mode: str = "complete") -> None:
        self.root = root
        self.mode = mode
        self.calls: list[str] = []
        self.store = SQLiteConnectionStore(path=root / "broker.sqlite3")
        self.artifacts = ImageArtifactStore(root / "artifacts")
        self.reference = self.artifacts.put_image(ORG, "ducktyper", PNG, "image/png")
        self.request = ImageGenerationRequest(
            project_id="ducktyper",
            prompt="Keep the canonical design.",
            references=(self.reference,),
        )
        self.runner = FakeSubprocessRunner()
        secrets = KeychainSecretStore(service_prefix="image-test", runner=self.runner)
        handle = secrets.put(organization_id=ORG, material="synthetic-image-secret")
        revision = image_generation_revision()
        connection = Connection(
            organization_id=ORG,
            connection_id=CONNECTION,
            connector_id=revision.connector_id,
            connector_revision=REVISION_ID,
            provider_application_profile="offline-test",
            verified_external_identity="synthetic-test-project",
            exposed_business_operations=(OPERATION_ID,),
            selected_business_resources=("ducktyper",),
            secret_handle=handle,
            status=ConnectionStatus.ACTIVE,
            created_at=NOW,
        )
        self.store.save_connector_revision(organization_id=ORG, revision=revision)
        self.store.save_connection(organization_id=ORG, connection=connection)
        self.authorization = EffectAuthorization(
            authorization_id=AuthorizationId(value="auth-image-test"),
            organization_id=ORG,
            seat_id="principal",
            runtime_binding_id="test-runtime",
            packet_id="test-packet",
            attempt_id="test-attempt",
            connection_id=CONNECTION,
            connector_revision=REVISION_ID,
            operation_id=OPERATION_ID,
            argument_digest=digest_bytes(self.request.model_dump_json().encode()),
            idempotency_key=IdempotencyKey(value="test-image-idempotency"),
            issued_at=NOW - timedelta(minutes=1),
            expires_at=NOW + timedelta(minutes=5),
            nonce="test-image-nonce",
            audience="zeocore",
            issuer="test-only",
            signature="synthetic-not-a-live-authorization",
        )
        self.service = ImageGenerationService(
            orchestrator=EffectOrchestrator(
                store=self.store,
                verifier=ExactAuthorizationVerifier(
                    signature_verifier=AcceptingSignatureVerifier(),
                    expected_audience="zeocore",
                    trusted_issuers=frozenset({"test-only"}),
                ),
                clock=lambda: NOW,
            ),
            secrets=secrets,
            artifacts=self.artifacts,
            provider_factory=lambda material: GeminiImageTransport(
                material, transport=httpx.MockTransport(self.provider)
            ),
        )

    def provider(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request.method)
        assert request.headers["x-goog-api-key"] == "synthetic-image-secret"
        assert str(request.url).startswith(ORIGIN + API_PATH)
        execution = self.store.get_execution(
            organization_id=ORG, execution_id=EXECUTION
        )
        assert execution is not None
        if request.method == "POST":
            assert execution.state is ExecutionState.DISPATCH_STARTED
            assert request.headers["content-type"] == "application/json"
            payload = json.loads(request.content)
            assert payload["store"] is True
            assert base64.b64decode(payload["input"][1]["data"]) == PNG
            assert "project_id" not in payload
        else:
            assert str(request.url) == ORIGIN + API_PATH + "/interaction_1"
        if self.mode == "lost":
            raise httpx.ReadTimeout("synthetic-image-secret in forbidden error")
        if self.mode in {"401", "302"}:
            return httpx.Response(int(self.mode), text="synthetic-image-secret")
        if self.mode in {"recover", "failed"} and request.method == "POST":
            return httpx.Response(
                200, json={"id": "interaction_1", "status": "in_progress"}
            )
        if self.mode == "failed":
            return httpx.Response(200, json={"id": "interaction_1", "status": "failed"})
        content = {
            "type": "image",
            "mime_type": "image/png",
            "data": base64.b64encode(PNG).decode(),
        }
        return httpx.Response(
            200,
            json={
                "id": "interaction_1",
                "status": "completed",
                "steps": [{"type": "user_input", "content": [content]}]
                + (
                    []
                    if self.mode == "echo"
                    else [{"type": "model_output", "content": [content]}]
                ),
            },
        )

    def run(self, *, authorized: bool = True) -> EffectExecutionResult:
        return self.service.generate(
            organization_id=ORG,
            connection_id=CONNECTION,
            execution_id=EXECUTION,
            authorization=self.authorization if authorized else None,
            request=self.request,
        )


def test_authorized_flow_persists_actual_bytes_and_replays_without_post(
    tmp_path: Path,
) -> None:
    h = Harness(tmp_path)
    assert h.run().state is ExecutionState.SUCCEEDED
    assert h.run().state is ExecutionState.SUCCEEDED
    assert h.calls == ["POST"]
    receipt = h.artifacts.receipt(ORG, str(EXECUTION))
    assert receipt is not None and receipt.qualification == "UNREVIEWED"
    assert receipt.request_digest == h.authorization.argument_digest
    assert h.artifacts.read_image(ORG, "ducktyper", receipt.images[0]) == PNG
    assert "synthetic-image-secret" not in receipt.model_dump_json()
    assert "synthetic-image-secret" not in repr(h.runner.calls)


@pytest.mark.parametrize("mode", ["lost", "302", "echo"])
def test_ambiguous_response_never_reposts(tmp_path: Path, mode: str) -> None:
    h = Harness(tmp_path, mode)
    assert h.run().state is ExecutionState.AMBIGUOUS
    assert h.run().state is ExecutionState.AMBIGUOUS
    assert h.calls.count("POST") == 1
    assert h.artifacts.receipt(ORG, str(EXECUTION)) is None


@pytest.mark.parametrize(
    "mode, expected",
    [("recover", ExecutionState.SUCCEEDED), ("failed", ExecutionState.FAILED_SAFE)],
)
def test_known_interaction_recovers_by_get(
    tmp_path: Path, mode: str, expected: ExecutionState
) -> None:
    h = Harness(tmp_path, mode)
    assert h.run().state is expected
    assert h.calls == ["POST", "GET"]


def test_auth_missing_or_changed_prompt_never_resolves_credentials(
    tmp_path: Path,
) -> None:
    h = Harness(tmp_path)
    calls = len(h.runner.calls)
    assert h.run(authorized=False).state is ExecutionState.REFUSED
    h.request = h.request.model_copy(update={"prompt": "Different billable intent"})
    assert h.run().state is ExecutionState.REFUSED
    assert len(h.runner.calls) == calls
    assert not h.calls


def test_project_scope_and_missing_reference_refuse_before_post(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    h.request = h.request.model_copy(update={"project_id": "another-project"})
    h.authorization = h.authorization.model_copy(
        update={"argument_digest": digest_bytes(h.request.model_dump_json().encode())}
    )
    assert h.run().state is ExecutionState.FAILED_SAFE
    assert not h.calls


def test_explicit_auth_rejection_is_sanitized_and_not_retried(tmp_path: Path) -> None:
    h = Harness(tmp_path, "401")
    assert h.run().state is ExecutionState.FAILED_SAFE
    assert h.calls == ["POST"]
    execution = h.store.get_execution(organization_id=ORG, execution_id=EXECUTION)
    assert execution is not None
    assert "synthetic-image-secret" not in execution.model_dump_json()


def test_store_refuses_cross_scope_symlinks_and_tampering(tmp_path: Path) -> None:
    store = ImageArtifactStore(tmp_path / "images")
    reference = store.put_image(ORG, "ducktyper", PNG, "image/png")
    with pytest.raises(FileNotFoundError):
        store.read_image(OrganizationId(value="other-org"), "ducktyper", reference)
    with pytest.raises(FileNotFoundError):
        store.read_image(ORG, "other-project", reference)
    org_path = store.root / hashlib.sha256(str(ORG).encode()).hexdigest()
    other_path = store.root / hashlib.sha256(b"other-org").hexdigest()
    other_path.symlink_to(org_path, target_is_directory=True)
    with pytest.raises(ValueError, match="path escapes"):
        store.read_image(OrganizationId(value="other-org"), "ducktyper", reference)
    file = next(org_path.rglob(reference.digest[7:]))
    file.write_bytes(b"x" * len(PNG))
    with pytest.raises(ValueError, match="digest changed"):
        store.read_image(ORG, "ducktyper", reference)


def test_closed_request_and_duplicate_reference_refused(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    value = h.request.model_dump()
    with pytest.raises(ValidationError):
        ImageGenerationRequest.model_validate({**value, "url": "https://example.com"})
    with pytest.raises(ValidationError):
        ImageGenerationRequest.model_validate(
            {**value, "references": [h.reference, h.reference]}
        )


def test_transport_error_context_contains_no_provider_secret() -> None:
    def fail(_request: httpx.Request) -> httpx.Response:
        raise RuntimeError("secret-from-transport")

    provider = GeminiImageTransport("synthetic", transport=httpx.MockTransport(fail))
    with pytest.raises(RuntimeError) as error:
        provider.get("interaction_1")
    assert error.value.__context__ is None
    assert "secret-from-transport" not in str(error.value)
