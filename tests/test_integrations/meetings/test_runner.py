"""Runtime authority and receipt failures never become a second provider dispatch."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import JsonValue, ValidationError

from zeo_core.integrations.meetings import (
    AdapterAmbiguousError,
    AdapterRefusalError,
    AuthorizationResult,
    InvocationAuthorization,
    InvocationReceipt,
    MeetingRunner,
    RuntimeRefusalError,
    request_digest,
)
from zeo_core.integrations.meetings.contracts import InvocationReconciliation
from zeo_core.integrations.meetings.runner import PreparedOperation

NOW = datetime(2026, 9, 9, 10, tzinfo=UTC)


def authorization(
    payload: dict[str, JsonValue],
    operation: str = "sheets.values.read",
    resource: str = "sheets:sheet:Sheet1!A1:B2",
) -> InvocationAuthorization:
    return InvocationAuthorization(
        invocation_id="invocation_0123456789abcdef",
        meeting_id="meeting_0123456789abcdef",
        organization_id="org-fixture",
        project_id="project-fixture",
        lease_id="lease-fixture",
        attempt_id="attempt-fixture",
        operation=operation,
        resource=resource,
        request_sha256=request_digest(payload),
        idempotency_key="once-fixture",
        authorized_at=NOW,
    )


class Runtime:
    def __init__(self) -> None:
        self.calls: list[InvocationAuthorization] = []
        self.receipts: list[InvocationReceipt] = []
        self.disposition = "EXECUTE"
        self.reconciliation: InvocationReconciliation | None = None
        self.wrong_binding = False
        self.wrong_receipt = False

    def authorize(self, request: InvocationAuthorization) -> AuthorizationResult:
        self.calls.append(request)
        bound = (
            request.model_copy(update={"resource": "other"})
            if self.wrong_binding
            else request
        )
        return AuthorizationResult(
            authorization=bound,
            disposition=self.disposition,
            receipt=self.receipts[-1] if self.receipts else None,
            reconciliation=self.reconciliation,
        )

    def admit_receipt(self, receipt: InvocationReceipt) -> InvocationReceipt:
        self.receipts.append(receipt)
        self.disposition = "REPLAY_FINAL"
        return (
            receipt.model_copy(update={"resource": "wrong"})
            if self.wrong_receipt
            else receipt
        )


class Adapter:
    def __init__(
        self, error: Exception | None = None, object_id: str = "draft-fixture"
    ) -> None:
        self.calls = 0
        self.error = error
        self.object_id = object_id

    def prepare(
        self, authorization: InvocationAuthorization, payload: dict[str, JsonValue]
    ) -> PreparedOperation:
        def call() -> tuple[str, JsonValue]:
            self.calls += 1
            if self.error:
                raise self.error
            return self.object_id, {"total": 10}

        return call


def test_success_and_exact_replay_are_admitted_once() -> None:
    runtime = Runtime()
    adapter = Adapter()
    auth = authorization({"n": 10})
    runner = MeetingRunner(runtime=runtime, adapters=adapter, clock=lambda: NOW)
    first = runner.execute(auth, {"n": 10})
    assert first.outcome == "SUCCEEDED"
    assert runner.execute(auth, {"n": 10}) == first
    assert adapter.calls == 1 and len(runtime.receipts) == 1
    assert first.request_sha256 == request_digest({"n": 10})
    assert "total" not in first.model_dump_json()


@pytest.mark.parametrize(
    "operation,error,expected",
    [
        ("gmail.draft.create", OSError("SECRET-CANARY"), "AMBIGUOUS"),
        ("notion.page.upsert", OSError("SECRET-CANARY"), "AMBIGUOUS"),
        ("gmail.draft.reconcile", AdapterAmbiguousError("unresolved"), "AMBIGUOUS"),
        ("sheets.values.read", OSError("SECRET-CANARY"), "REFUSED"),
        ("gmail.draft.create", AdapterRefusalError("preflight"), "REFUSED"),
    ],
)
def test_error_classification_never_echoes_provider_material(
    operation: str, error: Exception | None, expected: str
) -> None:
    runtime = Runtime()
    adapter = Adapter(error)
    auth = authorization({}, operation)
    result = MeetingRunner(
        runtime=runtime, adapters=adapter, clock=lambda: NOW
    ).execute(auth, {})
    assert (
        result.outcome == expected and "SECRET-CANARY" not in result.model_dump_json()
    )
    assert len(runtime.receipts) == 1 and adapter.calls == 1


def test_unknown_create_identity_is_ambiguous() -> None:
    result = MeetingRunner(
        runtime=Runtime(), adapters=Adapter(object_id=""), clock=lambda: NOW
    ).execute(authorization({}, "gmail.draft.create"), {})
    assert result.outcome == "AMBIGUOUS"


@pytest.mark.parametrize(
    "mode", ["digest", "binding", "reconcile", "missing-replay", "prior-result"]
)
def test_authority_refusals_do_not_dispatch(mode: str) -> None:
    runtime = Runtime()
    adapter = Adapter()
    auth = authorization({})
    if mode == "digest":
        auth = auth.model_copy(update={"request_sha256": "0" * 64})
    if mode == "binding":
        runtime.wrong_binding = True
    if mode == "reconcile":
        runtime.disposition = "RECONCILE"
    if mode == "missing-replay":
        runtime.disposition = "REPLAY_FINAL"
    if mode == "prior-result":
        runtime.receipts.append(
            InvocationReceipt(
                receipt_id="receipt_0123456789abcdef",
                invocation_id=auth.invocation_id,
                operation=auth.operation,
                resource=auth.resource,
                request_sha256=auth.request_sha256,
                outcome="REFUSED",
                observed_at=NOW,
            )
        )
    with pytest.raises(
        (AdapterRefusalError, AdapterAmbiguousError, RuntimeRefusalError)
    ):
        MeetingRunner(runtime=runtime, adapters=adapter).execute(auth, {})
    assert adapter.calls == 0


def test_receipt_admission_failure_never_returns_success() -> None:
    runtime = Runtime()
    runtime.wrong_receipt = True
    adapter = Adapter()
    with pytest.raises(RuntimeRefusalError):
        MeetingRunner(runtime=runtime, adapters=adapter).execute(authorization({}), {})
    assert adapter.calls == 1


def test_reconciled_projection_comes_only_from_matching_runtime_records() -> None:
    runtime = Runtime()
    adapter = Adapter(OSError())
    auth = authorization({}, "gmail.draft.create")
    runner = MeetingRunner(runtime=runtime, adapters=adapter, clock=lambda: NOW)
    assert runner.execute(auth, {}).outcome == "AMBIGUOUS"
    runtime.reconciliation = InvocationReconciliation(
        reconciliation_id="reconciliation_0123456789abcdef",
        invocation_id=auth.invocation_id,
        outcome="SUCCEEDED",
        provider_object_id="draft-recovered",
        evidence_sha256="a" * 64,
        observed_at=NOW,
    )
    final = runner.execute(auth, {})
    assert final.reconciled and final.outcome == "SUCCEEDED" and adapter.calls == 1
    runtime.reconciliation = runtime.reconciliation.model_copy(
        update={"invocation_id": "invocation_fedcba9876543210"}
    )
    with pytest.raises(RuntimeRefusalError):
        runner.execute(auth, {})


@pytest.mark.parametrize(
    "operation", ["gmail.send", "calendar.events.create", "unknown"]
)
def test_operation_set_is_closed(operation: str) -> None:
    with pytest.raises(ValidationError):
        authorization({}, operation)


def test_successful_create_requires_identity() -> None:
    auth = authorization({}, "gmail.draft.create")
    with pytest.raises(ValidationError):
        InvocationReceipt(
            receipt_id="receipt_0123456789abcdef",
            invocation_id=auth.invocation_id,
            operation=auth.operation,
            resource=auth.resource,
            request_sha256=auth.request_sha256,
            outcome="SUCCEEDED",
            observed_at=NOW,
        )


def test_observation_delivered_only_after_exact_receipt_admission() -> None:
    runtime = Runtime()
    observed: list[JsonValue] = []

    def observe(receipt: InvocationReceipt, data: JsonValue) -> None:
        assert runtime.receipts == [receipt]
        observed.append(data)

    runner = MeetingRunner(runtime=runtime, adapters=Adapter(), observe=observe)
    runner.execute(authorization({}), {})
    assert len(observed) == 1
    runner.execute(authorization({}), {})
    assert len(observed) == 1
    runtime = Runtime()
    runtime.wrong_receipt = True
    with pytest.raises(RuntimeRefusalError):
        MeetingRunner(runtime=runtime, adapters=Adapter(), observe=observe).execute(
            authorization({}), {}
        )
    assert len(observed) == 1
