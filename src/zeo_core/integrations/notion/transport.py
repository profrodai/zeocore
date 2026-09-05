"""Explicit HTTP construction for Notion SDK clients."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx


def build_notion_http_client(*, trust_env: bool = False) -> httpx.Client:
    """Build a transport with deliberate ambient-proxy behavior.

    Direct transport is deterministic by default. A caller may opt into a
    deliberately provisioned and tested ambient proxy with ``trust_env=True``.
    """

    import httpx

    return httpx.Client(trust_env=trust_env)
