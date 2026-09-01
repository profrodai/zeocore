"""
Example: zeo_core.config's load_config() end to end.

GET-STARTED.md's "Basic Configuration Setup" quick-start shows
load_config() being called two ways in the same snippet: once with no
argument (default-locations lookup) and once with an explicit path
("path/to/custom_config.yaml"). That second call is illustrative only --
copy-pasting the whole snippet verbatim raises ZeoConfigurationError
because the placeholder path doesn't exist. This example runs both real
code paths end to end, from a fresh directory, with no manual setup:

1. load_config() with no config file anywhere -- does NOT raise. It
   falls back to built-in defaults (merge_defaults=True) plus whatever
   environment variables are set (merge_env=True). This is the actual
   behavior of the bare `load_config()` call GET-STARTED.md leads with.
2. load_config(path) with an explicit path that does not exist -- this
   DOES raise ZeoConfigurationError, by design (an explicit path is a
   promise the file is there). Shown here as a deliberately caught
   example, not as something to copy verbatim.
3. load_config(path) with an explicit path to a real YAML file this
   script writes first -- the actually-correct way to exercise the
   "load from a specific file" path GET-STARTED.md's snippet gestures at
   without showing how to get there.

Run this file directly:

    uv run examples/config_usage.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from zeo_core.config import load_config
from zeo_core.core.errors import ZeoConfigurationError


def load_with_no_config_file(empty_dir: Path) -> None:
    """load_config() in a directory with no config file: does NOT raise."""
    import os

    cwd = Path.cwd()
    try:
        os.chdir(empty_dir)
        config = load_config()
        print("1. load_config() with no config file present:")
        print(f"   project_name = {config.general.project_name!r} (built-in default)")
        print(f"   log_level    = {config.logging.level!r} (built-in default)")
    finally:
        os.chdir(cwd)


def load_with_missing_explicit_path() -> None:
    """load_config(path) with a path that doesn't exist: DOES raise, by design."""
    print("\n2. load_config('path/to/custom_config.yaml') -- path does not exist:")
    try:
        load_config("path/to/custom_config.yaml")
        print("   unexpectedly succeeded")
    except ZeoConfigurationError as e:
        print(f"   ZeoConfigurationError (expected): {e}")


def load_with_real_file(tmp_dir: Path) -> None:
    """load_config(path) with a real file this script wrote: succeeds."""
    config_path = tmp_dir / "zeo_config.yaml"
    config_path.write_text(
        'general:\n  project_name: "example-app"\nlogging:\n  level: "DEBUG"\n',
        encoding="utf-8",
    )

    config = load_config(str(config_path))
    print("\n3. load_config(path) with a real file:")
    print(f"   project_name = {config.general.project_name!r} (from YAML)")
    print(f"   log_level    = {config.logging.level!r} (from YAML)")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="zeo_config_usage_") as tmp:
        tmp_dir = Path(tmp)
        load_with_no_config_file(tmp_dir)
        load_with_missing_explicit_path()
        load_with_real_file(tmp_dir)


if __name__ == "__main__":
    main()
