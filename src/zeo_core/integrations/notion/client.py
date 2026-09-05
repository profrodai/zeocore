"""Complete synchronous facade for Notion API 2026-03-11."""

# ruff: noqa: ANN401, A002 -- the upstream API is an intentionally heterogeneous
# JSON surface; preserving arbitrary keyword payloads is the compatibility seam.

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Mapping
from enum import StrEnum
from typing import Any

from .models import (
    NotionBlock,
    NotionDatabase,
    NotionDataSource,
    NotionPage,
    NotionPageResult,
)

NOTION_API_VERSION = "2026-03-11"
MAX_PAGE_SIZE = 100
MAX_BLOCK_CHILDREN = 1_000
MAX_REQUEST_BYTES = 500_000


class NotionNoDataSourceError(ValueError):
    """A database has no single unambiguous data source."""


class NotionAPIError(RuntimeError):
    """Credential-free normalized Notion failure."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "notion_error",
        status: int | None = None,
        retryable: bool = False,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.code, self.status = code, status
        self.retryable, self.retry_after = retryable, retry_after


class NotionOperation(StrEnum):
    """All public non-OAuth operations in notion-client 3.1.0."""

    BLOCK_APPEND_CHILDREN = "block.append_children"
    BLOCK_LIST_CHILDREN = "block.list_children"
    BLOCK_QUERY_MEETING_NOTES = "block.query_meeting_notes"
    BLOCK_RETRIEVE = "block.retrieve"
    BLOCK_UPDATE = "block.update"
    BLOCK_DELETE = "block.delete"
    DATABASE_RETRIEVE = "database.retrieve"
    DATABASE_CREATE = "database.create"
    DATABASE_UPDATE = "database.update"
    DATA_SOURCE_RETRIEVE = "data_source.retrieve"
    DATA_SOURCE_QUERY = "data_source.query"
    DATA_SOURCE_CREATE = "data_source.create"
    DATA_SOURCE_UPDATE = "data_source.update"
    DATA_SOURCE_LIST_TEMPLATES = "data_source.list_templates"
    PAGE_RETRIEVE = "page.retrieve"
    PAGE_RETRIEVE_PROPERTY = "page.retrieve_property"
    PAGE_CREATE = "page.create"
    PAGE_UPDATE = "page.update"
    PAGE_RETRIEVE_MARKDOWN = "page.retrieve_markdown"
    PAGE_UPDATE_MARKDOWN = "page.update_markdown"
    PAGE_MOVE = "page.move"
    USER_LIST = "user.list"
    USER_RETRIEVE = "user.retrieve"
    USER_ME = "user.me"
    SEARCH = "search"
    CUSTOM_EMOJI_LIST = "custom_emoji.list"
    COMMENT_CREATE = "comment.create"
    COMMENT_LIST = "comment.list"
    COMMENT_RETRIEVE = "comment.retrieve"
    COMMENT_UPDATE = "comment.update"
    COMMENT_DELETE = "comment.delete"
    FILE_UPLOAD_CREATE = "file_upload.create"
    FILE_UPLOAD_SEND = "file_upload.send"
    FILE_UPLOAD_COMPLETE = "file_upload.complete"
    FILE_UPLOAD_RETRIEVE = "file_upload.retrieve"
    FILE_UPLOAD_LIST = "file_upload.list"
    VIEW_CREATE = "view.create"
    VIEW_RETRIEVE = "view.retrieve"
    VIEW_UPDATE = "view.update"
    VIEW_DELETE = "view.delete"
    VIEW_LIST = "view.list"
    VIEW_QUERY_CREATE = "view_query.create"
    VIEW_QUERY_RESULTS = "view_query.results"
    VIEW_QUERY_DELETE = "view_query.delete"


_PATHS: Mapping[NotionOperation, str] = {
    NotionOperation.BLOCK_APPEND_CHILDREN: "blocks.children.append",
    NotionOperation.BLOCK_LIST_CHILDREN: "blocks.children.list",
    NotionOperation.BLOCK_QUERY_MEETING_NOTES: "blocks.meeting_notes.query",
    NotionOperation.BLOCK_RETRIEVE: "blocks.retrieve",
    NotionOperation.BLOCK_UPDATE: "blocks.update",
    NotionOperation.BLOCK_DELETE: "blocks.delete",
    NotionOperation.DATABASE_RETRIEVE: "databases.retrieve",
    NotionOperation.DATABASE_CREATE: "databases.create",
    NotionOperation.DATABASE_UPDATE: "databases.update",
    NotionOperation.DATA_SOURCE_RETRIEVE: "data_sources.retrieve",
    NotionOperation.DATA_SOURCE_QUERY: "data_sources.query",
    NotionOperation.DATA_SOURCE_CREATE: "data_sources.create",
    NotionOperation.DATA_SOURCE_UPDATE: "data_sources.update",
    NotionOperation.DATA_SOURCE_LIST_TEMPLATES: "data_sources.list_templates",
    NotionOperation.PAGE_RETRIEVE: "pages.retrieve",
    NotionOperation.PAGE_RETRIEVE_PROPERTY: "pages.properties.retrieve",
    NotionOperation.PAGE_CREATE: "pages.create",
    NotionOperation.PAGE_UPDATE: "pages.update",
    NotionOperation.PAGE_RETRIEVE_MARKDOWN: "pages.retrieve_markdown",
    NotionOperation.PAGE_UPDATE_MARKDOWN: "pages.update_markdown",
    NotionOperation.PAGE_MOVE: "pages.move",
    NotionOperation.USER_LIST: "users.list",
    NotionOperation.USER_RETRIEVE: "users.retrieve",
    NotionOperation.USER_ME: "users.me",
    NotionOperation.SEARCH: "search",
    NotionOperation.CUSTOM_EMOJI_LIST: "custom_emojis.list",
    NotionOperation.COMMENT_CREATE: "comments.create",
    NotionOperation.COMMENT_LIST: "comments.list",
    NotionOperation.COMMENT_RETRIEVE: "comments.retrieve",
    NotionOperation.COMMENT_UPDATE: "comments.update",
    NotionOperation.COMMENT_DELETE: "comments.delete",
    NotionOperation.FILE_UPLOAD_CREATE: "file_uploads.create",
    NotionOperation.FILE_UPLOAD_SEND: "file_uploads.send",
    NotionOperation.FILE_UPLOAD_COMPLETE: "file_uploads.complete",
    NotionOperation.FILE_UPLOAD_RETRIEVE: "file_uploads.retrieve",
    NotionOperation.FILE_UPLOAD_LIST: "file_uploads.list",
    NotionOperation.VIEW_CREATE: "views.create",
    NotionOperation.VIEW_RETRIEVE: "views.retrieve",
    NotionOperation.VIEW_UPDATE: "views.update",
    NotionOperation.VIEW_DELETE: "views.delete",
    NotionOperation.VIEW_LIST: "views.list",
    NotionOperation.VIEW_QUERY_CREATE: "views.queries.create",
    NotionOperation.VIEW_QUERY_RESULTS: "views.queries.results",
    NotionOperation.VIEW_QUERY_DELETE: "views.queries.delete",
}


class NotionClient:
    """Current-version Notion client with complete endpoint reachability."""

    def __init__(
        self,
        token: str,
        timeout_ms: int = 60_000,
        max_retries: int = 3,
        sdk_client: Any = None,
    ) -> None:  # noqa: ANN401, E501
        if not token or not token.strip():
            raise ValueError("A non-empty Notion token is required")
        self.timeout_ms, self.max_retries = timeout_ms, max_retries
        if sdk_client is not None:
            self._sdk = sdk_client
        else:
            from notion_client import Client as SDKClient
            from notion_client import RetryOptions

            self._sdk = SDKClient(
                auth=token,
                notion_version=NOTION_API_VERSION,
                timeout_ms=timeout_ms,
                retry=RetryOptions(max_retries=max_retries),
            )

    def __repr__(self) -> str:
        return (
            f"NotionClient(api_version={NOTION_API_VERSION!r}, "
            f"timeout_ms={self.timeout_ms}, max_retries={self.max_retries})"
        )

    @property
    def supported_operations(self) -> frozenset[NotionOperation]:
        return frozenset(_PATHS)

    def execute(
        self, operation: NotionOperation | str, **kwargs: Any
    ) -> dict[str, Any]:  # noqa: ANN401
        _assert_current_payload(kwargs)
        try:
            selected = NotionOperation(operation)
        except ValueError:
            raise ValueError("Unsupported Notion operation") from None
        target: Any = self._sdk
        for segment in _PATHS[selected].split("."):
            target = getattr(target, segment)
        return self._call(target, **kwargs)

    def _call(self, function: Callable[..., Any], **kwargs: Any) -> dict[str, Any]:
        try:
            response = function(**kwargs)
            return response if isinstance(response, dict) else dict(response)
        except Exception as exc:
            # Provider exceptions can retain request data.  The normalized
            # error is deliberately bounded, so do not chain the original.
            raise _normalize_error(exc) from None

    def paged(
        self,
        operation: NotionOperation | str,
        *,
        page_size: int = MAX_PAGE_SIZE,
        start_cursor: str | None = None,
        **kwargs: Any,
    ) -> NotionPageResult[dict[str, Any]]:  # noqa: ANN401, E501
        _validate_page_size(page_size)
        if start_cursor is not None:
            kwargs["start_cursor"] = start_cursor
        kwargs["page_size"] = page_size
        return NotionPageResult.from_response(self.execute(operation, **kwargs))

    def iterate(
        self,
        operation: NotionOperation | str,
        *,
        page_size: int = MAX_PAGE_SIZE,
        **kwargs: Any,
    ) -> Iterator[dict[str, Any]]:  # noqa: ANN401, E501
        cursor: str | None = None
        while True:
            page = self.paged(
                operation, page_size=page_size, start_cursor=cursor, **kwargs
            )
            yield from page.items
            if not page.has_more:
                return
            if not page.next_cursor:
                raise NotionAPIError(
                    "Notion returned has_more without next_cursor",
                    code="invalid_pagination_response",
                )
            cursor = page.next_cursor

    def get_page(self, page_id: str) -> NotionPage:
        return _page(self.execute(NotionOperation.PAGE_RETRIEVE, page_id=page_id))

    def list_page_blocks(
        self, page_id: str, page_size: int = 100, start_cursor: str | None = None
    ) -> tuple[list[NotionBlock], str | None]:
        page = self.paged(
            NotionOperation.BLOCK_LIST_CHILDREN,
            block_id=page_id,
            page_size=page_size,
            start_cursor=start_cursor,
        )
        return [_block(item) for item in page.items], page.next_cursor

    def search(
        self,
        query: str | None = None,
        filter_object_type: str | None = None,
        page_size: int = 100,
        start_cursor: str | None = None,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {}
        if query:
            kwargs["query"] = query
        if filter_object_type:
            if filter_object_type not in {"page", "data_source"}:
                raise ValueError("filter_object_type must be 'page' or 'data_source'")
            kwargs["filter"] = {"property": "object", "value": filter_object_type}
        return self.paged(
            NotionOperation.SEARCH,
            page_size=page_size,
            start_cursor=start_cursor,
            **kwargs,
        ).items

    def get_database(self, database_id: str) -> NotionDatabase:
        return _database(
            self.execute(NotionOperation.DATABASE_RETRIEVE, database_id=database_id)
        )

    def list_data_sources(self, database_id: str) -> list[NotionDataSource]:
        return self.get_database(database_id).data_sources

    def query_data_source(
        self,
        data_source_id: str,
        filter: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
        page_size: int = 100,
        start_cursor: str | None = None,
    ) -> tuple[list[NotionPage], str | None]:  # noqa: A002, E501
        kwargs: dict[str, Any] = {"data_source_id": data_source_id}
        if filter is not None:
            kwargs["filter"] = filter
        if sorts is not None:
            kwargs["sorts"] = sorts
        page = self.paged(
            NotionOperation.DATA_SOURCE_QUERY,
            page_size=page_size,
            start_cursor=start_cursor,
            **kwargs,
        )
        return [_page(item) for item in page.items], page.next_cursor

    def _sole_data_source(self, database_id: str) -> str:
        sources = self.list_data_sources(database_id)
        if len(sources) != 1:
            raise NotionNoDataSourceError(
                f"Database {database_id} has {len(sources)} data sources; "
                "pass a data_source_id explicitly"
            )
        return sources[0].id

    def query_database(
        self, database_id: str, **kwargs: Any
    ) -> tuple[list[NotionPage], str | None]:  # noqa: ANN401
        return self.query_data_source(self._sole_data_source(database_id), **kwargs)

    def create_page(
        self,
        parent: dict[str, Any],
        properties: dict[str, Any],
        children: list[dict[str, Any]] | None = None,
        **fields: Any,
    ) -> NotionPage:  # noqa: ANN401, E501
        kwargs: dict[str, Any] = {"parent": parent, "properties": properties, **fields}
        if children is not None:
            _validate_block_payload(children)
            kwargs["children"] = children
        return _page(self.execute(NotionOperation.PAGE_CREATE, **kwargs))

    def create_database_entry(
        self,
        database_id: str,
        properties: dict[str, Any],
        children: list[dict[str, Any]] | None = None,
    ) -> NotionPage:
        parent = {
            "type": "data_source_id",
            "data_source_id": self._sole_data_source(database_id),
        }
        return self.create_page(parent, properties, children)

    def update_page(
        self,
        page_id: str,
        properties: dict[str, Any] | None = None,
        archived: bool | None = None,
        *,
        in_trash: bool | None = None,
        **fields: Any,
    ) -> NotionPage:  # noqa: ANN401, E501
        if archived is not None and in_trash is not None:
            raise ValueError("Pass only in_trash; archived is a compatibility alias")
        kwargs: dict[str, Any] = {"page_id": page_id, **fields}
        if properties is not None:
            kwargs["properties"] = properties
        trash = in_trash if in_trash is not None else archived
        if trash is not None:
            kwargs["in_trash"] = trash
        return _page(self.execute(NotionOperation.PAGE_UPDATE, **kwargs))

    def append_blocks(
        self,
        block_id: str,
        children: list[dict[str, Any]],
        *,
        position: dict[str, Any] | None = None,
    ) -> list[NotionBlock]:
        _validate_block_payload(children)
        kwargs: dict[str, Any] = {"block_id": block_id, "children": children}
        if position is not None:
            kwargs["position"] = position
        data = self.execute(NotionOperation.BLOCK_APPEND_CHILDREN, **kwargs)
        return [_block(item) for item in data.get("results", [])]

    def update_block(self, block_id: str, **fields: Any) -> NotionBlock:  # noqa: ANN401
        return _block(
            self.execute(NotionOperation.BLOCK_UPDATE, block_id=block_id, **fields)
        )

    def delete_block(self, block_id: str) -> NotionBlock:
        return _block(self.execute(NotionOperation.BLOCK_DELETE, block_id=block_id))


def _validate_page_size(page_size: int) -> None:
    if (
        isinstance(page_size, bool)
        or not isinstance(page_size, int)
        or not 1 <= page_size <= MAX_PAGE_SIZE
    ):
        raise ValueError("page_size must be an integer from 1 through 100")


def _validate_block_payload(children: list[dict[str, Any]]) -> None:
    if len(children) > MAX_BLOCK_CHILDREN:
        raise ValueError("A Notion request may contain at most 1000 block elements")
    encoded = json.dumps(children, ensure_ascii=False, separators=(",", ":")).encode()
    if len(encoded) > MAX_REQUEST_BYTES:
        raise ValueError("A Notion request may contain at most 500000 encoded bytes")


def _assert_current_payload(value: object) -> None:
    """Reject fields removed from the selected wire version at any depth."""
    if isinstance(value, dict):
        removed = {"archived", "after"}.intersection(value)
        if removed:
            names = ", ".join(sorted(removed))
            raise ValueError(f"Notion API {NOTION_API_VERSION} removed: {names}")
        if value.get("type") == "transcription":
            raise ValueError(
                f"Notion API {NOTION_API_VERSION} renamed transcription "
                "to meeting_notes"
            )
        for nested in value.values():
            _assert_current_payload(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _assert_current_payload(nested)


def _normalize_error(exc: Exception) -> NotionAPIError:
    status = getattr(exc, "status", None)
    code_value = getattr(exc, "code", None)
    code = getattr(code_value, "value", code_value) or type(exc).__name__
    headers, retry_after = getattr(exc, "headers", None), None
    if headers:
        try:
            retry_after = float(headers.get("retry-after"))
        except TypeError, ValueError:
            pass
    retryable = status == 429 or (isinstance(status, int) and status >= 500)
    messages: dict[int | None, str] = {
        400: "Notion rejected the request",
        401: "Notion authentication failed",
        403: "Notion denied the requested capability",
        404: "Notion resource was not found or is not shared with the integration",
        409: "Notion reported a conflict",
        429: "Notion rate limit was exhausted after bounded retries",
    }
    message = messages.get(
        status if isinstance(status, int) else None, "Notion request failed"
    )
    return NotionAPIError(
        message,
        code=str(code),
        status=status if isinstance(status, int) else None,
        retryable=retryable,
        retry_after=retry_after,
    )


def _page(data: dict[str, Any]) -> NotionPage:
    return NotionPage(
        id=data.get("id", ""),
        url=data.get("url"),
        created_time=data.get("created_time"),
        last_edited_time=data.get("last_edited_time"),
        in_trash=data.get("in_trash", data.get("archived", False)),
        parent=data.get("parent", {}),
        properties=data.get("properties", {}),
        raw=data,
    )


def _database(data: dict[str, Any]) -> NotionDatabase:
    title = "".join(part.get("plain_text", "") for part in data.get("title", []))
    sources = [
        NotionDataSource(id=item.get("id", ""), name=item.get("name"), raw=item)
        for item in data.get("data_sources", [])
    ]
    return NotionDatabase(
        id=data.get("id", ""),
        title=title,
        url=data.get("url"),
        in_trash=data.get("in_trash", data.get("archived", False)),
        data_sources=sources,
        raw=data,
    )


def _block(data: dict[str, Any]) -> NotionBlock:
    kind = data.get("type", "")
    return NotionBlock(
        id=data.get("id", ""),
        type=kind,
        has_children=data.get("has_children", False),
        in_trash=data.get("in_trash", data.get("archived", False)),
        content=data.get(kind, {}) if kind else {},
        raw=data,
    )


# Historical private names retained for callers/tests that imported them.
_page_from_response = _page
_database_from_response = _database
_block_from_response = _block
