"""Runtime-checkable Supabase service protocols."""

# ruff: noqa: ANN401, A002 -- JSON payloads and upstream Realtime parameter.

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from zeo_core.integrations.core import IntegrationProtocol, IntegrationResult

from .models import (
    SupabaseBucket,
    SupabaseFilter,
    SupabaseFunctionResult,
    SupabaseOAuthStart,
    SupabaseOrder,
    SupabaseRealtimeChange,
    SupabaseRealtimeEvent,
    SupabaseRealtimeSubscription,
    SupabaseRowPage,
    SupabaseSessionStatus,
)


@runtime_checkable
class SupabaseDatabaseProtocol(Protocol):
    """Bounded PostgREST database operations."""

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
    ) -> IntegrationResult[SupabaseRowPage]: ...

    def insert(
        self, table: str, rows: Mapping[str, Any] | Sequence[Mapping[str, Any]]
    ) -> IntegrationResult[SupabaseRowPage]: ...

    def upsert(
        self,
        table: str,
        rows: Mapping[str, Any] | Sequence[Mapping[str, Any]],
        *,
        on_conflict: str | None = None,
        ignore_duplicates: bool = False,
    ) -> IntegrationResult[SupabaseRowPage]: ...

    def update(
        self,
        table: str,
        values: Mapping[str, Any],
        *,
        filters: Sequence[SupabaseFilter],
    ) -> IntegrationResult[SupabaseRowPage]: ...

    def delete(
        self, table: str, *, filters: Sequence[SupabaseFilter]
    ) -> IntegrationResult[SupabaseRowPage]: ...

    def rpc(
        self,
        function: str,
        params: Mapping[str, Any] | None = None,
        *,
        read_only: bool = False,
    ) -> IntegrationResult[SupabaseRowPage]: ...


@runtime_checkable
class SupabaseUserAuthProtocol(Protocol):
    """End-user Auth operations with secret-free results."""

    def sign_up(
        self, *, email: str, password: str
    ) -> IntegrationResult[SupabaseSessionStatus]: ...

    def sign_in_with_password(
        self, *, email: str, password: str
    ) -> IntegrationResult[SupabaseSessionStatus]: ...

    def sign_in_with_otp(
        self, *, email: str, redirect_to: str | None = None
    ) -> IntegrationResult[SupabaseSessionStatus]: ...

    def begin_oauth(
        self,
        provider: str,
        *,
        redirect_to: str | None = None,
        scopes: str | None = None,
    ) -> IntegrationResult[SupabaseOAuthStart]: ...

    def get_user(
        self, access_token: str | None = None
    ) -> IntegrationResult[SupabaseSessionStatus]: ...

    def refresh_session(
        self, refresh_token: str | None = None
    ) -> IntegrationResult[SupabaseSessionStatus]: ...

    def sign_out(self, *, scope: str = "local") -> IntegrationResult[None]: ...

    def reset_password_email(
        self, email: str, *, redirect_to: str | None = None
    ) -> IntegrationResult[None]: ...


@runtime_checkable
class SupabaseStorageProtocol(Protocol):
    """Bounded Storage bucket and object operations."""

    def list_buckets(self) -> IntegrationResult[list[SupabaseBucket]]: ...

    def create_bucket(
        self,
        bucket: str,
        *,
        public: bool = False,
        file_size_limit: int | None = None,
        allowed_mime_types: Sequence[str] = (),
    ) -> IntegrationResult[None]: ...

    def delete_bucket(
        self, bucket: str, *, empty_first: bool = False
    ) -> IntegrationResult[None]: ...

    def upload_bytes(
        self,
        bucket: str,
        path: str,
        content: bytes,
        *,
        content_type: str = "application/octet-stream",
        upsert: bool = False,
    ) -> IntegrationResult[None]: ...

    def upload_file(
        self,
        bucket: str,
        path: str,
        local_path: str | Path,
        *,
        content_type: str = "application/octet-stream",
        upsert: bool = False,
    ) -> IntegrationResult[None]: ...

    def download_bytes(self, bucket: str, path: str) -> IntegrationResult[bytes]: ...

    def list_objects(
        self,
        bucket: str,
        *,
        prefix: str | None = None,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
    ) -> IntegrationResult[list[dict[str, Any]]]: ...

    def move_object(
        self, bucket: str, source: str, destination: str
    ) -> IntegrationResult[None]: ...

    def copy_object(
        self, bucket: str, source: str, destination: str
    ) -> IntegrationResult[None]: ...

    def remove_objects(
        self, bucket: str, paths: Sequence[str]
    ) -> IntegrationResult[None]: ...


@runtime_checkable
class SupabaseFunctionsProtocol(Protocol):
    """Named, bounded Edge Function invocation."""

    def invoke_function(
        self,
        function: str,
        *,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> IntegrationResult[SupabaseFunctionResult]: ...


@runtime_checkable
class SupabaseRealtimeProtocol(Protocol):
    """Explicit async Realtime lifecycle."""

    async def subscribe_table(
        self,
        table: str,
        callback: Callable[[SupabaseRealtimeChange], None],
        *,
        event: SupabaseRealtimeEvent = SupabaseRealtimeEvent.ALL,
        schema: str = "public",
        filter: str | None = None,
    ) -> SupabaseRealtimeSubscription: ...

    async def unsubscribe(self, subscription_id: str) -> None: ...

    async def close(self) -> None: ...


@runtime_checkable
class SupabaseIntegrationProtocol(
    IntegrationProtocol,
    SupabaseDatabaseProtocol,
    SupabaseUserAuthProtocol,
    SupabaseStorageProtocol,
    SupabaseFunctionsProtocol,
    Protocol,
):
    """Complete synchronous application surface for Supabase."""

    @property
    def realtime(self) -> SupabaseRealtimeProtocol: ...
