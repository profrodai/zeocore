"""Behavioral contract for complete Notion API 2026-03-11 reachability."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from zeo_core.integrations.notion import (
    NOTION_API_VERSION,
    NotionAPIError,
    NotionClient,
    NotionNoDataSourceError,
    NotionOperation,
)
from zeo_core.integrations.notion.service import NotionIntegration


def _sdk() -> MagicMock:
    sdk = MagicMock()
    for path in {
        "blocks.children.append",
        "blocks.children.list",
        "blocks.meeting_notes.query",
        "blocks.retrieve",
        "blocks.update",
        "blocks.delete",
        "databases.retrieve",
        "databases.create",
        "databases.update",
        "data_sources.retrieve",
        "data_sources.query",
        "data_sources.create",
        "data_sources.update",
        "data_sources.list_templates",
        "pages.retrieve",
        "pages.properties.retrieve",
        "pages.create",
        "pages.update",
        "pages.retrieve_markdown",
        "pages.update_markdown",
        "pages.move",
        "users.list",
        "users.retrieve",
        "users.me",
        "search",
        "custom_emojis.list",
        "comments.create",
        "comments.list",
        "comments.retrieve",
        "comments.update",
        "comments.delete",
        "file_uploads.create",
        "file_uploads.send",
        "file_uploads.complete",
        "file_uploads.retrieve",
        "file_uploads.list",
        "views.create",
        "views.retrieve",
        "views.update",
        "views.delete",
        "views.list",
        "views.queries.create",
        "views.queries.results",
        "views.queries.delete",
    }:
        target = sdk
        for segment in path.split("."):
            target = getattr(target, segment)
        target.return_value = {"object": "test", "path": path}
    return sdk


def test_every_declared_operation_reaches_a_callable_sdk_endpoint() -> None:
    sdk = _sdk()
    client = NotionClient("canary-token", sdk_client=sdk)

    assert len(client.supported_operations) == 44
    assert client.supported_operations == frozenset(NotionOperation)
    for operation in NotionOperation:
        assert client.execute(operation)["object"] == "test"


def test_real_sdk_is_pinned_to_current_api_and_bounded_retry() -> None:
    client = NotionClient("not-a-live-token", max_retries=4)

    assert client._sdk.options.notion_version == NOTION_API_VERSION
    assert client._sdk.options.retry.max_retries == 4


def test_paginated_result_preserves_cursor_and_iteration_reads_every_page() -> None:
    sdk = _sdk()
    sdk.users.list.side_effect = [
        {"results": [{"id": "u1"}], "has_more": True, "next_cursor": "c2"},
        {"results": [{"id": "u2"}], "has_more": False, "next_cursor": None},
    ]
    client = NotionClient("canary-token", sdk_client=sdk)

    assert list(client.iterate(NotionOperation.USER_LIST, page_size=25)) == [
        {"id": "u1"},
        {"id": "u2"},
    ]
    assert sdk.users.list.call_args_list[1].kwargs["start_cursor"] == "c2"


@pytest.mark.parametrize("page_size", [0, 101, True, 1.5])
def test_invalid_page_size_is_rejected_before_sdk_call(page_size: object) -> None:
    sdk = _sdk()
    client = NotionClient("canary-token", sdk_client=sdk)

    with pytest.raises(ValueError, match="1 through 100"):
        client.paged(NotionOperation.USER_LIST, page_size=page_size)  # type: ignore[arg-type]
    sdk.users.list.assert_not_called()


def test_legacy_archive_argument_uses_current_wire_key() -> None:
    sdk = _sdk()
    sdk.pages.update.return_value = {"id": "p1", "in_trash": True}
    client = NotionClient("canary-token", sdk_client=sdk)

    page = client.update_page("p1", archived=True)

    assert page.in_trash is True
    sdk.pages.update.assert_called_once_with(page_id="p1", in_trash=True)


@pytest.mark.parametrize(
    "payload",
    [
        {"archived": True},
        {"after": "block-id"},
        {"children": [{"type": "transcription"}]},
    ],
)
def test_generic_surface_rejects_every_removed_2026_wire_shape(
    payload: dict[str, object],
) -> None:
    sdk = _sdk()
    client = NotionClient("canary-token", sdk_client=sdk)

    with pytest.raises(ValueError):
        client.execute(NotionOperation.PAGE_UPDATE, **payload)
    sdk.pages.update.assert_not_called()


def test_append_position_uses_2026_contract_and_never_after() -> None:
    sdk = _sdk()
    sdk.blocks.children.append.return_value = {"results": []}
    client = NotionClient("canary-token", sdk_client=sdk)

    client.append_blocks("b1", [], position={"type": "start"})

    sdk.blocks.children.append.assert_called_once_with(
        block_id="b1", children=[], position={"type": "start"}
    )


def test_append_rejects_documented_request_limits_before_sdk_call() -> None:
    sdk = _sdk()
    client = NotionClient("canary-token", sdk_client=sdk)

    with pytest.raises(ValueError, match="1000 block"):
        client.append_blocks("b1", [{}] * 1001)
    with pytest.raises(ValueError, match="500000 encoded bytes"):
        client.append_blocks("b1", [{"paragraph": {"text": "x" * 500_001}}])
    sdk.blocks.children.append.assert_not_called()


def test_database_convenience_refuses_ambiguous_multi_source_container() -> None:
    sdk = _sdk()
    sdk.databases.retrieve.return_value = {
        "id": "db1",
        "data_sources": [{"id": "a"}, {"id": "b"}],
    }
    client = NotionClient("canary-token", sdk_client=sdk)

    with pytest.raises(NotionNoDataSourceError, match="2 data sources"):
        client.query_database("db1")
    sdk.data_sources.query.assert_not_called()


def test_api_errors_drop_provider_message_and_token_from_all_text_channels() -> None:
    canary = "ntn_LIVE_SECRET_CANARY"
    sdk = _sdk()
    error = RuntimeError(f"authorization Bearer {canary}")
    error.status = 401  # type: ignore[attr-defined]
    error.code = "unauthorized"  # type: ignore[attr-defined]
    sdk.users.me.side_effect = error
    client = NotionClient(canary, sdk_client=sdk)

    with pytest.raises(NotionAPIError) as raised:
        client.execute(NotionOperation.USER_ME)

    rendered = repr(raised.value) + str(raised.value) + repr(client)
    assert canary not in rendered
    assert str(raised.value) == "Notion authentication failed"
    assert raised.value.__cause__ is None


def test_rate_limit_error_preserves_only_safe_retry_metadata() -> None:
    sdk = _sdk()
    error = RuntimeError("provider body must not be copied")
    error.status = 429  # type: ignore[attr-defined]
    error.code = SimpleNamespace(value="rate_limited")  # type: ignore[attr-defined]
    error.headers = {"retry-after": "7"}  # type: ignore[attr-defined]
    sdk.users.list.side_effect = error
    client = NotionClient("canary-token", sdk_client=sdk)

    with pytest.raises(NotionAPIError) as raised:
        client.execute(NotionOperation.USER_LIST)

    assert raised.value.code == "rate_limited"
    assert raised.value.retryable is True
    assert raised.value.retry_after == 7
    assert "provider body" not in str(raised.value)


def test_service_execute_exposes_complete_operation_surface() -> None:
    service = NotionIntegration()
    service._initialized = True
    service.client = MagicMock()
    service.client.execute.return_value = {"object": "user", "id": "me"}

    result = service.execute(NotionOperation.USER_ME)

    assert result.success is True
    assert result.content == {"object": "user", "id": "me"}
    service.client.execute.assert_called_once_with(NotionOperation.USER_ME)


def test_client_and_config_have_no_public_raw_token_attribute() -> None:
    client = NotionClient("ntn_LIVE_SECRET_CANARY", sdk_client=_sdk())

    assert not hasattr(client, "token")
    assert "ntn_LIVE_SECRET_CANARY" not in repr(client)
