"""Bounded synchronous facade over the maintained Supabase Python client."""

# ruff: noqa: ANN401 -- supabase-py returns intentionally heterogeneous JSON.

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .errors import SupabaseAPIError, normalize_supabase_error
from .models import (
    SupabaseBucket,
    SupabaseFilter,
    SupabaseFunctionResult,
    SupabaseOAuthStart,
    SupabaseOrder,
    SupabaseRowPage,
    SupabaseSessionStatus,
    SupabaseUser,
)
from .validation import (
    require_function_name,
    require_identifier,
    require_object_path,
    require_project_authorization_url,
    require_project_url,
    require_provider,
)

DEFAULT_MAX_ROWS = 1_000
DEFAULT_MAX_OBJECT_BYTES = 10_000_000
DEFAULT_MAX_FUNCTION_BYTES = 1_000_000


class SupabaseClient:
    """Database, Auth, Storage, and Functions without admin/Vault escape hatches."""

    def __init__(
        self,
        url: str,
        key: str,
        *,
        schema: str = "public",
        timeout_seconds: float = 30,
        max_rows: int = DEFAULT_MAX_ROWS,
        max_object_bytes: int = DEFAULT_MAX_OBJECT_BYTES,
        allow_local_http: bool = False,
        persist_session: bool = False,
        auto_refresh_token: bool = False,
        sdk_client: Any = None,
    ) -> None:
        self.url = require_project_url(url, allow_local_http=allow_local_http)
        self.schema = require_identifier(schema, label="schema")
        if not key.strip():
            raise ValueError("A non-empty Supabase project key is required")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not 1 <= max_rows <= 10_000:
            raise ValueError("max_rows must be between 1 and 10000")
        if not 1 <= max_object_bytes <= 100_000_000:
            raise ValueError("max_object_bytes must be between 1 and 100000000")
        self.timeout_seconds = timeout_seconds
        self.max_rows = max_rows
        self.max_object_bytes = max_object_bytes
        if sdk_client is not None:
            self._sdk = sdk_client
        else:
            from supabase import ClientOptions, create_client

            self._sdk = create_client(
                self.url,
                key,
                options=ClientOptions(
                    schema=self.schema,
                    auto_refresh_token=auto_refresh_token,
                    persist_session=persist_session,
                    postgrest_client_timeout=timeout_seconds,
                    storage_client_timeout=int(timeout_seconds),
                    function_client_timeout=int(timeout_seconds),
                ),
            )

    def __repr__(self) -> str:
        return (
            f"SupabaseClient(url={self.url!r}, schema={self.schema!r}, key=<redacted>)"
        )

    def __str__(self) -> str:
        return self.__repr__()

    def _execute(self, query: Any) -> Any:
        try:
            return query.execute()
        except Exception as error:
            raise normalize_supabase_error(error) from None

    def _query(
        self,
        query: Any,
        *,
        filters: Sequence[SupabaseFilter] = (),
        orders: Sequence[SupabaseOrder] = (),
        offset: int = 0,
        limit: int | None = None,
    ) -> Any:
        if offset < 0:
            raise ValueError("offset must not be negative")
        effective_limit = self.max_rows if limit is None else limit
        if not 1 <= effective_limit <= self.max_rows:
            raise ValueError(f"limit must be between 1 and {self.max_rows}")
        for item in filters:
            query = getattr(query, item.operator.value)(item.field, item.value)
        for order in orders:
            query = query.order(
                order.field,
                desc=order.descending,
                nullsfirst=order.nulls_first,
            )
        return query.range(offset, offset + effective_limit - 1)

    @staticmethod
    def _rows(response: Any, *, offset: int, limit: int | None) -> SupabaseRowPage:
        data = getattr(response, "data", response)
        if data is None:
            rows: list[dict[str, Any]] = []
        elif isinstance(data, list) and all(isinstance(row, dict) for row in data):
            rows = data
        elif isinstance(data, dict):
            rows = [data]
        else:
            raise SupabaseAPIError(code="invalid_database_response")
        raw_count = getattr(response, "count", None)
        count = raw_count if isinstance(raw_count, int) else None
        return SupabaseRowPage(rows=rows, count=count, offset=offset, limit=limit)

    def select(
        self,
        table: str,
        *,
        columns: Sequence[str] = ("*",),
        filters: Sequence[SupabaseFilter] = (),
        orders: Sequence[SupabaseOrder] = (),
        offset: int = 0,
        limit: int | None = None,
        count: str | None = None,
    ) -> SupabaseRowPage:
        """Select one bounded page from an RLS-governed table."""
        require_identifier(table, label="table")
        if not columns or any(
            column != "*" and require_identifier(column, label="column") != column
            for column in columns
        ):
            raise ValueError("columns must contain identifiers or '*'")
        if count not in {None, "exact", "planned", "estimated"}:
            raise ValueError("count must be exact, planned, estimated, or None")
        try:
            query = self._sdk.table(table).select(",".join(columns), count=count)
            query = self._query(
                query,
                filters=filters,
                orders=orders,
                offset=offset,
                limit=limit,
            )
            return self._rows(self._execute(query), offset=offset, limit=limit)
        except SupabaseAPIError:
            raise
        except Exception as error:
            raise normalize_supabase_error(error) from None

    def insert(
        self, table: str, rows: Mapping[str, Any] | Sequence[Mapping[str, Any]]
    ) -> SupabaseRowPage:
        require_identifier(table, label="table")
        payload = self._bounded_rows(rows)
        try:
            query = self._sdk.table(table).insert(payload)
            return self._rows(self._execute(query), offset=0, limit=None)
        except SupabaseAPIError:
            raise
        except Exception as error:
            raise normalize_supabase_error(error) from None

    def upsert(
        self,
        table: str,
        rows: Mapping[str, Any] | Sequence[Mapping[str, Any]],
        *,
        on_conflict: str | None = None,
        ignore_duplicates: bool = False,
    ) -> SupabaseRowPage:
        require_identifier(table, label="table")
        if on_conflict is not None:
            require_identifier(on_conflict, label="on_conflict")
        payload = self._bounded_rows(rows)
        try:
            query = self._sdk.table(table).upsert(
                payload,
                on_conflict=on_conflict,
                ignore_duplicates=ignore_duplicates,
            )
            return self._rows(self._execute(query), offset=0, limit=None)
        except SupabaseAPIError:
            raise
        except Exception as error:
            raise normalize_supabase_error(error) from None

    def update(
        self,
        table: str,
        values: Mapping[str, Any],
        *,
        filters: Sequence[SupabaseFilter],
    ) -> SupabaseRowPage:
        require_identifier(table, label="table")
        if not values:
            raise ValueError("update values must not be empty")
        if not filters:
            raise ValueError("update requires at least one filter")
        try:
            query = self._sdk.table(table).update(dict(values))
            query = self._query(query, filters=filters, limit=self.max_rows)
            return self._rows(self._execute(query), offset=0, limit=None)
        except SupabaseAPIError:
            raise
        except Exception as error:
            raise normalize_supabase_error(error) from None

    def delete(
        self, table: str, *, filters: Sequence[SupabaseFilter]
    ) -> SupabaseRowPage:
        require_identifier(table, label="table")
        if not filters:
            raise ValueError("delete requires at least one filter")
        try:
            query = self._sdk.table(table).delete()
            query = self._query(query, filters=filters, limit=self.max_rows)
            return self._rows(self._execute(query), offset=0, limit=None)
        except SupabaseAPIError:
            raise
        except Exception as error:
            raise normalize_supabase_error(error) from None

    def rpc(
        self,
        function: str,
        params: Mapping[str, Any] | None = None,
        *,
        read_only: bool = False,
    ) -> SupabaseRowPage:
        """Call a named Postgres function; arbitrary SQL is never accepted."""
        require_identifier(function, label="RPC function")
        try:
            query = self._sdk.rpc(function, dict(params or {}), get=read_only)
        except Exception as error:
            raise normalize_supabase_error(error) from None
        return self._rows(self._execute(query), offset=0, limit=None)

    def _bounded_rows(
        self, rows: Mapping[str, Any] | Sequence[Mapping[str, Any]]
    ) -> dict[str, Any] | list[dict[str, Any]]:
        if isinstance(rows, Mapping):
            if not rows:
                raise ValueError("row must not be empty")
            return dict(rows)
        payload = [dict(row) for row in rows]
        if (
            not payload
            or len(payload) > self.max_rows
            or any(not row for row in payload)
        ):
            raise ValueError(f"rows must contain between 1 and {self.max_rows} items")
        return payload

    # Auth -----------------------------------------------------------------

    def sign_up(self, *, email: str, password: str) -> SupabaseSessionStatus:
        return self._auth_call("sign_up", {"email": email, "password": password})

    def sign_in_with_password(
        self, *, email: str, password: str
    ) -> SupabaseSessionStatus:
        return self._auth_call(
            "sign_in_with_password", {"email": email, "password": password}
        )

    def sign_in_with_otp(
        self, *, email: str, redirect_to: str | None = None
    ) -> SupabaseSessionStatus:
        payload: dict[str, Any] = {"email": email}
        if redirect_to is not None:
            payload["options"] = {"email_redirect_to": redirect_to}
        return self._auth_call("sign_in_with_otp", payload)

    def begin_oauth(
        self,
        provider: str,
        *,
        redirect_to: str | None = None,
        scopes: str | None = None,
    ) -> SupabaseOAuthStart:
        require_provider(provider)
        options = {
            key: value
            for key, value in {"redirect_to": redirect_to, "scopes": scopes}.items()
            if value is not None
        }
        try:
            response = self._sdk.auth.sign_in_with_oauth(
                {"provider": provider, "options": options}
            )
            url = getattr(response, "url", None)
            if not isinstance(url, str):
                raise SupabaseAPIError(code="invalid_oauth_response")
            require_project_authorization_url(url, project_url=self.url)
            return SupabaseOAuthStart(provider=provider, authorization_url=url)
        except SupabaseAPIError:
            raise
        except Exception as error:
            raise normalize_supabase_error(error) from None

    def get_user(self, access_token: str | None = None) -> SupabaseSessionStatus:
        try:
            response = self._sdk.auth.get_user(access_token)
        except Exception as error:
            raise normalize_supabase_error(error) from None
        return _session_status(response)

    def refresh_session(
        self, refresh_token: str | None = None
    ) -> SupabaseSessionStatus:
        try:
            response = self._sdk.auth.refresh_session(refresh_token)
        except Exception as error:
            raise normalize_supabase_error(error) from None
        return _session_status(response)

    def sign_out(self, *, scope: str = "local") -> None:
        if scope not in {"local", "global", "others"}:
            raise ValueError("scope must be local, global, or others")
        try:
            self._sdk.auth.sign_out({"scope": scope})
        except Exception as error:
            raise normalize_supabase_error(error) from None

    def reset_password_email(
        self, email: str, *, redirect_to: str | None = None
    ) -> None:
        options = {"redirect_to": redirect_to} if redirect_to else None
        try:
            self._sdk.auth.reset_password_email(email, options)
        except Exception as error:
            raise normalize_supabase_error(error) from None

    def _auth_call(
        self, method: str, credentials: dict[str, Any]
    ) -> SupabaseSessionStatus:
        try:
            response = getattr(self._sdk.auth, method)(credentials)
        except Exception as error:
            raise normalize_supabase_error(error) from None
        return _session_status(response)

    # Storage --------------------------------------------------------------

    def list_buckets(self) -> list[SupabaseBucket]:
        try:
            return [_bucket(item) for item in self._sdk.storage.list_buckets()]
        except Exception as error:
            raise normalize_supabase_error(error) from None

    def create_bucket(
        self,
        bucket: str,
        *,
        public: bool = False,
        file_size_limit: int | None = None,
        allowed_mime_types: Sequence[str] = (),
    ) -> None:
        require_identifier(bucket, label="bucket")
        if (
            file_size_limit is not None
            and not 1 <= file_size_limit <= self.max_object_bytes
        ):
            raise ValueError("file_size_limit exceeds the configured object bound")
        options = {
            "public": public,
            "file_size_limit": file_size_limit,
            "allowed_mime_types": list(allowed_mime_types),
        }
        try:
            self._sdk.storage.create_bucket(bucket, options=options)
        except Exception as error:
            raise normalize_supabase_error(error) from None

    def delete_bucket(self, bucket: str, *, empty_first: bool = False) -> None:
        require_identifier(bucket, label="bucket")
        try:
            if empty_first:
                self._sdk.storage.empty_bucket(bucket)
            self._sdk.storage.delete_bucket(bucket)
        except Exception as error:
            raise normalize_supabase_error(error) from None

    def upload_bytes(
        self,
        bucket: str,
        path: str,
        content: bytes,
        *,
        content_type: str = "application/octet-stream",
        upsert: bool = False,
    ) -> None:
        require_identifier(bucket, label="bucket")
        require_object_path(path)
        if len(content) > self.max_object_bytes:
            raise ValueError("object exceeds the configured size bound")
        try:
            self._sdk.storage.from_(bucket).upload(
                path,
                content,
                {"content-type": content_type, "upsert": str(upsert).lower()},
            )
        except Exception as error:
            raise normalize_supabase_error(error) from None

    def upload_file(
        self,
        bucket: str,
        path: str,
        local_path: str | Path,
        *,
        content_type: str = "application/octet-stream",
        upsert: bool = False,
    ) -> None:
        source = Path(local_path)
        if source.stat().st_size > self.max_object_bytes:
            raise ValueError("object exceeds the configured size bound")
        self.upload_bytes(
            bucket,
            path,
            source.read_bytes(),
            content_type=content_type,
            upsert=upsert,
        )

    def download_bytes(self, bucket: str, path: str) -> bytes:
        require_identifier(bucket, label="bucket")
        require_object_path(path)
        try:
            data = self._sdk.storage.from_(bucket).download(path)
        except Exception as error:
            raise normalize_supabase_error(error) from None
        if not isinstance(data, bytes):
            raise SupabaseAPIError(code="invalid_storage_response")
        if len(data) > self.max_object_bytes:
            raise SupabaseAPIError(code="storage_response_too_large")
        return data

    def list_objects(
        self,
        bucket: str,
        *,
        prefix: str | None = None,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        require_identifier(bucket, label="bucket")
        if prefix is not None:
            require_object_path(prefix)
        if not 1 <= limit <= min(self.max_rows, 1_000) or offset < 0:
            raise ValueError("invalid Storage list range")
        options: dict[str, Any] = {"limit": limit, "offset": offset}
        if search is not None:
            options["search"] = search
        try:
            data = self._sdk.storage.from_(bucket).list(prefix, options)
        except Exception as error:
            raise normalize_supabase_error(error) from None
        if not isinstance(data, list) or not all(
            isinstance(item, dict) for item in data
        ):
            raise SupabaseAPIError(code="invalid_storage_response")
        return data

    def move_object(self, bucket: str, source: str, destination: str) -> None:
        self._storage_binary("move", bucket, source, destination)

    def copy_object(self, bucket: str, source: str, destination: str) -> None:
        self._storage_binary("copy", bucket, source, destination)

    def remove_objects(self, bucket: str, paths: Sequence[str]) -> None:
        require_identifier(bucket, label="bucket")
        if not paths or len(paths) > self.max_rows:
            raise ValueError("paths must be a bounded non-empty sequence")
        checked = [require_object_path(path) for path in paths]
        try:
            self._sdk.storage.from_(bucket).remove(checked)
        except Exception as error:
            raise normalize_supabase_error(error) from None

    def _storage_binary(
        self, method: str, bucket: str, source: str, destination: str
    ) -> None:
        require_identifier(bucket, label="bucket")
        require_object_path(source)
        require_object_path(destination)
        try:
            getattr(self._sdk.storage.from_(bucket), method)(source, destination)
        except Exception as error:
            raise normalize_supabase_error(error) from None

    # Edge Functions -------------------------------------------------------

    def invoke_function(
        self,
        function: str,
        *,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> SupabaseFunctionResult:
        require_function_name(function)
        safe_headers = dict(headers or {})
        if any(
            name.lower() in {"authorization", "apikey", "cookie"}
            for name in safe_headers
        ):
            raise ValueError("caller-controlled credential headers are forbidden")
        options: dict[str, Any] = {"body": body, "headers": safe_headers}
        if timeout_seconds is not None:
            if timeout_seconds <= 0 or timeout_seconds > self.timeout_seconds:
                raise ValueError("function timeout exceeds the configured bound")
            options["timeout"] = timeout_seconds
        try:
            response = self._sdk.functions.invoke(function, invoke_options=options)
        except Exception as error:
            raise normalize_supabase_error(error) from None
        status = getattr(response, "status_code", 200)
        data = _function_data(response)
        encoded = json.dumps(data, default=str).encode("utf-8")
        if len(encoded) > DEFAULT_MAX_FUNCTION_BYTES:
            raise SupabaseAPIError(code="function_response_too_large")
        return SupabaseFunctionResult(
            status_code=status if isinstance(status, int) else 200,
            data=data,
        )


def _model_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        data = value.model_dump()
        return data if isinstance(data, dict) else {}
    if hasattr(value, "dict"):
        data = value.dict()
        return data if isinstance(data, dict) else {}
    return {}


def _safe_user(value: Any) -> SupabaseUser | None:
    if value is None:
        return None
    data = _model_dict(value)
    user_id = data.get("id", getattr(value, "id", None))
    if not isinstance(user_id, str):
        return None
    return SupabaseUser(
        id=user_id,
        email=data.get("email", getattr(value, "email", None)),
        phone=data.get("phone", getattr(value, "phone", None)),
        app_metadata=data.get("app_metadata") or {},
        user_metadata=data.get("user_metadata") or {},
        created_at=data.get("created_at", getattr(value, "created_at", None)),
    )


def _session_status(response: Any) -> SupabaseSessionStatus:
    user = getattr(response, "user", None)
    if user is None and response is not None:
        user = _model_dict(response).get("user")
    session = getattr(response, "session", None)
    session_data = _model_dict(session)
    expires_at = session_data.get("expires_at", getattr(session, "expires_at", None))
    safe_user = _safe_user(user)
    return SupabaseSessionStatus(
        authenticated=safe_user is not None,
        user=safe_user,
        expires_at=expires_at if isinstance(expires_at, int) else None,
    )


def _bucket(value: Any) -> SupabaseBucket:
    data = _model_dict(value)
    bucket_id = data.get("id", getattr(value, "id", None))
    name = data.get("name", getattr(value, "name", bucket_id))
    if not isinstance(bucket_id, str) or not isinstance(name, str):
        raise SupabaseAPIError(code="invalid_bucket_response")
    mime_types = data.get("allowed_mime_types") or []
    return SupabaseBucket(
        id=bucket_id,
        name=name,
        public=bool(data.get("public", False)),
        file_size_limit=data.get("file_size_limit"),
        allowed_mime_types=mime_types if isinstance(mime_types, list) else [],
    )


def _function_data(response: Any) -> Any:
    if isinstance(response, (dict, list, str, int, float, bool)) or response is None:
        return response
    json_method = getattr(response, "json", None)
    if callable(json_method):
        try:
            return json_method()
        except Exception:
            return None
    content = getattr(response, "content", None)
    if isinstance(content, bytes) and len(content) <= DEFAULT_MAX_FUNCTION_BYTES:
        try:
            return json.loads(content)
        except json.JSONDecodeError, UnicodeDecodeError:
            return content.decode("utf-8", errors="replace")
    return None
