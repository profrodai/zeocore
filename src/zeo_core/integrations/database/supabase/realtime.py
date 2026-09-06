"""Explicit async Realtime facade for Supabase Postgres changes."""

# ruff: noqa: ANN401 -- SDK construction is an injectable third-party boundary.

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

from pydantic import SecretStr

from .errors import normalize_supabase_error
from .models import (
    SupabaseRealtimeChange,
    SupabaseRealtimeEvent,
    SupabaseRealtimeSubscription,
)
from .validation import require_identifier, require_project_url


class SupabaseRealtimeClient:
    """Manage async channels; no hidden event loop or background retry policy."""

    def __init__(
        self,
        url: str,
        key: str,
        *,
        allow_local_http: bool = False,
        sdk_client: Any = None,
        sdk_client_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.url = require_project_url(url, allow_local_http=allow_local_http)
        if not key.strip():
            raise ValueError("A non-empty Supabase project key is required")
        self._key: SecretStr | None = SecretStr(key)
        self._sdk = sdk_client
        self._factory = sdk_client_factory
        self._channels: dict[str, Any] = {}

    def __repr__(self) -> str:
        return f"SupabaseRealtimeClient(url={self.url!r}, key=<redacted>)"

    async def _client(self) -> Any:
        if self._sdk is None:
            if self._key is None:
                raise RuntimeError("Supabase Realtime client key is unavailable")
            key = self._key.get_secret_value()
            if self._factory is not None:
                self._sdk = await self._factory(self.url, key)
            else:
                from supabase import acreate_client

                self._sdk = await acreate_client(self.url, key)
            self._key = None
        return self._sdk

    async def subscribe_table(
        self,
        table: str,
        callback: Callable[[SupabaseRealtimeChange], None],
        *,
        event: SupabaseRealtimeEvent = SupabaseRealtimeEvent.ALL,
        schema: str = "public",
        filter: str | None = None,  # noqa: A002 -- upstream Realtime parameter
    ) -> SupabaseRealtimeSubscription:
        require_identifier(table, label="table")
        require_identifier(schema, label="schema")
        if filter is not None and any(char in filter for char in "\r\n\x00"):
            raise ValueError("Realtime filter contains a control character")
        topic = f"zeocore:{schema}:{table}:{uuid4().hex}"

        def receive(payload: dict[str, Any]) -> None:
            callback(_change(payload))

        try:
            client = await self._client()
            channel = client.channel(topic)
            channel.on_postgres_changes(
                event.value,
                receive,
                table=table,
                schema=schema,
                filter=filter,
            )
            await channel.subscribe()
        except Exception as error:
            raise normalize_supabase_error(error) from None
        subscription_id = uuid4().hex
        self._channels[subscription_id] = channel
        return SupabaseRealtimeSubscription(
            id=subscription_id,
            topic=topic,
            schema_name=schema,
            table=table,
            event=event,
        )

    async def unsubscribe(self, subscription_id: str) -> None:
        channel = self._channels.pop(subscription_id, None)
        if channel is None:
            raise KeyError("Unknown Realtime subscription")
        try:
            await channel.unsubscribe()
            if self._sdk is not None:
                await self._sdk.remove_channel(channel)
        except Exception as error:
            raise normalize_supabase_error(error) from None

    async def close(self) -> None:
        try:
            for channel in tuple(self._channels.values()):
                await channel.unsubscribe()
            self._channels.clear()
            if self._sdk is not None:
                await self._sdk.remove_all_channels()
                await self._sdk.close()
                self._sdk = None
        except Exception as error:
            raise normalize_supabase_error(error) from None


def _change(payload: dict[str, Any]) -> SupabaseRealtimeChange:
    nested = payload.get("data")
    data: dict[str, Any] = nested if isinstance(nested, dict) else payload
    return SupabaseRealtimeChange(
        event=str(data.get("type") or data.get("eventType") or "UNKNOWN"),
        schema_name=data.get("schema"),
        table=data.get("table"),
        committed_at=data.get("commit_timestamp"),
        new=data.get("record") if isinstance(data.get("record"), dict) else {},
        old=data.get("old_record") if isinstance(data.get("old_record"), dict) else {},
    )
