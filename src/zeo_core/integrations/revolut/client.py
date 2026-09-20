"""Revolut Business reads only: accounts and one bounded transaction page."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import SecretStr, TypeAdapter, ValidationError

from .models import (
    MAX_RESULT_BYTES,
    Account,
    RevolutEnvironment,
    Transaction,
    TransactionPage,
    TransactionQuery,
)
from .transport import RevolutAPIError, RevolutTransport

_ACCOUNTS = TypeAdapter(tuple[Account, ...])
_TRANSACTIONS = TypeAdapter(tuple[Transaction, ...])
_TOO_LARGE = "Normalized Revolut result exceeded the size limit; nothing was returned"


def _instant(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class RevolutBusinessClient:
    """Explicit read operations; credentials never appear in result objects."""

    def __init__(
        self,
        access_token: SecretStr | None = None,
        *,
        environment: RevolutEnvironment = RevolutEnvironment.PRODUCTION,
        transport: RevolutTransport | None = None,
    ) -> None:
        if transport is None:
            if access_token is None:
                raise ValueError("Revolut access token is required")
            transport = RevolutTransport(access_token, environment=environment)
        self._transport = transport

    def close(self) -> None:
        self._transport.close()

    def list_accounts(self) -> tuple[Account, ...]:
        try:
            accounts = _ACCOUNTS.validate_python(self._transport.get("/accounts"))
        except ValidationError:
            raise _unrecognized() from None
        if len(_ACCOUNTS.dump_json(accounts)) > MAX_RESULT_BYTES:
            raise RevolutAPIError("RESPONSE_TOO_LARGE", _TOO_LARGE)
        return accounts

    def list_transactions(
        self, query: TransactionQuery | None = None
    ) -> TransactionPage:
        """Return one observed page and the cursor for the next older page.

        There is no collect-everything form: the caller owns the loop, its
        checkpoint and replacement by transaction ``id``. Any error, including
        ``PAGINATION_STALLED`` and ``RESPONSE_TOO_LARGE``, means the window
        was not fully read: record an incomplete sync, never completion.
        """
        query = query or TransactionQuery()
        params: dict[str, str | int] = {"count": query.count}
        if query.from_ is not None:
            params["from"] = _instant(query.from_)
        if query.to is not None:
            params["to"] = _instant(query.to)
        if query.account_id is not None:
            params["account"] = str(query.account_id)
        if query.type is not None:
            params["type"] = query.type
        try:
            transactions = _TRANSACTIONS.validate_python(
                self._transport.get("/transactions", params=params)
            )
        except ValidationError:
            raise _unrecognized() from None
        observed_at = datetime.now(UTC)
        next_to = None
        if len(transactions) >= query.count:
            next_to = min(item.created_at for item in transactions)
            if query.to is not None and next_to >= query.to:
                raise RevolutAPIError(
                    "PAGINATION_STALLED",
                    "Revolut returned a full page that does not advance the cursor",
                )
        page = TransactionPage(
            transactions=transactions, observed_at=observed_at, next_to=next_to
        )
        # Never truncate: a partial page would silently lose matching evidence.
        if len(page.model_dump_json().encode()) > MAX_RESULT_BYTES:
            raise RevolutAPIError(
                "RESPONSE_TOO_LARGE", _TOO_LARGE + "; lower count or narrow the window"
            )
        return page


def _unrecognized() -> RevolutAPIError:
    # Validation detail can quote provider values; it is deliberately discarded.
    return RevolutAPIError(
        "RESPONSE", "Revolut response did not match the reviewed read contract"
    )
