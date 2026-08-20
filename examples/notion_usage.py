"""
Example: reading and writing Notion content with zeo_core.integrations.notion.

Requires the 'notion' extra:

    pip install "zeocore[notion]"

Auth is a single bearer "integration token" (Notion's own model -- create
one at https://www.notion.so/my-integrations, then share the specific
page/database you want it to touch with that integration). Set it via the
NOTION_TOKEN environment variable.

IMPORTANT, verified against the real source (not assumed from the token
alone): NotionIntegration.initialize() loads its configuration through
zeo_core.config's default-locations lookup, and that lookup RAISES if no
config file exists at any default location (./zeo_config.yaml,
./config/zeo_config.yaml, ~/.zeo/config.yaml, /etc/zeo/config.yaml) --
NOTION_TOKEN alone, with zero config file anywhere, is NOT enough to
initialize (unlike the jupytext integration, which falls back to defaults
cleanly with no config file at all). A minimal config file with an empty
`integrations: {notion: {}}` block is sufficient; NOTION_TOKEN then fills
in the token value via NotionConfigProvider's own env-var fallback. This
example writes exactly that minimal file into a scratch directory so it
runs end to end without requiring you to hand-author one first.

This example demonstrates the graceful-skip path (matching
examples/toolkit_usage.py's own pattern) when NOTION_TOKEN isn't set: it
still shows integration construction and the real calling shapes, just
without making a live API call. Set NOTION_TOKEN and point it at a
workspace with at least one shared page to see the live path run.

Run this file directly:

    python examples/notion_usage.py
    NOTION_TOKEN=secret_xxx python examples/notion_usage.py
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from zeo_core.integrations.notion import NotionIntegration


def main() -> None:
    """
    Initialize the Notion integration and, if a real token is available,
    run one real read call (search) and one real write call (create a
    page under the first search result, if any) end to end.

    NOTION_TOKEN is checked BEFORE calling initialize(): the integration's
    own initialize() requires a resolvable token to succeed at all (there
    is no "initialize now, authenticate later" path), so a missing token
    is treated here as a graceful-skip precondition, not a failure to
    report from a failed initialize() call.
    """
    token = os.environ.get("NOTION_TOKEN")

    if not token:
        print(
            "NOTION_TOKEN is not set -- skipping live initialization and "
            "API calls (graceful skip, not an error). Set NOTION_TOKEN to "
            "a real integration token (from "
            "https://www.notion.so/my-integrations), shared with at least "
            "one page, to see the live read/write calls run."
        )
        print("\nThe calling shapes, unchanged whether live or skipped:")
        print('  notion.search(query="Project")')
        print('  notion.get_page(page_id="...")')
        print('  notion.get_database(database_id="...")')
        print(
            '  notion.query_database(database_id="...", '
            'filter={"property": "Status", "select": {"equals": "Done"}})'
        )
        print(
            '  notion.create_page(parent={"type": "page_id", "page_id": "..."}, '
            'properties={"title": [{"text": {"content": "New page"}}]})'
        )
        return

    scratch_dir = Path("./tmp_notion_example")
    scratch_dir.mkdir(exist_ok=True)
    config_path = scratch_dir / "zeo_config.yaml"
    # NotionConfigProvider needs SOME config file to exist (see module
    # docstring above) -- an empty notion block is enough; NOTION_TOKEN
    # fills in the token value itself via the provider's own env-var
    # fallback.
    config_path.write_text("integrations:\n  notion: {}\n")

    try:
        # config_path is a constructor arg, not an initialize() arg --
        # create_integration() (the entry-point factory) takes no args at
        # all, so a caller who needs an explicit config path constructs
        # NotionIntegration directly instead.
        notion = NotionIntegration(config_path=str(config_path))
        init_result = notion.initialize()
        if not init_result.success:
            print(f"Failed to initialize Notion integration: {init_result.error}")
            return
        print(f"Notion integration initialized: {init_result.message}")

        # Real read: search the workspace for pages/databases the
        # integration has been shared with.
        search_result = notion.search(query="")
        if not search_result.success:
            print(f"search failed: {search_result.error}")
            return

        results = search_result.content or []
        print(f"search() found {len(results)} shared object(s)")

        page_results = [r for r in results if r.get("object") == "page"]
        if not page_results:
            print(
                "No pages shared with this integration yet -- share a page "
                "with your integration in Notion's UI to see the write "
                "path run too."
            )
            return

        parent_page_id = page_results[0]["id"]

        # Real write: create a child page under the first page found.
        create_result = notion.create_page(
            parent={"type": "page_id", "page_id": parent_page_id},
            properties={
                "title": [{"text": {"content": "zeocore notion_usage.py demo"}}]
            },
        )
        if not create_result.success:
            print(f"create_page failed: {create_result.error}")
            return

        new_page = create_result.content
        assert new_page is not None  # noqa: S101 -- success==True guarantees content
        print(f"Created page: {new_page.id}")

        # Append a paragraph block to the page we just created.
        append_result = notion.append_blocks(
            new_page.id,
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Created by zeocore's "
                                    "notion_usage.py example."
                                },
                            }
                        ]
                    },
                }
            ],
        )
        if append_result.success:
            print("Appended a paragraph block to the new page.")
        else:
            print(f"append_blocks failed: {append_result.error}")
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
