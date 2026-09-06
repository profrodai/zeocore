"""Async Realtime lifecycle tests."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from zeo_core.integrations.database.supabase import (
    SupabaseRealtimeChange,
    SupabaseRealtimeClient,
    SupabaseRealtimeEvent,
    SupabaseRealtimeProtocol,
)


def test_subscribe_delivers_typed_change_and_unsubscribes() -> None:
    asyncio.run(_subscribe_delivers_typed_change_and_unsubscribes())


async def _subscribe_delivers_typed_change_and_unsubscribes() -> None:
    sdk = MagicMock()
    sdk.remove_channel = AsyncMock()
    channel = MagicMock()
    channel.subscribe = AsyncMock(return_value=channel)
    channel.unsubscribe = AsyncMock()
    channel.on_postgres_changes.return_value = channel
    sdk.channel.return_value = channel
    received: list[SupabaseRealtimeChange] = []
    client = SupabaseRealtimeClient(
        "https://example.supabase.co", "sb_publishable_test", sdk_client=sdk
    )

    subscription = await client.subscribe_table(
        "events", received.append, event=SupabaseRealtimeEvent.INSERT
    )
    callback = channel.on_postgres_changes.call_args.args[1]
    callback(
        {
            "data": {
                "type": "INSERT",
                "schema": "public",
                "table": "events",
                "record": {"id": 1},
                "old_record": {},
            }
        }
    )

    assert received[0].event == "INSERT"
    assert received[0].new == {"id": 1}
    await client.unsubscribe(subscription.id)
    channel.unsubscribe.assert_awaited_once()
    sdk.remove_channel.assert_awaited_once_with(channel)


def test_close_is_explicit_and_idempotent() -> None:
    asyncio.run(_close_is_explicit_and_idempotent())


async def _close_is_explicit_and_idempotent() -> None:
    sdk = MagicMock()
    sdk.remove_all_channels = AsyncMock()
    sdk.close = AsyncMock()
    client = SupabaseRealtimeClient(
        "https://example.supabase.co", "sb_publishable_test", sdk_client=sdk
    )
    assert isinstance(client, SupabaseRealtimeProtocol)
    await client.close()
    await client.close()
    sdk.remove_all_channels.assert_awaited_once()
    sdk.close.assert_awaited_once()


def test_unknown_subscription_refuses() -> None:
    asyncio.run(_unknown_subscription_refuses())


async def _unknown_subscription_refuses() -> None:
    client = SupabaseRealtimeClient(
        "https://example.supabase.co", "sb_publishable_test", sdk_client=MagicMock()
    )
    with pytest.raises(KeyError, match="Unknown"):
        await client.unsubscribe("missing")


def test_realtime_repr_redacts_key() -> None:
    client = SupabaseRealtimeClient(
        "https://example.supabase.co", "sb_publishable_CANARY", sdk_client=MagicMock()
    )
    assert "CANARY" not in repr(client)


def test_lazy_realtime_key_is_opaque_and_released_after_construction() -> None:
    asyncio.run(_lazy_realtime_key_is_opaque_and_released_after_construction())


async def _lazy_realtime_key_is_opaque_and_released_after_construction() -> None:
    canary = "sb_publishable_REALTIME_CANARY"
    sdk = MagicMock()
    factory = AsyncMock(return_value=sdk)
    client = SupabaseRealtimeClient(
        "https://example.supabase.co", canary, sdk_client_factory=factory
    )

    assert canary not in repr(client)
    assert canary not in str(vars(client))
    await client._client()

    factory.assert_awaited_once_with("https://example.supabase.co", canary)
    assert client._key is None
