"""Refuse inconsistent release notes, changelog or version tags before publishing."""

import os
import re
import sys
import tomllib
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise SystemExit("Release version must be a stable three-part version")
    if (root / "RELEASE_NOTES.md").read_text().splitlines()[0] != f"# zeocore {version}":
        raise SystemExit("Release notes heading does not match package version")
    if not re.search(
        rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$",
        (root / "CHANGELOG.md").read_text(), re.MULTILINE,
    ):
        raise SystemExit("Dated changelog entry does not match package version")
    ref = os.environ.get("GITHUB_REF", "")
    if ref.startswith("refs/tags/") and ref != f"refs/tags/v{version}":
        raise SystemExit("Version tag does not match package version")
    print(f"Release identity verified: zeocore {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
