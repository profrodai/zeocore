"""Behavioral proofs for the admitted Notion page-upsert effect."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from tests.connections.adapters.fake_subprocess_runner import FakeSubprocessRunner
from zeo_core.connections import (
    DispatchDisposition,
    EffectDispatchRequest,
    EffectOrchestrator,
    ExactAuthorizationVerifier,
    KeychainEffectDispatcher,
    KeychainEffectReconciler,
    KeychainSecretStore,
    ReconciliationDisposition,
    SQLiteConnectionStore,
    validate_connector_revision,
    validate_operation_request,
)
from zeo_core.contracts.connections import (
    AuthorizationId,
    Connection,
    ConnectionId,
    ConnectionStatus,
    EffectAuthorization,
    ExecutionId,
    IdempotencyKey,
    OrganizationId,
    SecretRef,
)
from zeo_core.integrations.notion import (
    NOTION_PAGE_UPSERT_OPERATION_ID,
    CitedText,
    NotionClientPageUpsertProvider,
    NotionPage,
    NotionPageSnapshot,
    NotionPageUpsertDispatcher,
    NotionPageUpsertReconciler,
    NotionPageUpsertRequest,
    notion_page_upsert_revision,
)

PAGE_ID = "12345678-1234-4234-9234-123456789abc"
DESTINATION_ID = "87654321-4321-4321-8321-cba987654321"


def _request(**changes: object) -> NotionPageUpsertRequest:
    artifact = "a" * 64
    values: dict[str, object] = {
        "meeting_id": "meeting-course",
        "meeting_artifact_sha256": artifact,
        "interpretation_id": "interpretation-course",
        "interpretation_sha256": "b" * 64,
        "destination_parent_id": DESTINATION_ID,
        "title": "Weekly course review",
        "summary": CitedText(
            text="The cohort completed the lab.", source_citations=("transcript:12-18",)
        ),
        "decisions": (
            CitedText(
                text="Keep the next lab local-first.",
                source_citations=("transcript:31-34",),
            ),
        ),
        "actions": (),
        "open_questions": (),
        "full_transcript": None,
        "idempotency_marker": NotionPageUpsertRequest.marker_for(
            meeting_artifact_sha256=artifact,
            destination_parent_id=DESTINATION_ID,
        ),
    }
    values.update(changes)
    return NotionPageUpsertRequest.model_validate(values)


def _dispatch(request: NotionPageUpsertRequest) -> EffectDispatchRequest:
    revision = notion_page_upsert_revision()
    organization_id = OrganizationId(value="org-course")
    connection = Connection(
        connection_id=ConnectionId(value="conn-notion"),
        organization_id=organization_id,
        connector_id=revision.connector_id,
        connector_revision=revision.revision_id,
        provider_application_profile="course-notion",
        verified_external_identity="workspace-course",
        exposed_business_operations=(NOTION_PAGE_UPSERT_OPERATION_ID,),
        secret_handle=SecretRef(handle="zc0-kc:org-course:opaque"),
        status=ConnectionStatus.ACTIVE,
        created_at=datetime(2026, 9, 5, tzinfo=UTC),
    )
    body = request.model_dump_json().encode()
    return EffectDispatchRequest(
        organization_id=organization_id,
        connection=connection,
        connector_revision=revision,
        operation_id=NOTION_PAGE_UPSERT_OPERATION_ID,
        execution_id=ExecutionId(value="exec-notion"),
        idempotency_key=IdempotencyKey(value="idem-notion"),
        request_digest="sha256:" + hashlib.sha256(body).hexdigest(),
        request_body=body,
    )


def _snapshot(
    request: NotionPageUpsertRequest, *, markdown: str | None = None
) -> NotionPageSnapshot:
    return NotionPageSnapshot(
        page_id=PAGE_ID,
        title=request.title,
        idempotency_marker=request.idempotency_marker,
        markdown=request.canonical_markdown() if markdown is None else markdown,
    )


class FakeProvider:
    def __init__(self, matches: tuple[NotionPageSnapshot, ...] = ()) -> None:
        self.matches = matches
        self.created = 0
        self.replaced = 0
        self.finds = 0
        self.raise_after_create = False
        self.created_page_id = PAGE_ID

    def find_by_marker(
        self, *, destination_parent_id: str, idempotency_marker: str
    ) -> tuple[NotionPageSnapshot, ...]:
        assert destination_parent_id == DESTINATION_ID
        assert idempotency_marker.startswith("zeo-notion-upsert:v1:")
        self.finds += 1
        return self.matches

    def create(self, request: NotionPageUpsertRequest) -> NotionPageSnapshot:
        self.created += 1
        self.matches = (
            _snapshot(request).model_copy(update={"page_id": self.created_page_id}),
        )
        if self.raise_after_create:
            raise TimeoutError("lost provider response")
        return self.matches[0]

    def replace_content(
        self, *, page_id: str, request: NotionPageUpsertRequest
    ) -> NotionPageSnapshot:
        assert page_id == PAGE_ID
        self.replaced += 1
        self.matches = (_snapshot(request),)
        return self.matches[0]


def _factory(provider: FakeProvider) -> MagicMock:
    return MagicMock(return_value=provider)


class AcceptingSignatureVerifier:
    def verify_signature(self, authorization: EffectAuthorization) -> bool:
        del authorization
        return True


def test_revision_is_closed_admitted_and_exactly_names_upsert() -> None:
    revision = notion_page_upsert_revision()
    validate_connector_revision(revision)
    assert tuple(op.operation_id for op in revision.operations) == (
        NOTION_PAGE_UPSERT_OPERATION_ID,
    )
    schema = revision.operations[0].request_schema
    assert schema["additionalProperties"] is False
    properties = schema["properties"]
    assert isinstance(properties, dict)
    assert "url" not in properties
    assert "headers" not in properties


def test_request_marker_binds_artifact_and_destination_and_unknown_fields_refuse() -> (
    None
):
    request = _request()
    with pytest.raises(ValidationError, match="must bind"):
        _request(idempotency_marker="zeo-notion-upsert:v1:" + "0" * 64)
    with pytest.raises(ValidationError, match="Extra inputs"):
        NotionPageUpsertRequest.model_validate(
            {**request.model_dump(), "url": "https://example.test"}
        )
    with pytest.raises(ValidationError, match="Notion UUID"):
        _request(destination_parent_id="-" * 32)
    with pytest.raises(ValidationError, match="source citations"):
        _request(summary={"text": "Summary", "source_citations": [""]})


def test_operation_admission_refuses_unknown_top_level_field() -> None:
    revision = notion_page_upsert_revision()
    body = _request().model_dump()
    body["headers"] = {"authorization": "must-not-pass"}
    with pytest.raises(ValueError, match="transport fields"):
        validate_operation_request(
            revision=revision,
            operation_id=NOTION_PAGE_UPSERT_OPERATION_ID,
            request_body=__import__("json").dumps(body).encode(),
        )


def test_create_path_confirms_read_back_and_digest_binds_page() -> None:
    request = _request()
    provider = FakeProvider()
    factory = _factory(provider)
    result = NotionPageUpsertDispatcher(factory)(
        "credential-canary", _dispatch(request)
    )

    assert result.disposition is DispatchDisposition.CONFIRMED
    assert result.confirmation_digest is not None
    assert provider.created == 1
    assert provider.replaced == 0
    factory.assert_called_once_with("credential-canary")
    assert "credential-canary" not in result.model_dump_json()

    other_provider = FakeProvider()
    other_provider.created_page_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    other = NotionPageUpsertDispatcher(_factory(other_provider))(
        "credential-canary", _dispatch(request)
    )
    assert other.confirmation_digest != result.confirmation_digest


def test_existing_exact_page_is_idempotent_without_second_write() -> None:
    request = _request()
    provider = FakeProvider((_snapshot(request),))
    result = NotionPageUpsertDispatcher(_factory(provider))(
        "credential", _dispatch(request)
    )

    assert result.disposition is DispatchDisposition.CONFIRMED
    assert provider.created == 0
    assert provider.replaced == 0


def test_existing_same_title_with_changed_content_is_replaced_once() -> None:
    request = _request()
    provider = FakeProvider((_snapshot(request, markdown="# stale\n"),))
    result = NotionPageUpsertDispatcher(_factory(provider))(
        "credential", _dispatch(request)
    )

    assert result.disposition is DispatchDisposition.CONFIRMED
    assert provider.created == 0
    assert provider.replaced == 1


def test_duplicate_marker_and_title_conflict_fail_safe_before_write() -> None:
    request = _request()
    exact = _snapshot(request)
    duplicate = exact.model_copy(
        update={"page_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}
    )
    duplicate_provider = FakeProvider((exact, duplicate))
    duplicate_result = NotionPageUpsertDispatcher(_factory(duplicate_provider))(
        "credential", _dispatch(request)
    )
    assert duplicate_result.disposition is DispatchDisposition.FAILED_SAFE
    assert duplicate_provider.created == duplicate_provider.replaced == 0

    conflict_provider = FakeProvider((exact.model_copy(update={"title": "Other"}),))
    conflict_result = NotionPageUpsertDispatcher(_factory(conflict_provider))(
        "credential", _dispatch(request)
    )
    assert conflict_result.disposition is DispatchDisposition.FAILED_SAFE
    assert conflict_provider.created == conflict_provider.replaced == 0


def test_lost_create_response_reconciles_by_marker_without_redispatch() -> None:
    request = _request()
    provider = FakeProvider()
    provider.raise_after_create = True
    dispatch = _dispatch(request)
    dispatcher = NotionPageUpsertDispatcher(_factory(provider))

    with pytest.raises(RuntimeError, match="requires reconciliation"):
        dispatcher("credential", dispatch)
    assert provider.created == 1

    result = NotionPageUpsertReconciler(_factory(provider))("credential", dispatch)
    assert result.disposition is ReconciliationDisposition.CONFIRMED
    assert result.confirmation_digest is not None
    assert provider.created == 1
    assert provider.replaced == 0


def test_orchestrator_timeout_reconciles_once_and_replay_never_redispatches(
    tmp_path: Path,
) -> None:
    request = _request()
    dispatch = _dispatch(request)
    now = datetime(2026, 9, 5, 12, tzinfo=UTC)
    store = SQLiteConnectionStore(tmp_path / "notion.sqlite3")
    custody = KeychainSecretStore(
        service_prefix="notion-upsert-test",
        runner=FakeSubprocessRunner(),
        clock=lambda: now,
    )
    ref = custody.put(
        organization_id=dispatch.organization_id, material="credential-canary"
    )
    connection = dispatch.connection.model_copy(update={"secret_handle": ref})
    store.save_connector_revision(
        organization_id=dispatch.organization_id,
        revision=dispatch.connector_revision,
    )
    store.save_connection(
        organization_id=dispatch.organization_id, connection=connection
    )
    authorization = EffectAuthorization(
        authorization_id=AuthorizationId(value="auth-notion"),
        organization_id=dispatch.organization_id,
        seat_id="principal",
        runtime_binding_id="runtime-course",
        packet_id="packet-course",
        attempt_id="attempt-course",
        connection_id=connection.connection_id,
        connector_revision=dispatch.connector_revision.revision_id,
        operation_id=dispatch.operation_id,
        argument_digest=dispatch.request_digest,
        idempotency_key=dispatch.idempotency_key,
        issued_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(minutes=5),
        nonce="notion-nonce",
        audience="zeocore",
        issuer="zeo-go",
        signature="opaque-signature",
    )
    provider = FakeProvider()
    provider.raise_after_create = True
    factory = _factory(provider)
    orchestrator = EffectOrchestrator(
        store=store,
        verifier=ExactAuthorizationVerifier(
            signature_verifier=AcceptingSignatureVerifier(),
            expected_audience="zeocore",
            trusted_issuers=frozenset({"zeo-go"}),
        ),
        clock=lambda: now,
    )
    dispatcher = KeychainEffectDispatcher(
        store=custody, invoke=NotionPageUpsertDispatcher(factory)
    )
    reconciler = KeychainEffectReconciler(
        store=custody, invoke=NotionPageUpsertReconciler(factory)
    )

    result = orchestrator.execute(
        organization_id=dispatch.organization_id,
        connection_id=connection.connection_id,
        connector_revision=dispatch.connector_revision.revision_id,
        operation_id=dispatch.operation_id,
        authorization=authorization,
        execution_id=dispatch.execution_id,
        request_body=dispatch.request_body,
        dispatcher=dispatcher,
        reconciler=reconciler,
    )
    replay = orchestrator.execute(
        organization_id=dispatch.organization_id,
        connection_id=connection.connection_id,
        connector_revision=dispatch.connector_revision.revision_id,
        operation_id=dispatch.operation_id,
        authorization=authorization,
        execution_id=ExecutionId(value="exec-notion-replay"),
        request_body=dispatch.request_body,
        dispatcher=dispatcher,
        reconciler=reconciler,
    )

    assert result.state.value == "SUCCEEDED"
    assert replay.execution_id == dispatch.execution_id
    assert provider.created == 1
    assert provider.replaced == 0
    assert [
        item.state.value
        for item in store.get_execution_history(
            organization_id=dispatch.organization_id,
            execution_id=dispatch.execution_id,
        )
    ][-2:] == ["AMBIGUOUS", "SUCCEEDED"]
    assert b"credential-canary" not in (tmp_path / "notion.sqlite3").read_bytes()
    store.close()


def test_default_provider_disables_sdk_retries_for_effect_calls() -> None:
    constructor = MagicMock()
    wrapper = MagicMock()
    with (
        patch("zeo_core.integrations.notion.upsert.NotionClient", constructor),
        patch(
            "zeo_core.integrations.notion.upsert.NotionClientPageUpsertProvider",
            wrapper,
        ),
    ):
        from zeo_core.integrations.notion.upsert import _default_provider

        _default_provider("credential-canary")

    constructor.assert_called_once_with("credential-canary", max_retries=0)
    wrapper.assert_called_once_with(constructor.return_value)


def test_absent_or_conflicting_reconciliation_stays_unresolved_and_read_only() -> None:
    request = _request()
    for matches in ((), (_snapshot(request, markdown="# partial\n"),)):
        provider = FakeProvider(matches)
        result = NotionPageUpsertReconciler(_factory(provider))(
            "credential", _dispatch(request)
        )
        assert result.disposition is ReconciliationDisposition.UNRESOLVED
        assert provider.created == provider.replaced == 0


def test_wrong_operation_fails_safe_without_constructing_provider() -> None:
    request = _request()
    dispatch = _dispatch(request)
    wrong = dispatch.__class__(
        **{
            **dispatch.__dict__,
            "operation_id": dispatch.operation_id.__class__(value="notion.raw.request"),
        }
    )
    factory = MagicMock()
    result = NotionPageUpsertDispatcher(factory)("credential", wrong)
    assert result.disposition is DispatchDisposition.FAILED_SAFE
    factory.assert_not_called()


def test_concrete_provider_uses_fixed_query_create_and_replace_shapes() -> None:
    request = _request()
    client = MagicMock()
    client.query_data_source.return_value = ([], None)
    page = NotionPage(
        id=PAGE_ID,
        properties={
            "Name": {"title": [{"plain_text": request.title}]},
            "ZEO Idempotency": {
                "rich_text": [{"plain_text": request.idempotency_marker}]
            },
        },
    )
    client.get_page.return_value = page
    client.execute.side_effect = [
        {"id": PAGE_ID},
        {"markdown": request.canonical_markdown()},
        {"object": "page_markdown"},
        {"markdown": request.canonical_markdown()},
    ]
    provider = NotionClientPageUpsertProvider(client)

    assert (
        provider.find_by_marker(
            destination_parent_id=DESTINATION_ID,
            idempotency_marker=request.idempotency_marker,
        )
        == ()
    )
    created = provider.create(request)
    replaced = provider.replace_content(page_id=PAGE_ID, request=request)

    assert created == replaced
    query = client.query_data_source.call_args.kwargs
    assert query["filter"]["rich_text"] == {"equals": request.idempotency_marker}
    create = client.execute.call_args_list[0]
    assert create.kwargs["parent"]["data_source_id"] == DESTINATION_ID
    assert create.kwargs["markdown"] == request.canonical_markdown()
    replace = client.execute.call_args_list[2]
    assert replace.kwargs["type"] == "replace_content"
    assert replace.kwargs["replace_content"] == {
        "new_str": request.canonical_markdown()
    }
