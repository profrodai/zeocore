"""SQLite persistence for organization-scoped connection execution records."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from zeo_core.contracts.connections import (
    ConfirmationEvidence,
    ConfirmationEvidenceRef,
    Connection,
    ConnectionId,
    ConnectorRevision,
    ConnectorRevisionId,
    Execution,
    ExecutionId,
    ExecutionReceipt,
    ExecutionState,
    IdempotencyKey,
    ObservationId,
    ObservationReceipt,
    ObservationRecord,
    ObservationState,
    OrganizationId,
    is_allowed_transition,
)

_SCHEMA_VERSION = 2


class ConnectionStoreError(RuntimeError):
    """Sanitized persistence failure with no record or provider payload."""


def _json_bytes(model: BaseModel) -> str:
    data = model.model_dump(mode="json")
    if isinstance(model, Connection):
        data["secret_handle"] = {"handle": model.secret_handle.handle}
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _same_execution_identity(left: Execution, right: Execution) -> bool:
    excluded = {"state", "updated_at", "completed_at"}
    return left.model_dump(exclude=excluded) == right.model_dump(exclude=excluded)


def _same_observation_identity(
    left: ObservationRecord, right: ObservationRecord
) -> bool:
    excluded = {"state", "completed_at"}
    return left.model_dump(exclude=excluded) == right.model_dump(exclude=excluded)


class SQLiteConnectionStore:
    """Thread-safe SQLite implementation of the ConnectionStore protocol."""

    def __init__(
        self,
        path: str | Path,
        *,
        uuid_factory: Callable[[], uuid.UUID] = uuid.uuid4,
    ) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._uuid_factory = uuid_factory
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self._path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        try:
            os.chmod(self._path, 0o600)
            self._initialize()
        except Exception:
            self._connection.close()
            raise

    def close(self) -> None:
        """Close the owned database connection."""

        with self._lock:
            self._connection.close()

    def __enter__(self) -> SQLiteConnectionStore:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                yield self._connection
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise

    def _initialize(self) -> None:
        with self._transaction() as connection:
            current_version = int(
                connection.execute("PRAGMA user_version").fetchone()[0]
            )
            if current_version > _SCHEMA_VERSION:
                raise ConnectionStoreError(
                    "database schema is newer than this ZeoCore build"
                )
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS connections (
                    organization_id TEXT NOT NULL,
                    connection_id TEXT NOT NULL,
                    document TEXT NOT NULL,
                    PRIMARY KEY (organization_id, connection_id)
                );
                CREATE TABLE IF NOT EXISTS connector_revisions (
                    organization_id TEXT NOT NULL,
                    revision_id TEXT NOT NULL,
                    document TEXT NOT NULL,
                    PRIMARY KEY (organization_id, revision_id)
                );
                CREATE TABLE IF NOT EXISTS executions (
                    organization_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    connection_id TEXT NOT NULL,
                    connector_revision TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    state TEXT NOT NULL,
                    document TEXT NOT NULL,
                    PRIMARY KEY (organization_id, execution_id),
                    UNIQUE (
                        organization_id, connection_id, connector_revision,
                        operation_id, idempotency_key
                    )
                );
                CREATE TABLE IF NOT EXISTS execution_history (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    organization_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    document TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS receipts (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    organization_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    final_state TEXT NOT NULL,
                    document TEXT NOT NULL,
                    UNIQUE (organization_id, execution_id, recorded_at)
                );
                CREATE TABLE IF NOT EXISTS evidence_references (
                    organization_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    evidence_ref TEXT NOT NULL,
                    PRIMARY KEY (organization_id, evidence_ref)
                );
                CREATE TABLE IF NOT EXISTS confirmation_evidence (
                    organization_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    evidence_ref TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    confirmation_digest TEXT NOT NULL,
                    PRIMARY KEY (organization_id, evidence_ref)
                );
                CREATE TABLE IF NOT EXISTS authorization_nonces (
                    organization_id TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    PRIMARY KEY (organization_id, nonce)
                );
                CREATE TABLE IF NOT EXISTS observations (
                    organization_id TEXT NOT NULL,
                    observation_id TEXT NOT NULL,
                    connection_id TEXT NOT NULL,
                    connector_revision TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_digest TEXT NOT NULL,
                    state TEXT NOT NULL,
                    document TEXT NOT NULL,
                    PRIMARY KEY (organization_id, observation_id),
                    UNIQUE (
                        organization_id, connection_id, connector_revision,
                        operation_id, idempotency_key
                    )
                );
                CREATE TABLE IF NOT EXISTS observation_receipts (
                    organization_id TEXT NOT NULL,
                    observation_id TEXT NOT NULL,
                    document TEXT NOT NULL,
                    PRIMARY KEY (organization_id, observation_id)
                );
                """
            )
            connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")

    @staticmethod
    def _require_scope(
        expected: OrganizationId, actual: OrganizationId, record_kind: str
    ) -> None:
        if expected != actual:
            raise ConnectionStoreError(f"{record_kind} organization mismatch")

    def save_connection(
        self, *, organization_id: OrganizationId, connection: Connection
    ) -> None:
        self._require_scope(organization_id, connection.organization_id, "connection")
        with self._transaction() as database:
            database.execute(
                """
                INSERT INTO connections (organization_id, connection_id, document)
                VALUES (?, ?, ?)
                ON CONFLICT (organization_id, connection_id)
                DO UPDATE SET document = excluded.document
                """,
                (
                    str(organization_id),
                    str(connection.connection_id),
                    _json_bytes(connection),
                ),
            )

    def get_connection(
        self, *, organization_id: OrganizationId, connection_id: ConnectionId
    ) -> Connection | None:
        with self._lock:
            row = self._connection.execute(
                """SELECT document FROM connections
                WHERE organization_id = ? AND connection_id = ?""",
                (str(organization_id), str(connection_id)),
            ).fetchone()
        return None if row is None else Connection.model_validate_json(row["document"])

    def save_connector_revision(
        self, *, organization_id: OrganizationId, revision: ConnectorRevision
    ) -> None:
        document = _json_bytes(revision)
        with self._transaction() as database:
            row = database.execute(
                """SELECT document FROM connector_revisions
                WHERE organization_id = ? AND revision_id = ?""",
                (str(organization_id), str(revision.revision_id)),
            ).fetchone()
            if row is not None and row["document"] != document:
                raise ConnectionStoreError("connector revision is immutable")
            database.execute(
                """INSERT OR IGNORE INTO connector_revisions
                (organization_id, revision_id, document) VALUES (?, ?, ?)""",
                (str(organization_id), str(revision.revision_id), document),
            )

    def get_connector_revision(
        self,
        *,
        organization_id: OrganizationId,
        revision_id: ConnectorRevisionId,
    ) -> ConnectorRevision | None:
        with self._lock:
            row = self._connection.execute(
                """SELECT document FROM connector_revisions
                WHERE organization_id = ? AND revision_id = ?""",
                (str(organization_id), str(revision_id)),
            ).fetchone()
        if row is None:
            return None
        return ConnectorRevision.model_validate_json(row["document"])

    def save_execution(
        self, *, organization_id: OrganizationId, execution: Execution
    ) -> None:
        self._require_scope(organization_id, execution.organization_id, "execution")
        document = _json_bytes(execution)
        with self._transaction() as database:
            row = database.execute(
                """SELECT document FROM executions
                WHERE organization_id = ? AND execution_id = ?""",
                (str(organization_id), str(execution.execution_id)),
            ).fetchone()
            if row is None:
                if execution.state is not ExecutionState.CREATED:
                    raise ConnectionStoreError("first persisted state must be CREATED")
                try:
                    database.execute(
                        """INSERT INTO executions (
                            organization_id, execution_id, connection_id,
                            connector_revision, operation_id, idempotency_key,
                            state, document
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            str(organization_id),
                            str(execution.execution_id),
                            str(execution.connection_id),
                            str(execution.connector_revision),
                            str(execution.operation_id),
                            str(execution.idempotency_key),
                            execution.state.value,
                            document,
                        ),
                    )
                except sqlite3.IntegrityError as error:
                    raise ConnectionStoreError(
                        "execution id or idempotency identity already exists"
                    ) from error
            else:
                previous = Execution.model_validate_json(row["document"])
                if not _same_execution_identity(previous, execution):
                    raise ConnectionStoreError("execution identity is immutable")
                if not is_allowed_transition(previous.state, execution.state):
                    raise ConnectionStoreError(
                        "execution state transition is not allowed"
                    )
                if execution.updated_at < previous.updated_at:
                    raise ConnectionStoreError("execution updated_at must be monotonic")
                database.execute(
                    """UPDATE executions SET state = ?, document = ?
                    WHERE organization_id = ? AND execution_id = ?""",
                    (
                        execution.state.value,
                        document,
                        str(organization_id),
                        str(execution.execution_id),
                    ),
                )
            database.execute(
                """INSERT INTO execution_history
                (organization_id, execution_id, state, recorded_at, document)
                VALUES (?, ?, ?, ?, ?)""",
                (
                    str(organization_id),
                    str(execution.execution_id),
                    execution.state.value,
                    execution.updated_at.isoformat(),
                    document,
                ),
            )

    def get_execution(
        self, *, organization_id: OrganizationId, execution_id: ExecutionId
    ) -> Execution | None:
        with self._lock:
            row = self._connection.execute(
                """SELECT document FROM executions
                WHERE organization_id = ? AND execution_id = ?""",
                (str(organization_id), str(execution_id)),
            ).fetchone()
        return None if row is None else Execution.model_validate_json(row["document"])

    def get_execution_by_idempotency(
        self,
        *,
        organization_id: OrganizationId,
        connection_id: ConnectionId,
        connector_revision: ConnectorRevisionId,
        operation_id: str,
        idempotency_key: str,
    ) -> Execution | None:
        """Resolve one scoped idempotency identity without crossing tenants."""

        with self._lock:
            row = self._connection.execute(
                """SELECT document FROM executions
                WHERE organization_id = ? AND connection_id = ?
                AND connector_revision = ? AND operation_id = ?
                AND idempotency_key = ?""",
                (
                    str(organization_id),
                    str(connection_id),
                    str(connector_revision),
                    operation_id,
                    idempotency_key,
                ),
            ).fetchone()
        return None if row is None else Execution.model_validate_json(row["document"])

    def claim_execution(
        self,
        *,
        organization_id: OrganizationId,
        nonce: str,
        nonce_recorded_at: datetime,
        execution: Execution,
    ) -> tuple[Execution, bool]:
        """Atomically consume authorization replay identity and create execution.

        Returns ``(execution, True)`` to the winner. Concurrent callers with the
        same scoped idempotency identity receive ``(winner, False)`` and must
        never dispatch independently.
        """

        self._require_scope(organization_id, execution.organization_id, "execution")
        if execution.state is not ExecutionState.CREATED:
            raise ConnectionStoreError("claimed execution must start at CREATED")
        try:
            with self._transaction() as database:
                database.execute(
                    """INSERT INTO authorization_nonces
                    (organization_id, nonce, recorded_at) VALUES (?, ?, ?)""",
                    (str(organization_id), nonce, nonce_recorded_at.isoformat()),
                )
                database.execute(
                    """INSERT INTO executions (
                        organization_id, execution_id, connection_id,
                        connector_revision, operation_id, idempotency_key,
                        state, document
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(organization_id),
                        str(execution.execution_id),
                        str(execution.connection_id),
                        str(execution.connector_revision),
                        str(execution.operation_id),
                        str(execution.idempotency_key),
                        execution.state.value,
                        _json_bytes(execution),
                    ),
                )
                database.execute(
                    """INSERT INTO execution_history
                    (organization_id, execution_id, state, recorded_at, document)
                    VALUES (?, ?, ?, ?, ?)""",
                    (
                        str(organization_id),
                        str(execution.execution_id),
                        execution.state.value,
                        execution.updated_at.isoformat(),
                        _json_bytes(execution),
                    ),
                )
        except sqlite3.IntegrityError as error:
            existing = self.get_execution_by_idempotency(
                organization_id=organization_id,
                connection_id=execution.connection_id,
                connector_revision=execution.connector_revision,
                operation_id=str(execution.operation_id),
                idempotency_key=str(execution.idempotency_key),
            )
            if existing is not None:
                return existing, False
            raise ConnectionStoreError(
                "authorization nonce or execution identity was already used"
            ) from error
        return execution, True

    def get_execution_history(
        self, *, organization_id: OrganizationId, execution_id: ExecutionId
    ) -> tuple[Execution, ...]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT document FROM execution_history
                WHERE organization_id = ? AND execution_id = ? ORDER BY sequence""",
                (str(organization_id), str(execution_id)),
            ).fetchall()
        return tuple(Execution.model_validate_json(row["document"]) for row in rows)

    def save_receipt(
        self, *, organization_id: OrganizationId, receipt: ExecutionReceipt
    ) -> None:
        self._require_scope(organization_id, receipt.organization_id, "receipt")
        with self._transaction() as database:
            execution_row = database.execute(
                """SELECT document FROM executions
                WHERE organization_id = ? AND execution_id = ?""",
                (str(organization_id), str(receipt.execution_id)),
            ).fetchone()
            if execution_row is None:
                raise ConnectionStoreError("receipt execution does not exist")
            execution = Execution.model_validate_json(execution_row["document"])
            if execution.connection_id != receipt.connection_id:
                raise ConnectionStoreError("receipt connection mismatch")
            if execution.state is not receipt.final_state:
                raise ConnectionStoreError("receipt state does not match execution")
            if receipt.confirmation_evidence_ref is not None:
                evidence = database.execute(
                    """SELECT 1 FROM evidence_references
                    WHERE organization_id = ? AND execution_id = ?
                    AND evidence_ref = ?""",
                    (
                        str(organization_id),
                        str(receipt.execution_id),
                        str(receipt.confirmation_evidence_ref),
                    ),
                ).fetchone()
                if evidence is None:
                    raise ConnectionStoreError(
                        "confirmation evidence provenance is not persisted"
                    )
            if receipt.resolves_ambiguous_recorded_at is not None:
                prior = database.execute(
                    """SELECT 1 FROM receipts
                    WHERE organization_id = ? AND execution_id = ?
                    AND recorded_at = ? AND final_state = ?""",
                    (
                        str(organization_id),
                        str(receipt.execution_id),
                        receipt.resolves_ambiguous_recorded_at.isoformat(),
                        ExecutionState.AMBIGUOUS.value,
                    ),
                ).fetchone()
                if prior is None:
                    raise ConnectionStoreError(
                        "resolving receipt does not reference persisted ambiguity"
                    )
            try:
                database.execute(
                    """INSERT INTO receipts
                    (organization_id, execution_id, recorded_at, final_state, document)
                    VALUES (?, ?, ?, ?, ?)""",
                    (
                        str(organization_id),
                        str(receipt.execution_id),
                        receipt.recorded_at.isoformat(),
                        receipt.final_state.value,
                        _json_bytes(receipt),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise ConnectionStoreError(
                    "receipt timestamp already exists"
                ) from error

    def get_receipts_for_execution(
        self, *, organization_id: OrganizationId, execution_id: ExecutionId
    ) -> tuple[ExecutionReceipt, ...]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT document FROM receipts
                WHERE organization_id = ? AND execution_id = ? ORDER BY sequence""",
                (str(organization_id), str(execution_id)),
            ).fetchall()
        return tuple(
            ExecutionReceipt.model_validate_json(row["document"]) for row in rows
        )

    def save_evidence_reference(
        self,
        *,
        organization_id: OrganizationId,
        execution_id: ExecutionId,
        evidence_ref: ConfirmationEvidenceRef,
    ) -> None:
        with self._transaction() as database:
            self._require_execution(database, organization_id, execution_id)
            try:
                database.execute(
                    """INSERT INTO evidence_references
                    (organization_id, execution_id, evidence_ref) VALUES (?, ?, ?)""",
                    (str(organization_id), str(execution_id), str(evidence_ref)),
                )
            except sqlite3.IntegrityError as error:
                raise ConnectionStoreError(
                    "evidence reference already exists"
                ) from error

    def get_evidence_references_for_execution(
        self, *, organization_id: OrganizationId, execution_id: ExecutionId
    ) -> tuple[ConfirmationEvidenceRef, ...]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT evidence_ref FROM evidence_references
                WHERE organization_id = ? AND execution_id = ? ORDER BY rowid""",
                (str(organization_id), str(execution_id)),
            ).fetchall()
        return tuple(ConfirmationEvidenceRef(value=row["evidence_ref"]) for row in rows)

    def save_confirmation_evidence(
        self,
        *,
        organization_id: OrganizationId,
        execution_id: ExecutionId,
        observed_at: datetime,
        confirmation_digest: str,
    ) -> ConfirmationEvidence:
        evidence = self.new_confirmation_evidence(
            organization_id=organization_id,
            execution_id=execution_id,
            observed_at=observed_at,
            confirmation_digest=confirmation_digest,
        )
        with self._transaction() as database:
            self._require_execution(database, organization_id, execution_id)
            database.execute(
                """INSERT INTO evidence_references
                (organization_id, execution_id, evidence_ref) VALUES (?, ?, ?)""",
                (
                    str(organization_id),
                    str(execution_id),
                    str(evidence.evidence_ref),
                ),
            )
            database.execute(
                """INSERT INTO confirmation_evidence
                (organization_id, execution_id, evidence_ref, observed_at,
                 confirmation_digest) VALUES (?, ?, ?, ?, ?)""",
                (
                    str(organization_id),
                    str(execution_id),
                    str(evidence.evidence_ref),
                    observed_at.isoformat(),
                    confirmation_digest,
                ),
            )
        return evidence

    def new_confirmation_evidence(
        self,
        *,
        organization_id: OrganizationId,
        execution_id: ExecutionId,
        observed_at: datetime,
        confirmation_digest: str,
    ) -> ConfirmationEvidence:
        """Mint and validate an unpersisted evidence record for atomic commit."""

        return ConfirmationEvidence(
            evidence_ref=ConfirmationEvidenceRef(
                value=f"zeo-evidence:v1:{self._uuid_factory()}"
            ),
            organization_id=organization_id,
            execution_id=execution_id,
            observed_at=observed_at,
            confirmation_digest=confirmation_digest,
        )

    def commit_outcome(
        self,
        *,
        organization_id: OrganizationId,
        execution: Execution,
        receipt: ExecutionReceipt,
        evidence: ConfirmationEvidence | None = None,
    ) -> None:
        """Atomically append a terminal/ambiguous transition and its evidence."""

        self._validate_outcome_context(
            organization_id=organization_id,
            execution=execution,
            receipt=receipt,
            evidence=evidence,
        )
        try:
            with self._transaction() as database:
                self._commit_outcome_rows(
                    database=database,
                    organization_id=organization_id,
                    execution=execution,
                    receipt=receipt,
                    evidence=evidence,
                )
        except sqlite3.IntegrityError as error:
            raise ConnectionStoreError(
                "outcome record conflicts with history"
            ) from error

    def _commit_outcome_rows(
        self,
        *,
        database: sqlite3.Connection,
        organization_id: OrganizationId,
        execution: Execution,
        receipt: ExecutionReceipt,
        evidence: ConfirmationEvidence | None,
    ) -> None:
        previous_row = database.execute(
            """SELECT document FROM executions
            WHERE organization_id = ? AND execution_id = ?""",
            (str(organization_id), str(execution.execution_id)),
        ).fetchone()
        if previous_row is None:
            raise ConnectionStoreError("execution does not exist in organization")
        previous = Execution.model_validate_json(previous_row["document"])
        if not _same_execution_identity(previous, execution):
            raise ConnectionStoreError("execution identity is immutable")
        if not is_allowed_transition(previous.state, execution.state):
            raise ConnectionStoreError("execution state transition is not allowed")
        if execution.updated_at < previous.updated_at:
            raise ConnectionStoreError("execution updated_at must be monotonic")
        if evidence is not None:
            self._insert_confirmation_evidence(database, evidence)
        self._validate_receipt_provenance(database, receipt)
        database.execute(
            """UPDATE executions SET state = ?, document = ?
            WHERE organization_id = ? AND execution_id = ?""",
            (
                execution.state.value,
                _json_bytes(execution),
                str(organization_id),
                str(execution.execution_id),
            ),
        )
        database.execute(
            """INSERT INTO execution_history
            (organization_id, execution_id, state, recorded_at, document)
            VALUES (?, ?, ?, ?, ?)""",
            (
                str(organization_id),
                str(execution.execution_id),
                execution.state.value,
                execution.updated_at.isoformat(),
                _json_bytes(execution),
            ),
        )
        database.execute(
            """INSERT INTO receipts
            (organization_id, execution_id, recorded_at, final_state, document)
            VALUES (?, ?, ?, ?, ?)""",
            (
                str(organization_id),
                str(execution.execution_id),
                receipt.recorded_at.isoformat(),
                receipt.final_state.value,
                _json_bytes(receipt),
            ),
        )

    def _validate_outcome_context(
        self,
        *,
        organization_id: OrganizationId,
        execution: Execution,
        receipt: ExecutionReceipt,
        evidence: ConfirmationEvidence | None,
    ) -> None:
        self._require_scope(organization_id, execution.organization_id, "execution")
        self._require_scope(organization_id, receipt.organization_id, "receipt")
        if receipt.execution_id != execution.execution_id:
            raise ConnectionStoreError("receipt execution mismatch")
        if receipt.connection_id != execution.connection_id:
            raise ConnectionStoreError("receipt connection mismatch")
        if receipt.final_state is not execution.state:
            raise ConnectionStoreError("receipt state does not match execution")
        if evidence is None:
            return
        self._require_scope(
            organization_id, evidence.organization_id, "confirmation evidence"
        )
        if evidence.execution_id != execution.execution_id:
            raise ConnectionStoreError("confirmation evidence execution mismatch")
        if receipt.confirmation_evidence_ref != evidence.evidence_ref:
            raise ConnectionStoreError("receipt evidence reference mismatch")

    @staticmethod
    def _insert_confirmation_evidence(
        database: sqlite3.Connection, evidence: ConfirmationEvidence
    ) -> None:
        database.execute(
            """INSERT INTO evidence_references
            (organization_id, execution_id, evidence_ref) VALUES (?, ?, ?)""",
            (
                str(evidence.organization_id),
                str(evidence.execution_id),
                str(evidence.evidence_ref),
            ),
        )
        database.execute(
            """INSERT INTO confirmation_evidence
            (organization_id, execution_id, evidence_ref, observed_at,
             confirmation_digest) VALUES (?, ?, ?, ?, ?)""",
            (
                str(evidence.organization_id),
                str(evidence.execution_id),
                str(evidence.evidence_ref),
                evidence.observed_at.isoformat(),
                evidence.confirmation_digest,
            ),
        )

    @staticmethod
    def _validate_receipt_provenance(
        database: sqlite3.Connection, receipt: ExecutionReceipt
    ) -> None:
        if receipt.confirmation_evidence_ref is not None:
            found = database.execute(
                """SELECT 1 FROM evidence_references
                WHERE organization_id = ? AND execution_id = ?
                AND evidence_ref = ?""",
                (
                    str(receipt.organization_id),
                    str(receipt.execution_id),
                    str(receipt.confirmation_evidence_ref),
                ),
            ).fetchone()
            if found is None:
                raise ConnectionStoreError(
                    "confirmation evidence provenance is not persisted"
                )
        if receipt.resolves_ambiguous_recorded_at is None:
            return
        prior = database.execute(
            """SELECT 1 FROM receipts
            WHERE organization_id = ? AND execution_id = ?
            AND recorded_at = ? AND final_state = ?""",
            (
                str(receipt.organization_id),
                str(receipt.execution_id),
                receipt.resolves_ambiguous_recorded_at.isoformat(),
                ExecutionState.AMBIGUOUS.value,
            ),
        ).fetchone()
        if prior is None:
            raise ConnectionStoreError(
                "resolving receipt does not reference persisted ambiguity"
            )

    def get_confirmation_evidence(
        self,
        *,
        organization_id: OrganizationId,
        evidence_ref: ConfirmationEvidenceRef,
    ) -> ConfirmationEvidence | None:
        with self._lock:
            row = self._connection.execute(
                """SELECT execution_id, observed_at, confirmation_digest
                FROM confirmation_evidence
                WHERE organization_id = ? AND evidence_ref = ?""",
                (str(organization_id), str(evidence_ref)),
            ).fetchone()
        if row is None:
            return None
        return ConfirmationEvidence(
            evidence_ref=evidence_ref,
            organization_id=organization_id,
            execution_id=ExecutionId(value=row["execution_id"]),
            observed_at=datetime.fromisoformat(row["observed_at"]),
            confirmation_digest=row["confirmation_digest"],
        )

    def has_authorization_nonce(
        self, *, organization_id: OrganizationId, nonce: str
    ) -> bool:
        with self._lock:
            row = self._connection.execute(
                """SELECT 1 FROM authorization_nonces
                WHERE organization_id = ? AND nonce = ?""",
                (str(organization_id), nonce),
            ).fetchone()
        return row is not None

    def record_authorization_nonce(
        self, *, organization_id: OrganizationId, nonce: str, recorded_at: datetime
    ) -> None:
        with self._transaction() as database:
            try:
                database.execute(
                    """INSERT INTO authorization_nonces
                    (organization_id, nonce, recorded_at) VALUES (?, ?, ?)""",
                    (str(organization_id), nonce, recorded_at.isoformat()),
                )
            except sqlite3.IntegrityError as error:
                raise ConnectionStoreError(
                    "authorization nonce was already used"
                ) from error

    def get_observation(
        self, *, organization_id: OrganizationId, observation_id: ObservationId
    ) -> ObservationRecord | None:
        with self._lock:
            row = self._connection.execute(
                """SELECT document FROM observations
                WHERE organization_id = ? AND observation_id = ?""",
                (str(organization_id), str(observation_id)),
            ).fetchone()
        return (
            None
            if row is None
            else ObservationRecord.model_validate_json(row["document"])
        )

    def get_observation_by_idempotency(
        self,
        *,
        organization_id: OrganizationId,
        connection_id: ConnectionId,
        connector_revision: ConnectorRevisionId,
        operation_id: str,
        idempotency_key: IdempotencyKey,
    ) -> ObservationRecord | None:
        with self._lock:
            row = self._connection.execute(
                """SELECT document FROM observations
                WHERE organization_id = ? AND connection_id = ?
                AND connector_revision = ? AND operation_id = ?
                AND idempotency_key = ?""",
                (
                    str(organization_id),
                    str(connection_id),
                    str(connector_revision),
                    operation_id,
                    str(idempotency_key),
                ),
            ).fetchone()
        return (
            None
            if row is None
            else ObservationRecord.model_validate_json(row["document"])
        )

    def claim_observation(
        self,
        *,
        organization_id: OrganizationId,
        nonce: str,
        nonce_recorded_at: datetime,
        observation: ObservationRecord,
    ) -> tuple[ObservationRecord, bool]:
        self._require_scope(organization_id, observation.organization_id, "observation")
        if observation.state is not ObservationState.CLAIMED:
            raise ConnectionStoreError("new observation must start CLAIMED")
        try:
            with self._transaction() as database:
                database.execute(
                    """INSERT INTO authorization_nonces
                    (organization_id, nonce, recorded_at) VALUES (?, ?, ?)""",
                    (str(organization_id), nonce, nonce_recorded_at.isoformat()),
                )
                database.execute(
                    """INSERT INTO observations (
                        organization_id, observation_id, connection_id,
                        connector_revision, operation_id, idempotency_key,
                        request_digest, state, document
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(organization_id),
                        str(observation.observation_id),
                        str(observation.connection_id),
                        str(observation.connector_revision),
                        str(observation.operation_id),
                        str(observation.idempotency_key),
                        observation.request_digest,
                        observation.state.value,
                        _json_bytes(observation),
                    ),
                )
        except sqlite3.IntegrityError as error:
            existing = self.get_observation_by_idempotency(
                organization_id=organization_id,
                connection_id=observation.connection_id,
                connector_revision=observation.connector_revision,
                operation_id=str(observation.operation_id),
                idempotency_key=observation.idempotency_key,
            )
            if existing is not None:
                return existing, False
            raise ConnectionStoreError(
                "authorization nonce or observation identity was already used"
            ) from error
        return observation, True

    def commit_observation(
        self,
        *,
        organization_id: OrganizationId,
        observation: ObservationRecord,
        receipt: ObservationReceipt,
    ) -> None:
        self._require_scope(organization_id, observation.organization_id, "observation")
        self._require_scope(
            organization_id, receipt.organization_id, "observation receipt"
        )
        if observation.state is ObservationState.CLAIMED:
            raise ConnectionStoreError("committed observation must be terminal")
        if receipt.observation_id != observation.observation_id:
            raise ConnectionStoreError("observation receipt identity mismatch")
        if receipt.connection_id != observation.connection_id:
            raise ConnectionStoreError("observation receipt connection mismatch")
        if receipt.request_digest != observation.request_digest:
            raise ConnectionStoreError("observation receipt request mismatch")
        if receipt.final_state is not observation.state:
            raise ConnectionStoreError("observation receipt state mismatch")
        try:
            with self._transaction() as database:
                row = database.execute(
                    """SELECT document FROM observations
                    WHERE organization_id = ? AND observation_id = ?""",
                    (str(organization_id), str(observation.observation_id)),
                ).fetchone()
                if row is None:
                    raise ConnectionStoreError("observation claim does not exist")
                previous = ObservationRecord.model_validate_json(row["document"])
                if previous.state is not ObservationState.CLAIMED:
                    raise ConnectionStoreError("observation is already terminal")
                if not _same_observation_identity(previous, observation):
                    raise ConnectionStoreError("observation identity is immutable")
                database.execute(
                    """UPDATE observations SET state = ?, document = ?
                    WHERE organization_id = ? AND observation_id = ?""",
                    (
                        observation.state.value,
                        _json_bytes(observation),
                        str(organization_id),
                        str(observation.observation_id),
                    ),
                )
                database.execute(
                    """INSERT INTO observation_receipts
                    (organization_id, observation_id, document) VALUES (?, ?, ?)""",
                    (
                        str(organization_id),
                        str(observation.observation_id),
                        _json_bytes(receipt),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ConnectionStoreError("observation outcome already exists") from error

    def get_observation_receipt(
        self, *, organization_id: OrganizationId, observation_id: ObservationId
    ) -> ObservationReceipt | None:
        with self._lock:
            row = self._connection.execute(
                """SELECT document FROM observation_receipts
                WHERE organization_id = ? AND observation_id = ?""",
                (str(organization_id), str(observation_id)),
            ).fetchone()
        return (
            None
            if row is None
            else ObservationReceipt.model_validate_json(row["document"])
        )

    @staticmethod
    def _require_execution(
        database: sqlite3.Connection,
        organization_id: OrganizationId,
        execution_id: ExecutionId,
    ) -> None:
        row = database.execute(
            """SELECT 1 FROM executions
            WHERE organization_id = ? AND execution_id = ?""",
            (str(organization_id), str(execution_id)),
        ).fetchone()
        if row is None:
            raise ConnectionStoreError("execution does not exist in organization")
