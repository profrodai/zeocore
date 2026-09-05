"""Meta-tests for the coverage gate's exact boundary."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from coverage.results import should_fail_under

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_coverage_gate_enforces_literal_two_decimal_threshold() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        configuration = tomllib.load(handle)
    precision = configuration["tool"]["coverage"]["report"]["precision"]
    makefile = (REPO_ROOT / "Makefile").read_text()
    match = re.search(r"^COVERAGE_THRESHOLD\s*:=\s*([0-9.]+)$", makefile, re.MULTILINE)

    assert match is not None
    threshold = float(match.group(1))
    assert precision == 2
    assert should_fail_under(89.99, threshold, precision) is True
    assert should_fail_under(90.00, threshold, precision) is False
