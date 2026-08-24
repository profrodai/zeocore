"""Smoke-test beginner examples that require only the base installation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


class ExampleCase(NamedTuple):
    """A credential-free example and its stable stdout contract."""

    script: str
    stdout: str


SAFE_EXAMPLES = (
    ExampleCase(
        "minimal_tool.py",
        "Tool initialized: word_count initialized\n"
        "Result: Word count completed\n"
        "Words: 8, Characters: 73\n",
    ),
    ExampleCase("capability_authoring.py", "Hello, World!\n"),
    ExampleCase(
        "capability_guards.py",
        "accepted: hello-world\n"
        "rejected outcome: guard_rejected\n"
        "rejected code: ZEO_CAP_GUARD_REJECTED\n"
        "rejected has data: False\n",
    ),
    ExampleCase(
        "tool_to_capability.py",
        "class run: 2\n"
        "invoke_sync: 2\n"
        "canonical id: demo.word_count@1.0.0\n"
        "registry hit: True\n",
    ),
    ExampleCase(
        "llm_tools_usage.py",
        "projected name: demo_greet_v1_0_0\n"
        "description: Greet a person by name.\n"
        "required: ['name']\n"
        "properties: ['name']\n"
        "refusal ok: False\n"
        "refusal reason: unsupported JSON Schema keyword 'not' cannot be preserved\n",
    ),
)


@pytest.mark.parametrize("case", SAFE_EXAMPLES, ids=lambda case: case.script)
def test_beginner_example_runs_offline(case: ExampleCase, tmp_path: Path) -> None:
    """Run an allowlisted example without credentials or user configuration."""
    environment = {
        "HOME": str(tmp_path),
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
    }
    completed = subprocess.run(  # noqa: S603 - static, repository-owned scripts
        [sys.executable, str(REPO_ROOT / "examples" / case.script)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
        timeout=20,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    assert completed.stdout == case.stdout
