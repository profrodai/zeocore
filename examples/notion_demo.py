"""Safe Notion API 2026-03-11 demo.

Simulated mode is the default and uses no credentials or network. Live mode
is read-only and must be requested explicitly.
"""

from __future__ import annotations

import argparse
import os
from types import SimpleNamespace
from typing import Any

from zeo_core.integrations.notion import NotionClient, NotionOperation


class SimulatedSDK(SimpleNamespace):
    """Tiny SDK-shaped recorder used to teach the transport boundary."""

    calls: list[tuple[str, dict[str, Any]]]

    def __init__(self) -> None:
        self.calls = []
        self.users = SimpleNamespace(list=self._endpoint("users.list"))
        self.search = self._endpoint("search")
        self.data_sources = SimpleNamespace(query=self._endpoint("data_sources.query"))
        self.blocks = SimpleNamespace(
            children=SimpleNamespace(list=self._endpoint("blocks.children.list"))
        )
        self.comments = SimpleNamespace(list=self._endpoint("comments.list"))

    def _endpoint(self, name: str) -> Any:  # noqa: ANN401
        def call(**kwargs: Any) -> dict[str, Any]:  # noqa: ANN401
            self.calls.append((name, kwargs))
            return {
                "object": "list",
                "results": [{"object": name, "id": f"sim-{len(self.calls)}"}],
                "has_more": False,
                "next_cursor": None,
            }

        return call


def simulated() -> int:
    sdk = SimulatedSDK()
    client = NotionClient("simulation-only", sdk_client=sdk)
    requests: list[tuple[NotionOperation, dict[str, Any]]] = [
        (NotionOperation.USER_LIST, {}),
        (NotionOperation.SEARCH, {"query": "Course"}),
        (NotionOperation.DATA_SOURCE_QUERY, {"data_source_id": "ds-course"}),
        (NotionOperation.BLOCK_LIST_CHILDREN, {"block_id": "page-course"}),
        (NotionOperation.COMMENT_LIST, {"block_id": "page-course"}),
    ]
    print("Notion API", client.__repr__())
    for operation, kwargs in requests:
        page = client.paged(operation, **kwargs)
        print(f"{operation}: {len(page.items)} item, has_more={page.has_more}")
    print(f"SIMULATED: {len(sdk.calls)} current API calls, no network or credential")
    return 0


def live_read() -> int:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise SystemExit(
            "Set NOTION_TOKEN in .env, then use: uv run --env-file .env ..."
        )
    client = NotionClient(token)
    page = client.paged(NotionOperation.SEARCH, page_size=10)
    print(f"Authenticated read succeeded: {len(page.items)} shared objects")
    for item in page.items:
        print(item.get("object"), item.get("id"))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulated", action="store_true")
    parser.add_argument("--live-read", action="store_true")
    args = parser.parse_args()
    if args.live_read:
        return live_read()
    return simulated()


if __name__ == "__main__":
    raise SystemExit(main())
