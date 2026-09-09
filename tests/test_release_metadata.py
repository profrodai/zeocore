"""Release mistakes must be refused before an index filename is consumed."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "ref,notes,entry,ok",
    [
        ("refs/heads/release", "# zeocore 1.2.3", "## [1.2.3] - 2026-09-09", True),
        ("refs/tags/v1.2.3", "# zeocore 1.2.3", "## [1.2.3] - 2026-09-09", True),
        ("refs/tags/v1.2.4", "# zeocore 1.2.3", "## [1.2.3] - 2026-09-09", False),
        ("refs/tags/v1.2.3", "# zeocore 1.2.2", "## [1.2.3] - 2026-09-09", False),
        ("refs/tags/v1.2.3", "# zeocore 1.2.3", "## [Unreleased]", False),
    ],
)
def test_release_identity_gate(
    tmp_path: Path, ref: str, notes: str, entry: str, ok: bool
) -> None:
    script = Path(__file__).resolve().parents[1] / "tools/check-release-identity-v1.py"
    (tmp_path / "tools").mkdir()
    copied = tmp_path / "tools" / script.name
    copied.write_bytes(script.read_bytes())
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n')
    (tmp_path / "RELEASE_NOTES.md").write_text(notes + "\n")
    (tmp_path / "CHANGELOG.md").write_text(entry + "\n")
    result = subprocess.run(  # noqa: S603 - fixed repository gate in an isolated fixture
        [sys.executable, str(copied)],
        env={**os.environ, "GITHUB_REF": ref},
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode == 0) is ok, result.stderr
