"""Supported integration inventory and credential inputs for managed execution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrationSetup:
    guide: str
    variables: tuple[str, ...] = ()
    prefixes: tuple[str, ...] = ()
    entry_point: bool = True


_GOOGLE = IntegrationSetup("google.md")
_LOCAL_PREFIXES = {
    "pandoc": "ZEO_PANDOC_",
    "ffmpeg": "ZEO_FFMPEG_",
    "jupytext": "ZEO_JUPYTEXT_",
}
CATALOG: dict[str, IntegrationSetup] = {
    "github": IntegrationSetup("github.md", ("GITHUB_TOKEN",)),
    **{
        f"google.{name}": _GOOGLE
        for name in ("mail", "drive", "calendar", "docs", "sheets", "slides")
    },
    "notion": IntegrationSetup("notion.md", ("NOTION_TOKEN",)),
    "supabase": IntegrationSetup(
        "supabase.md",
        (
            "SUPABASE_URL",
            "SUPABASE_PUBLISHABLE_KEY",
            "SUPABASE_KEY",
            "SUPABASE_SECRET_KEY",
        ),
    ),
    "hubspot.marketing": IntegrationSetup("hubspot.md", ("HUBSPOT_ACCESS_TOKEN",)),
    "kit.marketing": IntegrationSetup("kit.md", ("KIT_API_KEY", "KIT_ACCESS_TOKEN")),
    "social.bluesky": IntegrationSetup(
        "bluesky.md",
        ("BLUESKY_IDENTIFIER", "BLUESKY_APP_PASSWORD", "BLUESKY_SERVICE_URL"),
    ),
    "llms": IntegrationSetup(
        "llms.md", ("OPENAI_API_KEY", "OPENAI_ORG_ID", "ANTHROPIC_API_KEY")
    ),
    **{
        name: IntegrationSetup("local-tools.md", prefixes=(prefix,))
        for name, prefix in _LOCAL_PREFIXES.items()
    },
    "zeoconnect": IntegrationSetup("zeoconnect.md", entry_point=False),
}
