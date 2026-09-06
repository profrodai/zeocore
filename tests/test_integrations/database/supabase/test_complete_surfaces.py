"""Cross-surface acceptance tests for the public Supabase integration."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from zeo_core.integrations.database.supabase import (
    SupabaseAPIError,
    SupabaseClient,
    SupabaseConfigProvider,
    SupabaseFilter,
    SupabaseIntegration,
    SupabaseKeyKind,
    SupabaseRealtimeClient,
)


def _sdk() -> MagicMock:
    sdk = MagicMock()
    query = MagicMock()
    for method in (
        "select",
        "eq",
        "order",
        "range",
        "insert",
        "upsert",
        "update",
        "delete",
    ):
        getattr(query, method).return_value = query
    query.execute.return_value = SimpleNamespace(data=[{"id": 1}], count=1)
    sdk.table.return_value = query
    sdk.rpc.return_value = query
    user = SimpleNamespace(
        id="user-1",
        email="member@example.com",
        phone=None,
        app_metadata={},
        user_metadata={},
        created_at=None,
    )
    auth_response = SimpleNamespace(user=user, session=SimpleNamespace(expires_at=123))
    sdk.auth.sign_up.return_value = auth_response
    sdk.auth.sign_in_with_password.return_value = auth_response
    sdk.auth.sign_in_with_otp.return_value = auth_response
    sdk.auth.get_user.return_value = auth_response
    sdk.auth.refresh_session.return_value = auth_response
    sdk.auth.sign_in_with_oauth.return_value = SimpleNamespace(
        url="https://example.supabase.co/auth/v1/authorize?provider=google"
    )
    sdk.storage.list_buckets.return_value = [
        {
            "id": "artifacts",
            "name": "artifacts",
            "public": False,
            "allowed_mime_types": ["text/plain"],
        }
    ]
    bucket = sdk.storage.from_.return_value
    bucket.download.return_value = b"hello"
    bucket.list.return_value = [{"name": "one.txt"}]
    sdk.functions.invoke.return_value = {"ok": True}
    return sdk


def test_integration_exercises_every_sync_product_surface(tmp_path: Path) -> None:
    sdk = _sdk()
    client = SupabaseClient(
        "https://example.supabase.co",
        "sb_publishable_test",
        sdk_client=sdk,
        max_rows=50,
        max_object_bytes=100,
    )
    realtime = MagicMock()
    service = SupabaseIntegration(client=client, realtime_client=realtime)
    row_filter = (SupabaseFilter(field="id", value=1),)
    opaque_value = "not-secret-test-value"
    local_file = tmp_path / "one.txt"
    local_file.write_bytes(b"hello")

    assert service.select("items", limit=1).success
    assert service.insert("items", {"id": 1}).success
    assert service.upsert("items", {"id": 1}, on_conflict="id").success
    assert service.update("items", {"name": "tea"}, filters=row_filter).success
    assert service.delete("items", filters=row_filter).success
    assert service.rpc("claim_item", {"id": 1}, read_only=True).success

    assert service.sign_up(email="member@example.com", password=opaque_value).success
    assert service.sign_in_with_password(
        email="member@example.com", password=opaque_value
    ).success
    assert service.sign_in_with_otp(email="member@example.com").success
    assert service.begin_oauth("google").success
    assert service.get_user().success
    assert service.refresh_session().success
    assert service.sign_out(scope="global").success
    assert service.reset_password_email("member@example.com").success

    assert service.list_buckets().success
    assert service.create_bucket(
        "artifacts", file_size_limit=100, allowed_mime_types=("text/plain",)
    ).success
    assert service.upload_bytes("artifacts", "one.txt", b"hello").success
    assert service.upload_file("artifacts", "two.txt", local_file).success
    assert service.download_bytes("artifacts", "one.txt").content == b"hello"
    assert service.list_objects(
        "artifacts", prefix="folder", limit=50, search="one"
    ).success
    assert service.move_object("artifacts", "one.txt", "moved.txt").success
    assert service.copy_object("artifacts", "moved.txt", "copy.txt").success
    assert service.remove_objects("artifacts", ("copy.txt",)).success
    assert service.delete_bucket("artifacts", empty_first=True).success

    assert service.invoke_function(
        "render-report", body={"id": 1}, timeout_seconds=5
    ).success
    assert service.realtime is realtime
    assert service.name == "Supabase"
    assert service.version == "1.0.0"


def test_bounded_edge_and_invalid_response_paths(tmp_path: Path) -> None:
    sdk = _sdk()
    client = SupabaseClient(
        "https://example.supabase.co",
        "sb_publishable_test",
        sdk_client=sdk,
        max_rows=2,
        max_object_bytes=5,
    )

    with pytest.raises(SupabaseAPIError):
        client.select("items", offset=-1)
    with pytest.raises(SupabaseAPIError):
        client.select("items", limit=3)
    with pytest.raises(ValueError):
        client.select("items", columns=())
    with pytest.raises(ValueError):
        client.select("items", count="wrong")
    with pytest.raises(ValueError):
        client.insert("items", {})
    with pytest.raises(ValueError):
        client.insert("items", [{"id": 1}, {"id": 2}, {"id": 3}])
    with pytest.raises(ValueError):
        client.update("items", {}, filters=(SupabaseFilter(field="id", value=1),))
    with pytest.raises(ValueError):
        client.sign_out(scope="somewhere")
    with pytest.raises(ValueError):
        client.create_bucket("artifacts", file_size_limit=6)
    with pytest.raises(ValueError):
        client.list_objects("artifacts", limit=0)
    with pytest.raises(ValueError):
        client.remove_objects("artifacts", ())
    with pytest.raises(ValueError):
        client.invoke_function("render-report", timeout_seconds=31)

    oversized = tmp_path / "large.bin"
    oversized.write_bytes(b"123456")
    with pytest.raises(ValueError):
        client.upload_file("artifacts", "large.bin", oversized)

    sdk.table.return_value.select.return_value.execute.return_value = SimpleNamespace(
        data="not rows"
    )
    with pytest.raises(SupabaseAPIError):
        client.select("items")
    sdk.storage.from_.return_value.download.return_value = "not bytes"
    with pytest.raises(SupabaseAPIError):
        client.download_bytes("artifacts", "one.txt")
    sdk.storage.from_.return_value.list.return_value = "not objects"
    with pytest.raises(SupabaseAPIError):
        client.list_objects("artifacts", limit=2)


def test_safe_response_normalization_variants() -> None:
    sdk = _sdk()
    client = SupabaseClient(
        "https://example.supabase.co", "sb_publishable_test", sdk_client=sdk
    )
    query = sdk.table.return_value.select.return_value

    query.execute.return_value = SimpleNamespace(data=None, count=None)
    assert client.select("items").rows == []
    query.execute.return_value = SimpleNamespace(data={"id": 1}, count=None)
    assert client.select("items").rows == [{"id": 1}]

    sdk.auth.get_user.side_effect = RuntimeError("credential canary")
    with pytest.raises(SupabaseAPIError) as caught:
        client.get_user()
    assert "credential canary" not in str(caught.value)

    sdk.auth.get_user.side_effect = None
    sdk.auth.get_user.return_value = {"user": {"id": "user-2"}}
    assert client.get_user().user is not None

    sdk.storage.list_buckets.return_value = [{"id": "private"}]
    assert client.list_buckets()[0].name == "private"
    sdk.storage.list_buckets.return_value = [{"name": "missing-id"}]
    with pytest.raises(SupabaseAPIError):
        client.list_buckets()

    response = MagicMock()
    response.json.side_effect = ValueError("not json")
    sdk.functions.invoke.return_value = response
    assert client.invoke_function("render-report").data is None


def test_configuration_and_constructor_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError):
        SupabaseClient("https://example.supabase.co", "", sdk_client=MagicMock())
    with pytest.raises(ValueError):
        SupabaseClient(
            "https://example.supabase.co",
            "key",
            timeout_seconds=0,
            sdk_client=MagicMock(),
        )
    with pytest.raises(ValueError):
        SupabaseClient(
            "https://example.supabase.co",
            "key",
            max_rows=0,
            sdk_client=MagicMock(),
        )
    with pytest.raises(ValueError):
        SupabaseClient(
            "https://example.supabase.co",
            "key",
            max_object_bytes=0,
            sdk_client=MagicMock(),
        )
    with pytest.raises(ValueError):
        SupabaseRealtimeClient("https://example.supabase.co", "")

    provider = SupabaseConfigProvider()
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    assert not provider.load_config().success
    assert not provider.validate_config({"timeout_seconds": 0})

    with pytest.raises(ValidationError):
        SupabaseFilter(field="id", value=1, unexpected=True)  # type: ignore[call-arg]


def test_uninitialized_and_initialization_failure_are_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = SupabaseIntegration()
    assert not service.select("items").success
    with pytest.raises(RuntimeError):
        _ = service.realtime

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")

    def broken_factory(**_: object) -> SupabaseClient:
        raise RuntimeError("provider secret should never escape")

    service = SupabaseIntegration(client_factory=broken_factory)
    result = service.initialize()
    assert not result.success
    assert "provider secret" not in result.model_dump_json()


def test_key_kinds_and_environment_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    from zeo_core.integrations.database.supabase import SupabaseAuthProvider

    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    absent = SupabaseAuthProvider.from_environment()
    assert not absent.authenticate().success
    privileged = SupabaseAuthProvider.from_environment(allow_privileged_key=True)
    assert privileged.key_kind is SupabaseKeyKind.PRIVILEGED
    assert privileged.refresh_credentials().success
    assert privileged.save_credentials() is False
