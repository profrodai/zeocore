"""Behavioral proofs for organization-scoped SQLite connection persistence."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import uuid
from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from zeo_core.connections import (
    ConnectionStoreError,
    SQLiteConnectionStore,
)
from zeo_core.contracts.connections import (
    BrokerExecutionStore,
    ConfirmationEvidenceRef,
    Connection,
    ConnectionStore,
    ConnectorRevision,
    Execution,
    ExecutionId,
    ExecutionReceipt,
    ExecutionState,
    NormalizedError,
    NormalizedErrorCode,
    OrganizationId,
)

_EVIDENCE_UUID = uuid.UUID("12345678-1234-4234-9234-123456789abc")


@pytest.fixture
def store(tmp_path: Path) -> Generator[SQLiteConnectionStore]:
    database = SQLiteConnectionStore(
        tmp_path / "connections.sqlite3", uuid_factory=lambda: _EVIDENCE_UUID
    )
    yield database
    database.close()


def transition(execution: Execution, state: ExecutionState, at: datetime) -> Execution:
    data = execution.model_dump()
    data.update(
        state=state,
        updated_at=at,
        completed_at=at
        if state
        in {
            ExecutionState.SUCCEEDED,
            ExecutionState.FAILED_SAFE,
            ExecutionState.REFUSED,
        }
        else None,
    )
    return Execution.model_validate(data)


def persist_path_to_dispatch(
    store: SQLiteConnectionStore, execution: Execution, now: datetime
) -> Execution:
    store.save_execution(organization_id=execution.organization_id, execution=execution)
    current = execution
    for offset, state in enumerate(
        (
            ExecutionState.AUTHORIZATION_VERIFIED,
            ExecutionState.PREPARED,
            ExecutionState.DISPATCH_STARTED,
        ),
        start=1,
    ):
        current = transition(current, state, now + timedelta(seconds=offset))
        store.save_execution(organization_id=current.organization_id, execution=current)
    return current


def ambiguous_error() -> NormalizedError:
    return NormalizedError(
        code=NormalizedErrorCode.RESULT_AMBIGUOUS,
        message="Provider effect could not be confirmed",
    )


def test_store_satisfies_protocol_and_database_is_private(
    tmp_path: Path,
) -> None:
    path = tmp_path / "connections.sqlite3"
    database = SQLiteConnectionStore(path)
    try:
        assert isinstance(database, ConnectionStore)
        assert isinstance(database, BrokerExecutionStore)
        assert path.stat().st_mode & 0o777 == 0o600
    finally:
        database.close()


def test_connection_round_trip_preserves_deliberate_secret_handle(
    store: SQLiteConnectionStore, connection: Connection
) -> None:
    store.save_connection(
        organization_id=connection.organization_id, connection=connection
    )

    loaded = store.get_connection(
        organization_id=connection.organization_id,
        connection_id=connection.connection_id,
    )

    assert loaded == connection
    assert loaded is not None
    assert loaded.secret_handle.handle == connection.secret_handle.handle


def test_cross_organization_reads_return_nothing(
    store: SQLiteConnectionStore,
    connection: Connection,
    connector_revision: ConnectorRevision,
    created_execution: Execution,
) -> None:
    store.save_connection(
        organization_id=connection.organization_id, connection=connection
    )
    store.save_connector_revision(
        organization_id=connection.organization_id, revision=connector_revision
    )
    store.save_execution(
        organization_id=created_execution.organization_id,
        execution=created_execution,
    )
    other = OrganizationId(value="org-2")

    assert (
        store.get_connection(
            organization_id=other, connection_id=connection.connection_id
        )
        is None
    )
    assert (
        store.get_connector_revision(
            organization_id=other, revision_id=connector_revision.revision_id
        )
        is None
    )
    assert (
        store.get_execution(
            organization_id=other, execution_id=created_execution.execution_id
        )
        is None
    )
    assert (
        store.get_receipts_for_execution(
            organization_id=other, execution_id=created_execution.execution_id
        )
        == ()
    )


def test_same_idempotency_identity_is_independent_between_organizations(
    store: SQLiteConnectionStore, created_execution: Execution
) -> None:
    second = created_execution.model_copy(
        update={"organization_id": OrganizationId(value="org-2")}
    )

    store.save_execution(
        organization_id=created_execution.organization_id,
        execution=created_execution,
    )
    store.save_execution(organization_id=second.organization_id, execution=second)

    assert (
        store.get_execution(
            organization_id=created_execution.organization_id,
            execution_id=created_execution.execution_id,
        )
        == created_execution
    )
    assert (
        store.get_execution(
            organization_id=second.organization_id,
            execution_id=second.execution_id,
        )
        == second
    )


def test_payload_cannot_override_trusted_organization(
    store: SQLiteConnectionStore, connection: Connection
) -> None:
    with pytest.raises(ConnectionStoreError, match="organization mismatch"):
        store.save_connection(
            organization_id=OrganizationId(value="org-2"), connection=connection
        )


def test_connector_revision_is_immutable(
    store: SQLiteConnectionStore,
    connector_revision: ConnectorRevision,
    connection: Connection,
) -> None:
    store.save_connector_revision(
        organization_id=connection.organization_id, revision=connector_revision
    )
    changed = connector_revision.model_copy(update={"provider": "different"})

    with pytest.raises(ConnectionStoreError, match="immutable"):
        store.save_connector_revision(
            organization_id=connection.organization_id, revision=changed
        )


def test_execution_history_is_append_only_and_transition_checked(
    store: SQLiteConnectionStore, created_execution: Execution, now: datetime
) -> None:
    dispatched = persist_path_to_dispatch(store, created_execution, now)

    assert [
        item.state
        for item in store.get_execution_history(
            organization_id=created_execution.organization_id,
            execution_id=created_execution.execution_id,
        )
    ] == [
        ExecutionState.CREATED,
        ExecutionState.AUTHORIZATION_VERIFIED,
        ExecutionState.PREPARED,
        ExecutionState.DISPATCH_STARTED,
    ]
    invalid = transition(dispatched, ExecutionState.REFUSED, now + timedelta(seconds=4))
    with pytest.raises(ConnectionStoreError, match="transition is not allowed"):
        store.save_execution(organization_id=invalid.organization_id, execution=invalid)


def test_first_persisted_execution_must_be_created(
    store: SQLiteConnectionStore, created_execution: Execution, now: datetime
) -> None:
    prepared = transition(created_execution, ExecutionState.PREPARED, now)
    with pytest.raises(ConnectionStoreError, match="first persisted state"):
        store.save_execution(
            organization_id=prepared.organization_id, execution=prepared
        )


def test_idempotency_identity_is_unique(
    store: SQLiteConnectionStore, created_execution: Execution
) -> None:
    store.save_execution(
        organization_id=created_execution.organization_id,
        execution=created_execution,
    )
    duplicate = created_execution.model_copy(
        update={"execution_id": ExecutionId(value="exec-2")}
    )

    with pytest.raises(ConnectionStoreError, match="idempotency identity"):
        store.save_execution(
            organization_id=duplicate.organization_id, execution=duplicate
        )


def test_success_receipt_requires_persisted_evidence_provenance(
    store: SQLiteConnectionStore, created_execution: Execution, now: datetime
) -> None:
    dispatched = persist_path_to_dispatch(store, created_execution, now)
    succeeded_at = now + timedelta(seconds=4)
    succeeded = transition(dispatched, ExecutionState.SUCCEEDED, succeeded_at)
    store.save_execution(organization_id=succeeded.organization_id, execution=succeeded)
    evidence_ref = ConfirmationEvidenceRef(value=f"zeo-evidence:v1:{_EVIDENCE_UUID}")
    receipt = ExecutionReceipt(
        execution_id=succeeded.execution_id,
        organization_id=succeeded.organization_id,
        connection_id=succeeded.connection_id,
        final_state=ExecutionState.SUCCEEDED,
        recorded_at=succeeded_at,
        dispatch_started_at=dispatched.updated_at,
        confirmation_evidence_ref=evidence_ref,
    )

    with pytest.raises(ConnectionStoreError, match="provenance"):
        store.save_receipt(organization_id=succeeded.organization_id, receipt=receipt)

    store.save_confirmation_evidence(
        organization_id=succeeded.organization_id,
        execution_id=succeeded.execution_id,
        observed_at=succeeded_at,
        confirmation_digest="a" * 64,
    )
    store.save_receipt(organization_id=succeeded.organization_id, receipt=receipt)

    assert store.get_receipts_for_execution(
        organization_id=succeeded.organization_id,
        execution_id=succeeded.execution_id,
    ) == (receipt,)


def test_ambiguity_is_retained_when_resolution_is_appended(
    store: SQLiteConnectionStore, created_execution: Execution, now: datetime
) -> None:
    dispatched = persist_path_to_dispatch(store, created_execution, now)
    ambiguous_at = now + timedelta(seconds=4)
    ambiguous = transition(dispatched, ExecutionState.AMBIGUOUS, ambiguous_at)
    store.save_execution(organization_id=ambiguous.organization_id, execution=ambiguous)
    first = ExecutionReceipt(
        execution_id=ambiguous.execution_id,
        organization_id=ambiguous.organization_id,
        connection_id=ambiguous.connection_id,
        final_state=ExecutionState.AMBIGUOUS,
        normalized_error=ambiguous_error(),
        recorded_at=ambiguous_at,
        dispatch_started_at=dispatched.updated_at,
    )
    store.save_receipt(organization_id=ambiguous.organization_id, receipt=first)

    resolved_at = now + timedelta(seconds=5)
    succeeded = transition(ambiguous, ExecutionState.SUCCEEDED, resolved_at)
    store.save_execution(organization_id=succeeded.organization_id, execution=succeeded)
    evidence = store.save_confirmation_evidence(
        organization_id=succeeded.organization_id,
        execution_id=succeeded.execution_id,
        observed_at=resolved_at,
        confirmation_digest="b" * 64,
    )
    second = ExecutionReceipt(
        execution_id=succeeded.execution_id,
        organization_id=succeeded.organization_id,
        connection_id=succeeded.connection_id,
        final_state=ExecutionState.SUCCEEDED,
        recorded_at=resolved_at,
        dispatch_started_at=dispatched.updated_at,
        resolved_at=resolved_at,
        confirmation_evidence_ref=evidence.evidence_ref,
        reconciliation_evidence="provider lookup confirmed the effect",
        resolves_ambiguous_recorded_at=ambiguous_at,
    )
    store.save_receipt(organization_id=succeeded.organization_id, receipt=second)

    assert store.get_receipts_for_execution(
        organization_id=succeeded.organization_id,
        execution_id=succeeded.execution_id,
    ) == (first, second)
    assert [
        item.state
        for item in store.get_execution_history(
            organization_id=succeeded.organization_id,
            execution_id=succeeded.execution_id,
        )
    ][-2:] == [ExecutionState.AMBIGUOUS, ExecutionState.SUCCEEDED]


def test_atomic_outcome_rolls_back_state_evidence_and_history_on_conflict(
    store: SQLiteConnectionStore, created_execution: Execution, now: datetime
) -> None:
    dispatched = persist_path_to_dispatch(store, created_execution, now)
    ambiguous_at = now + timedelta(seconds=4)
    ambiguous = transition(dispatched, ExecutionState.AMBIGUOUS, ambiguous_at)
    first = ExecutionReceipt(
        execution_id=ambiguous.execution_id,
        organization_id=ambiguous.organization_id,
        connection_id=ambiguous.connection_id,
        final_state=ExecutionState.AMBIGUOUS,
        normalized_error=ambiguous_error(),
        recorded_at=ambiguous_at,
        dispatch_started_at=dispatched.updated_at,
    )
    store.commit_outcome(
        organization_id=ambiguous.organization_id,
        execution=ambiguous,
        receipt=first,
    )
    history_before = store.get_execution_history(
        organization_id=ambiguous.organization_id,
        execution_id=ambiguous.execution_id,
    )
    resolved_at = now + timedelta(seconds=5)
    succeeded = transition(ambiguous, ExecutionState.SUCCEEDED, resolved_at)
    evidence = store.new_confirmation_evidence(
        organization_id=succeeded.organization_id,
        execution_id=succeeded.execution_id,
        observed_at=resolved_at,
        confirmation_digest="c" * 64,
    )
    # Reusing the prior receipt timestamp makes the final INSERT collide,
    # after the transaction has already staged the state and evidence writes.
    conflicting = ExecutionReceipt(
        execution_id=succeeded.execution_id,
        organization_id=succeeded.organization_id,
        connection_id=succeeded.connection_id,
        final_state=ExecutionState.SUCCEEDED,
        recorded_at=ambiguous_at,
        dispatch_started_at=dispatched.updated_at,
        resolved_at=resolved_at,
        confirmation_evidence_ref=evidence.evidence_ref,
        reconciliation_evidence="c" * 64,
        resolves_ambiguous_recorded_at=ambiguous_at,
    )

    with pytest.raises(ConnectionStoreError, match="conflicts with history"):
        store.commit_outcome(
            organization_id=succeeded.organization_id,
            execution=succeeded,
            receipt=conflicting,
            evidence=evidence,
        )

    current = store.get_execution(
        organization_id=ambiguous.organization_id,
        execution_id=ambiguous.execution_id,
    )
    assert current is not None and current.state is ExecutionState.AMBIGUOUS
    assert (
        store.get_execution_history(
            organization_id=ambiguous.organization_id,
            execution_id=ambiguous.execution_id,
        )
        == history_before
    )
    assert (
        store.get_confirmation_evidence(
            organization_id=ambiguous.organization_id,
            evidence_ref=evidence.evidence_ref,
        )
        is None
    )


def test_confirmation_store_persists_digest_not_raw_canary(
    store: SQLiteConnectionStore,
    created_execution: Execution,
    now: datetime,
    tmp_path: Path,
) -> None:
    store.save_execution(
        organization_id=created_execution.organization_id,
        execution=created_execution,
    )
    canary = b"SQLITE-EVIDENCE-CANARY-51b7"
    evidence = store.save_confirmation_evidence(
        organization_id=created_execution.organization_id,
        execution_id=created_execution.execution_id,
        observed_at=now,
        confirmation_digest=hashlib.sha256(canary).hexdigest(),
    )

    assert evidence.confirmation_digest == hashlib.sha256(canary).hexdigest()
    assert canary not in (tmp_path / "connections.sqlite3").read_bytes()


def test_nonce_is_organization_scoped_and_append_only(
    store: SQLiteConnectionStore, now: datetime
) -> None:
    first = OrganizationId(value="org-1")
    second = OrganizationId(value="org-2")
    store.record_authorization_nonce(
        organization_id=first, nonce="nonce-1", recorded_at=now
    )

    assert store.has_authorization_nonce(organization_id=first, nonce="nonce-1")
    assert not store.has_authorization_nonce(organization_id=second, nonce="nonce-1")
    store.record_authorization_nonce(
        organization_id=second, nonce="nonce-1", recorded_at=now
    )
    with pytest.raises(ConnectionStoreError, match="already used"):
        store.record_authorization_nonce(
            organization_id=first, nonce="nonce-1", recorded_at=now
        )


def test_existing_loose_database_mode_is_tightened(tmp_path: Path) -> None:
    path = tmp_path / "connections.sqlite3"
    path.touch(mode=0o644)
    os.chmod(path, 0o644)

    store = SQLiteConnectionStore(path)
    try:
        assert path.stat().st_mode & 0o777 == 0o600
    finally:
        store.close()


def test_records_survive_store_restart(
    tmp_path: Path, connection: Connection, created_execution: Execution
) -> None:
    path = tmp_path / "connections.sqlite3"
    first = SQLiteConnectionStore(path)
    first.save_connection(
        organization_id=connection.organization_id, connection=connection
    )
    first.save_execution(
        organization_id=created_execution.organization_id,
        execution=created_execution,
    )
    first.close()

    second = SQLiteConnectionStore(path)
    try:
        assert (
            second.get_connection(
                organization_id=connection.organization_id,
                connection_id=connection.connection_id,
            )
            == connection
        )
        assert (
            second.get_execution(
                organization_id=created_execution.organization_id,
                execution_id=created_execution.execution_id,
            )
            == created_execution
        )
    finally:
        second.close()


def test_schema_version_is_recorded_and_future_schema_refuses(tmp_path: Path) -> None:
    path = tmp_path / "connections.sqlite3"
    store = SQLiteConnectionStore(path)
    store.close()
    with sqlite3.connect(path) as database:
        assert database.execute("PRAGMA user_version").fetchone()[0] == 1
        database.execute("PRAGMA user_version = 2")

    with pytest.raises(ConnectionStoreError, match="newer"):
        SQLiteConnectionStore(path)
