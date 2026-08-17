"""
Example: structured error handling with zeo_core's ZeoError family.

zeo_core.core.errors defines a typed exception hierarchy (ZeoError and its
subclasses) carrying structured context (path, config_key, etc.) instead of
bare strings. This example shows:

1. A tool that loads and validates a small JSON "settings" file, raising
   specific ZeoError subclasses for each failure mode:
   - ZeoFileNotFoundError: the settings file doesn't exist.
   - ZeoFormatError: the file exists but isn't valid JSON.
   - ZeoValidationError: the file parses but is missing a required key.
2. The @wrap_io_errors decorator, which converts *unhandled* standard
   exceptions (OSError, ValueError, etc.) raised inside a wrapped function
   into the matching ZeoError subclass automatically -- so callers only
   need to catch ZeoError-family exceptions, not a mix of builtins and
   custom types.
3. A caller (main()) that walks three scenarios -- missing file, invalid
   JSON, and a missing required key -- catching each ZeoError subtype by
   name and printing its structured .context.

Run this file directly to see all three failure modes handled end to end:

    python examples/error_handling.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from zeo_core.core.errors import (
    ZeoError,
    ZeoFileNotFoundError,
    ZeoFormatError,
    ZeoValidationError,
    wrap_io_errors,
)

REQUIRED_KEYS = ("project_name", "output_dir")


@wrap_io_errors
def load_settings(path: Path) -> dict[str, Any]:
    """
    Load and validate a JSON settings file.

    Raises:
        ZeoFileNotFoundError: If path does not exist (converted by
            @wrap_io_errors from the builtin FileNotFoundError raised by
            Path.read_text()).
        ZeoFormatError: If the file exists but is not valid JSON.
        ZeoValidationError: If the file parses but is missing a required key.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        # Raised explicitly (rather than left to @wrap_io_errors) so we can
        # supply a clearer, tool-specific message than the generic converter
        # would produce.
        raise ZeoFileNotFoundError(
            path, message=f"Settings file not found: {path}"
        ) from e

    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ZeoFormatError(path, format_name="JSON", original_error=e) from e

    missing = [key for key in REQUIRED_KEYS if key not in data]
    if missing:
        raise ZeoValidationError(
            f"Settings file is missing required keys: {missing}",
            path=path,
            errors={"missing_keys": missing},
        )

    return data


def try_load(path: Path) -> None:
    """Attempt to load settings from path, reporting any ZeoError raised."""
    try:
        settings = load_settings(path)
        print(f"  OK: loaded settings {settings}")
    except ZeoFileNotFoundError as e:
        print(f"  ZeoFileNotFoundError: {e}")
        print(f"    context: {e.context}")
    except ZeoFormatError as e:
        print(f"  ZeoFormatError: {e}")
        print(f"    context: {e.context}")
    except ZeoValidationError as e:
        print(f"  ZeoValidationError: {e}")
        print(f"    context: {e.context}")
    except ZeoError as e:
        # Fallback: any other ZeoError subtype we didn't anticipate above.
        print(f"  ZeoError ({type(e).__name__}): {e}")


def main() -> None:
    """Exercise three real failure modes and one success case."""
    with tempfile.TemporaryDirectory(prefix="zeo_error_handling_") as tmp:
        tmp_dir = Path(tmp)

        print("1. Missing file:")
        try_load(tmp_dir / "does_not_exist.json")

        print("\n2. Invalid JSON:")
        bad_json_path = tmp_dir / "bad.json"
        bad_json_path.write_text("{not valid json", encoding="utf-8")
        try_load(bad_json_path)

        print("\n3. Valid JSON, missing required key:")
        incomplete_path = tmp_dir / "incomplete.json"
        incomplete_path.write_text(
            json.dumps({"project_name": "demo"}), encoding="utf-8"
        )
        try_load(incomplete_path)

        print("\n4. Valid, complete settings file:")
        good_path = tmp_dir / "good.json"
        good_path.write_text(
            json.dumps({"project_name": "demo", "output_dir": "./output"}),
            encoding="utf-8",
        )
        try_load(good_path)


if __name__ == "__main__":
    main()
