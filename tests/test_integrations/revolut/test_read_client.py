"""Offline contract tests; no Revolut account or network is involved."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from zeo_core.integrations.revolut import (
    NORMALIZATION_VERSION,
    RevolutAPIError,
    RevolutBusinessClient,
    RevolutEnvironment,
    RevolutTransport,
    TransactionQuery,
)

CANARY = "canary-credential-7f3e9a"  # noqa: S105 -- synthetic test value
ACCOUNT_ID = "2a0d4d05-4d4f-4f3a-9a53-1a0f6f6d3b11"
LEG_ID = "5b1c7f0e-0c6e-4f0b-8a51-7e7a2b9d1c22"
Handler = Callable[[httpx.Request], httpx.Response]


def _account(**extra: object) -> dict[str, Any]:
    return {
        "id": ACCOUNT_ID,
        "name": "Main",
        "balance": 1234.56,
        "currency": "EUR",
        "state": "active",
        "public": False,
        "created_at": "2025-01-02T03:04:05.123456Z",
        "updated_at": "2025-06-02T03:04:05Z",
        **extra,
    }


def _transaction(index: int, created: datetime, **extra: object) -> dict[str, Any]:
    return {
        "id": f"tx-{index}",
        "type": "card_payment",
        "state": "completed",
        "created_at": created.isoformat(),
        "updated_at": created.isoformat(),
        "completed_at": created.isoformat(),
        "merchant": {"name": "Hetzner", "city": "Gunzenhausen", "country": "DE"},
        "card": {
            "id": "9c9f2a1e-3a0b-4a44-9f55-0d8e1f2a3b33",
            "card_number": "535243******1234",
            "first_name": "Private",
            "last_name": "Holder",
            "phone": "+440000000000",
        },
        "legs": [
            {
                "leg_id": LEG_ID,
                "account_id": ACCOUNT_ID,
                "amount": -0.1,
                "fee": 0,
                "currency": "EUR",
                "bill_amount": -0.3,
                "bill_currency": "USD",
                "balance": 10.20,
                "counterparty": {"account_type": "external"},
                "description": "Hetzner Online",
            }
        ],
        **extra,
    }


def _client(
    handler: Handler,
    environment: RevolutEnvironment = RevolutEnvironment.SANDBOX,
) -> RevolutBusinessClient:
    return RevolutBusinessClient(
        transport=RevolutTransport(
            SecretStr(CANARY),
            environment=environment,
            transport=httpx.MockTransport(handler),
        )
    )


def _json(payload: object, status: int = 200, **headers: str) -> Handler:
    return lambda request: httpx.Response(status, json=payload, headers=headers)


def test_accounts_use_fixed_origin_bearer_and_exact_decimals() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            content=json.dumps([_account(access_token=CANARY[:6], unknown=1)]),
        )

    client = _client(handler, RevolutEnvironment.PRODUCTION)
    (account,) = client.list_accounts()
    client.close()
    assert str(seen[0].url) == "https://b2b.revolut.com/api/1.0/accounts"
    assert seen[0].headers["Authorization"] == "Bearer " + CANARY
    assert account.id == UUID(ACCOUNT_ID)
    assert account.balance == Decimal("1234.56")
    assert account.account_type is None
    dumped = account.model_dump_json()
    assert "unknown" not in dumped and "access_token" not in dumped
    assert CANARY not in dumped and CANARY not in repr(client.__dict__)


def test_transactions_drop_card_holder_data_and_keep_money_exact() -> None:
    created = datetime(2025, 3, 1, 12, tzinfo=UTC)
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[_transaction(1, created)])

    query = TransactionQuery(
        from_=created - timedelta(days=1),
        to=created + timedelta(days=1),
        account_id=UUID(ACCOUNT_ID),
        type="card_payment",
        count=50,
    )
    page = _client(handler).list_transactions(query)
    assert seen[0].url.host == "sandbox-b2b.revolut.com"
    assert dict(seen[0].url.params) == {
        "count": "50",
        "from": "2025-02-28T12:00:00Z",
        "to": "2025-03-02T12:00:00Z",
        "account": ACCOUNT_ID,
        "type": "card_payment",
    }
    assert page.normalization_version == NORMALIZATION_VERSION
    assert page.next_to is None
    (transaction,) = page.transactions
    (leg,) = transaction.legs
    assert (leg.amount, leg.bill_amount, leg.fee) == (
        Decimal("-0.1"),
        Decimal("-0.3"),
        Decimal(0),
    )
    assert transaction.card is not None and set(transaction.card.model_dump()) == {"id"}
    dumped = page.model_dump_json()
    for private in ("Holder", "535243", "+44000"):
        assert private not in dumped


def test_full_page_returns_oldest_instant_as_next_cursor() -> None:
    newest = datetime(2025, 3, 1, 12, tzinfo=UTC)
    rows = [_transaction(i, newest - timedelta(minutes=i)) for i in range(3)]
    page = _client(_json(rows)).list_transactions(TransactionQuery(count=3))
    assert page.next_to == newest - timedelta(minutes=2)
    default = _client(_json(rows)).list_transactions()
    assert default.next_to is None and len(default.transactions) == 3


def test_full_page_that_cannot_advance_is_refused() -> None:
    instant = datetime(2025, 3, 1, 12, tzinfo=UTC)
    rows = [_transaction(i, instant) for i in range(2)]
    with pytest.raises(RevolutAPIError) as caught:
        _client(_json(rows)).list_transactions(TransactionQuery(to=instant, count=2))
    assert caught.value.code == "PAGINATION_STALLED"


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (401, "AUTHENTICATION"),
        (403, "ACCESS"),
        (404, "NOT_FOUND"),
        (429, "RATE_LIMIT"),
        (500, "HTTP"),
        (302, "HTTP"),
    ],
)
def test_errors_are_classified_without_provider_bodies(status: int, code: str) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            status,
            json={"message": "provider-detail " + CANARY},
            headers={"Retry-After": "7", "Location": "https://example.invalid/"},
        )

    with pytest.raises(RevolutAPIError) as caught:
        _client(handler).list_accounts()
    error = caught.value
    assert (error.code, error.status_code) == (code, status)
    assert error.retry_after_seconds == 7
    assert calls == 1
    assert error.__cause__ is None and error.__context__ is None
    assert "provider-detail" not in str(error) and CANARY not in str(error)


def test_unparseable_retry_after_is_ignored() -> None:
    with pytest.raises(RevolutAPIError) as caught:
        _client(_json({}, 429, **{"Retry-After": "soon"})).list_accounts()
    assert caught.value.retry_after_seconds is None


def test_transport_failure_is_not_retried_and_keeps_no_context() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("refused " + CANARY, request=request)

    with pytest.raises(RevolutAPIError) as caught:
        _client(handler).list_accounts()
    assert caught.value.code == "TRANSPORT" and calls == 1
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(200, content=b"not json"),
        _json({"accounts": []}),
        _json(["not-an-object"]),
        _json([{"id": "not-a-uuid"}]),
        _json([_account(reference=CANARY)]),
        lambda request: httpx.Response(200, content=b" " * (16 * 1024 * 1024 + 1)),
    ],
)
def test_unreviewed_or_credential_bearing_responses_are_refused(
    handler: Handler,
) -> None:
    with pytest.raises(RevolutAPIError) as caught:
        _client(handler).list_accounts()
    assert caught.value.code == "RESPONSE"
    assert CANARY not in str(caught.value) and "not-a-uuid" not in str(caught.value)
    assert caught.value.__cause__ is None


def test_unrecognized_transaction_page_is_refused() -> None:
    with pytest.raises(RevolutAPIError) as caught:
        _client(_json([{"id": "tx"}])).list_transactions()
    assert caught.value.code == "RESPONSE"


def test_only_reviewed_routes_and_inputs_are_accepted() -> None:
    transport = RevolutTransport(
        SecretStr(CANARY),
        environment=RevolutEnvironment.SANDBOX,
        transport=httpx.MockTransport(_json([])),
    )
    for path in ("/pay", "/accounts/", "/transactions/../pay", "//evil.invalid"):
        with pytest.raises(ValueError, match="outside the read integration"):
            transport.get(path)
    with pytest.raises(ValueError, match="access token"):
        RevolutTransport(SecretStr(" "), environment=RevolutEnvironment.SANDBOX)
    with pytest.raises(ValueError, match="timeout"):
        RevolutTransport(
            SecretStr(CANARY), environment=RevolutEnvironment.SANDBOX, timeout=121
        )
    with pytest.raises(ValueError, match="access token"):
        RevolutBusinessClient()
    with pytest.raises(ValueError):
        RevolutTransport(SecretStr(CANARY), environment="staging")  # type: ignore[arg-type]


def test_default_client_builds_a_production_transport() -> None:
    client = RevolutBusinessClient(SecretStr(CANARY))
    assert client._transport._origin == "https://b2b.revolut.com"
    client.close()


def test_query_rejects_unbounded_naive_or_inverted_windows() -> None:
    instant = datetime(2025, 3, 1, tzinfo=UTC)
    for invalid in (
        {"count": 0},
        {"count": 1001},
        {"from_": datetime(2025, 3, 1)},  # noqa: DTZ001 -- naive on purpose
        {"from_": instant, "to": instant},
        {"type": "Card Payment"},
        {"url": "https://evil.invalid"},
    ):
        with pytest.raises(ValidationError):
            TransactionQuery.model_validate(invalid)


def test_http_client_logs_are_silenced_only_during_the_request(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger="httpx")
    _client(_json([])).list_accounts()
    assert not [r for r in caplog.records if r.name.startswith("httpx")]
    logging.getLogger("httpx").info("unrelated")
    assert [r for r in caplog.records if r.getMessage() == "unrelated"]
