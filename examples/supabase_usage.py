"""Credential-safe, read-only Supabase integration smoke example."""

from __future__ import annotations

import os

from zeo_core.config import load_dotenv_file
from zeo_core.integrations.database.supabase import SupabaseIntegration


def main() -> int:
    """Initialize and perform an opt-in bounded table read."""
    load_dotenv_file()
    if not os.environ.get("SUPABASE_URL") or not (
        os.environ.get("SUPABASE_PUBLISHABLE_KEY") or os.environ.get("SUPABASE_KEY")
    ):
        print("Supabase not configured; set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY")
        return 0

    table = os.environ.get("SUPABASE_DEMO_TABLE")
    if not table:
        print("Supabase configured; set SUPABASE_DEMO_TABLE to opt into a read")
        return 0

    supabase = SupabaseIntegration()
    initialized = supabase.initialize()
    if not initialized.success:
        print(f"Initialization refused safely: {initialized.error}")
        return 1
    result = supabase.select(table, limit=5)
    if not result.success:
        print(f"Read refused safely: {result.error}")
        return 1
    print(f"Read {len(result.content.rows if result.content else [])} row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
