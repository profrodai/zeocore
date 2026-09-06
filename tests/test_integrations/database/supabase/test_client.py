"""Behavioral tests for the bounded Supabase facade."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from zeo_core.integrations.database.supabase import (
    SupabaseAPIError,
    SupabaseClient,
    SupabaseFilter,
    SupabaseFilterOperator,
    SupabaseOrder,
)


@pytest.fixture
def sdk() -> MagicMock:
    client = MagicMock()
    query = MagicMock()
    for method in (
        "select",
        "eq",
        "neq",
        "gt",
        "gte",
        "lt",
        "lte",
        "like",
        "ilike",
        "is_",
        "in_",
        "contains",
        "contained_by",
        "overlaps",
        "order",
        "range",
        "insert",
        "upsert",
        "update",
        "delete",
    ):
        getattr(query, method).return_value = query
    query.execute.return_value = SimpleNamespace(data=[{"id": 1}], count=1)
    client.table.return_value = query
    client.rpc.return_value = query
    return client


@pytest.fixture
def client(sdk: MagicMock) -> SupabaseClient:
    return SupabaseClient(
        "https://example.supabase.co",
        "sb_publishable_canary",
        sdk_client=sdk,
        max_rows=50,
        max_object_bytes=32,
    )


def test_select_applies_typed_filters_order_and_range(
    client: SupabaseClient, sdk: MagicMock
) -> None:
    result = client.select(
        "items",
        columns=("id", "name"),
        filters=(
            SupabaseFilter(
                field="status", operator=SupabaseFilterOperator.EQ, value="ready"
            ),
        ),
        orders=(SupabaseOrder(field="created_at", descending=True),),
        offset=10,
        limit=5,
        count="exact",
    )

    query = sdk.table.return_value
    sdk.table.assert_called_once_with("items")
    query.select.assert_called_once_with("id,name", count="exact")
    query.eq.assert_called_once_with("status", "ready")
    query.order.assert_called_once_with("created_at", desc=True, nullsfirst=False)
    query.range.assert_called_once_with(10, 14)
    assert result.rows == [{"id": 1}]
    assert result.count == 1


@pytest.mark.parametrize(
    "table", ["public.items", "items;drop table users", "https://evil.example"]
)
def test_table_names_are_not_sql_or_urls(client: SupabaseClient, table: str) -> None:
    with pytest.raises(ValueError, match="unqualified identifier"):
        client.select(table)


def test_database_mutations_are_bounded(client: SupabaseClient, sdk: MagicMock) -> None:
    client.insert("items", {"name": "tea"})
    client.upsert("items", [{"id": 1}], on_conflict="id")
    mutation_filter = (SupabaseFilter(field="id", value=1),)
    client.update("items", {"name": "coffee"}, filters=mutation_filter)
    client.delete("items", filters=mutation_filter)

    query = sdk.table.return_value
    query.insert.assert_called_once_with({"name": "tea"})
    query.upsert.assert_called_once_with(
        [{"id": 1}], on_conflict="id", ignore_duplicates=False
    )
    query.update.assert_called_once_with({"name": "coffee"})
    query.delete.assert_called_once_with()


def test_update_and_delete_refuse_unbounded_mutation(client: SupabaseClient) -> None:
    with pytest.raises(ValueError, match="update requires"):
        client.update("items", {"name": "all"}, filters=())
    with pytest.raises(ValueError, match="delete requires"):
        client.delete("items", filters=())


def test_rpc_accepts_names_not_sql(client: SupabaseClient, sdk: MagicMock) -> None:
    client.rpc("claim_job", {"job_id": "one"}, read_only=True)
    sdk.rpc.assert_called_once_with("claim_job", {"job_id": "one"}, get=True)
    with pytest.raises(ValueError):
        client.rpc("select * from vault.decrypted_secrets")


def test_auth_results_never_transport_session_tokens(
    client: SupabaseClient, sdk: MagicMock
) -> None:
    canary = "sb-session-CREDENTIAL-CANARY"
    user = SimpleNamespace(
        id="user-1",
        email="member@example.com",
        phone=None,
        app_metadata={},
        user_metadata={},
        created_at=None,
    )
    sdk.auth.sign_in_with_password.return_value = SimpleNamespace(
        user=user,
        session=SimpleNamespace(
            access_token=canary,
            refresh_token=canary,
            expires_at=123,
        ),
    )

    result = client.sign_in_with_password(email="member@example.com", password=canary)

    assert result.authenticated is True
    assert result.user is not None and result.user.id == "user-1"
    channels = (
        repr(result),
        str(result),
        result.model_dump(),
        result.model_dump_json(),
    )
    assert all(canary not in str(channel) for channel in channels)


def test_oauth_returns_only_valid_browser_url(
    client: SupabaseClient, sdk: MagicMock
) -> None:
    sdk.auth.sign_in_with_oauth.return_value = SimpleNamespace(
        url="https://example.supabase.co/auth/v1/authorize?provider=google"
    )
    result = client.begin_oauth(
        "google", redirect_to="https://connect.example/callback", scopes="openid"
    )
    assert result.provider == "google"
    assert result.authorization_url.startswith("https://example.supabase.co/")


def test_oauth_refuses_authorization_url_on_another_origin(
    client: SupabaseClient, sdk: MagicMock
) -> None:
    sdk.auth.sign_in_with_oauth.return_value = SimpleNamespace(
        url="https://attacker.example/auth/v1/authorize?provider=google"
    )
    with pytest.raises(SupabaseAPIError):
        client.begin_oauth("google")


def test_storage_enforces_paths_and_size(
    client: SupabaseClient, sdk: MagicMock
) -> None:
    bucket = MagicMock()
    sdk.storage.from_.return_value = bucket
    bucket.download.return_value = b"hello"

    client.upload_bytes("artifacts", "reports/one.json", b"hello")
    assert client.download_bytes("artifacts", "reports/one.json") == b"hello"
    with pytest.raises(ValueError, match="traversal"):
        client.upload_bytes("artifacts", "../secret", b"x")
    with pytest.raises(ValueError, match="size bound"):
        client.upload_bytes("artifacts", "large.bin", b"x" * 33)


def test_oversized_download_refuses_after_provider_call(
    client: SupabaseClient, sdk: MagicMock
) -> None:
    sdk.storage.from_.return_value.download.return_value = b"x" * 33
    with pytest.raises(SupabaseAPIError) as caught:
        client.download_bytes("artifacts", "large.bin")
    assert caught.value.code == "storage_response_too_large"


@pytest.mark.parametrize("header", ["Authorization", "apikey", "COOKIE"])
def test_function_invocation_rejects_credential_headers(
    client: SupabaseClient, header: str
) -> None:
    with pytest.raises(ValueError, match="credential headers"):
        client.invoke_function("render-report", headers={header: "canary"})


def test_function_response_is_bounded(client: SupabaseClient, sdk: MagicMock) -> None:
    response = MagicMock(status_code=201)
    response.json.return_value = {"ok": True}
    sdk.functions.invoke.return_value = response
    result = client.invoke_function("render-report", body={"id": 1})
    assert result.status_code == 201
    assert result.data == {"ok": True}


def test_upstream_error_text_is_discarded(
    client: SupabaseClient, sdk: MagicMock
) -> None:
    canary = "sb_secret_NEVER_DISCLOSE_THIS"
    sdk.table.return_value.select.side_effect = RuntimeError(canary)
    with pytest.raises(SupabaseAPIError) as caught:
        client.select("items")
    assert canary not in repr(caught.value)
    assert canary not in str(caught.value)


@pytest.mark.parametrize("operation", ["insert", "upsert", "update", "delete"])
def test_mutation_builder_error_text_is_discarded(
    client: SupabaseClient, sdk: MagicMock, operation: str
) -> None:
    canary = "sb_secret_MUTATION_BUILDER_CANARY"
    getattr(sdk.table.return_value, operation).side_effect = RuntimeError(canary)
    mutation_filter = (SupabaseFilter(field="id", value=1),)

    with pytest.raises(SupabaseAPIError) as caught:
        if operation == "insert":
            client.insert("items", {"id": 1})
        elif operation == "upsert":
            client.upsert("items", {"id": 1})
        elif operation == "update":
            client.update("items", {"name": "tea"}, filters=mutation_filter)
        else:
            client.delete("items", filters=mutation_filter)

    assert canary not in repr(caught.value)
    assert canary not in str(caught.value)


@pytest.mark.parametrize(
    "url",
    [
        "http://example.supabase.co",
        "ftp://example.supabase.co",
        "https://user:password@example.supabase.co",
        "https://example.supabase.co/rest/v1",
        "https://example.supabase.co?key=secret",
    ],
)
def test_project_url_rejects_unsafe_shapes(url: str) -> None:
    with pytest.raises(ValueError):
        SupabaseClient(url, "sb_publishable_test", sdk_client=MagicMock())


def test_repr_redacts_project_key(client: SupabaseClient) -> None:
    assert "sb_publishable_canary" not in repr(client)
    assert "<redacted>" in repr(client)
