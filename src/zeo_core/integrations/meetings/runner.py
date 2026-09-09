"""Execute only a freshly admitted exact meeting invocation and file its receipt."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from pydantic import JsonValue

from .contracts import InvocationAuthorization, InvocationReceipt
from .runtime import MeetingRuntimePort, RuntimeRefusalError


class AdapterRefusalError(RuntimeError):
    """Proven refusal before a provider mutation."""


class AdapterAmbiguousError(RuntimeError):
    """A mutation may have happened; automatic redispatch is forbidden."""


class PreparedOperation(Protocol):
    def __call__(self) -> tuple[str, JsonValue]: ...


class AdapterPort(Protocol):
    def prepare(
        self, authorization: InvocationAuthorization, payload: dict[str, JsonValue]
    ) -> PreparedOperation: ...


def request_digest(payload: dict[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()


class MeetingRunner:
    """Runtime owns leases and replay; this runner owns no second execution ledger."""

    def __init__(
        self,
        *,
        runtime: MeetingRuntimePort,
        adapters: AdapterPort,
        clock: Callable[[], datetime] | None = None,
        observe: Callable[[InvocationReceipt, JsonValue], None] | None = None,
    ) -> None:
        self._observe = observe
        self._runtime = runtime
        self._adapters = adapters
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(
        self, authorization: InvocationAuthorization, payload: dict[str, JsonValue]
    ) -> InvocationReceipt:
        # Freeze arguments before validation and runtime admission.
        frozen = json.loads(json.dumps(payload, allow_nan=False))
        if request_digest(frozen) != authorization.request_sha256:
            raise AdapterRefusalError("meeting request digest mismatch")
        prepared = self._adapters.prepare(authorization, frozen)
        admitted = self._runtime.authorize(authorization)
        if admitted.authorization != authorization:
            raise RuntimeRefusalError("runtime authorization binding mismatch")
        if admitted.disposition == "RECONCILE":
            raise AdapterAmbiguousError("runtime requires reconciliation; no dispatch")
        if admitted.disposition == "REPLAY_FINAL":
            receipt = admitted.receipt
            if receipt is None or not _matches(receipt, authorization):
                raise RuntimeRefusalError("runtime replay receipt mismatch")
            reconciliation = admitted.reconciliation
            if reconciliation is not None:
                if reconciliation.invocation_id != authorization.invocation_id:
                    raise RuntimeRefusalError("runtime reconciliation binding mismatch")
                # A projection of the runtime's two admitted records, not a new receipt.
                return InvocationReceipt.model_validate(
                    {
                        **receipt.model_dump(),
                        "outcome": reconciliation.outcome,
                        "provider_object_id": reconciliation.provider_object_id,
                        "observed_at": reconciliation.observed_at,
                        "reconciled": True,
                    }
                )
            return receipt
        if admitted.receipt is not None or admitted.reconciliation is not None:
            raise RuntimeRefusalError("fresh execution carried a prior result")
        return self._dispatch_and_admit(authorization, prepared)

    def _dispatch_and_admit(
        self, authorization: InvocationAuthorization, prepared: PreparedOperation
    ) -> InvocationReceipt:
        object_id = ""
        response_hash = ""
        response: JsonValue = None
        try:
            object_id, response = prepared()
            response_hash = hashlib.sha256(
                json.dumps(
                    response, sort_keys=True, separators=(",", ":"), allow_nan=False
                ).encode()
            ).hexdigest()
            if authorization.operation.endswith(".create") and not object_id:
                raise AdapterAmbiguousError("provider object identity is missing")
            outcome = "SUCCEEDED"
        except AdapterRefusalError:
            outcome = "REFUSED"
        except Exception:
            outcome = (
                "AMBIGUOUS"
                if authorization.operation
                in {"gmail.draft.create", "notion.page.upsert", "gmail.draft.reconcile"}
                else "REFUSED"
            )
            object_id = ""
            response_hash = ""
        receipt = InvocationReceipt(
            receipt_id="receipt_" + uuid.uuid4().hex,
            invocation_id=authorization.invocation_id,
            operation=authorization.operation,
            resource=authorization.resource,
            request_sha256=authorization.request_sha256,
            outcome=outcome,
            provider_object_id=object_id,
            response_sha256=response_hash,
            observed_at=self._clock(),
        )
        accepted = self._runtime.admit_receipt(receipt)
        if accepted != receipt:
            raise RuntimeRefusalError(
                "runtime did not admit the exact provider receipt"
            )
        if accepted.outcome == "SUCCEEDED" and self._observe is not None:
            self._observe(accepted, response)
        return accepted


def _matches(
    receipt: InvocationReceipt, authorization: InvocationAuthorization
) -> bool:
    return (
        receipt.invocation_id == authorization.invocation_id
        and receipt.operation == authorization.operation
        and receipt.resource == authorization.resource
        and receipt.request_sha256 == authorization.request_sha256
    )
