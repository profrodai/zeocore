"""Compatibility entrypoint for the safe Notion demo.

The historical example name remains linkable. It now delegates to
``notion_demo`` whose default is credential-free and non-mutating.
"""

from notion_demo import main  # type: ignore[import-not-found]

if __name__ == "__main__":
    raise SystemExit(main())
