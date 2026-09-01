"""
Self-consistency guards for the facts a release must agree on internally.

RULING-413/RULING-414 (org corpus, 2026-09-01): the same evening a release
was blocked twice by facts that disagreed with each other and nothing
tested the disagreement -- a required CI check named a Python version that
a legitimate floor-bump PR could never produce again, and the published
package's own __version__ literal drifted from the version it was actually
tagged and published as. Both were caught by hand, late, by a human/agent
re-reading raw bytes rather than by any gate.

These tests assert on the SAME kind of fact: values that appear in more
than one file and are expected, structurally, to always agree. A test
here is not "is X true" -- it is "do these N independently-editable
statements of the same fact still say the same thing."
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _pyproject() -> dict:
    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)


def _requires_python_floor() -> tuple[int, int]:
    """Parse the (major, minor) floor out of pyproject's `requires-python`.

    Only the `>=X.Y` form is supported -- that is the only form this repo
    has ever used, and a different form appearing is itself worth a loud
    failure rather than a silent skip.
    """
    spec = _pyproject()["project"]["requires-python"]
    m = re.fullmatch(r">=\s*(\d+)\.(\d+)", spec.strip())
    assert m, (
        f"requires-python is {spec!r}, not the expected '>=X.Y' form this "
        "test knows how to parse. Update the parser, don't skip the check."
    )
    return int(m.group(1)), int(m.group(2))


def _ci_matrix_versions() -> list[str]:
    """Every python-version string in the CI job's matrix."""
    text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    m = re.search(r"python-version:\s*\[([^\]]+)\]", text)
    assert m, "ci.yml no longer declares a `python-version: [...]` matrix line"
    return [v.strip().strip("\"'") for v in m.group(1).split(",")]


def test_ci_matrix_agrees_with_pyproject_floor() -> None:
    """Every Python version CI tests against must satisfy the declared floor.

    RULING-413's failure was the mirror image of this: a required check
    named a version CI no longer produced. This test guards the more basic
    fact underneath that incident -- CI's matrix and pyproject's floor
    talking about the same interpreter version.
    """
    floor = _requires_python_floor()
    for raw in _ci_matrix_versions():
        major, minor = (int(p) for p in raw.split("."))
        assert (major, minor) >= floor, (
            f"CI matrix tests Python {raw}, which is BELOW the "
            f"requires-python floor {floor[0]}.{floor[1]} in pyproject.toml. "
            "Either the matrix or the floor is stale."
        )


def test_ci_matrix_includes_the_floor_version() -> None:
    """CI should test AT the floor, not only above it.

    A matrix that only runs newer interpreters never proves the floor
    itself still works -- exactly the gap that let the floor and the
    matrix drift apart unnoticed in the lead-up to RULING-413.
    """
    floor = _requires_python_floor()
    floor_str = f"{floor[0]}.{floor[1]}"
    versions = _ci_matrix_versions()
    assert floor_str in versions, (
        f"requires-python floor is {floor_str}, but the CI matrix "
        f"{versions} never runs it directly."
    )


def test_makefile_default_python_version_matches_floor() -> None:
    """Makefile's PYTHON_VERSION default must match the declared floor.

    `make setup`/`make env` build the default onboarding venv from this
    value -- a beginner who never overrides PYTHON_VERSION gets whatever
    this line says, regardless of what pyproject.toml or the README claim.
    """
    floor = _requires_python_floor()
    floor_str = f"{floor[0]}.{floor[1]}"
    text = (REPO_ROOT / "Makefile").read_text()
    m = re.search(r"^PYTHON_VERSION\s*:=\s*(\S+)", text, re.MULTILINE)
    assert m, "Makefile no longer declares `PYTHON_VERSION := ...`"
    assert m.group(1) == floor_str, (
        f"Makefile's PYTHON_VERSION default is {m.group(1)!r}, but "
        f"pyproject.toml's requires-python floor is {floor_str!r}."
    )


def test_contributing_guide_states_the_current_floor() -> None:
    """CONTRIBUTING.md's stated floor must match pyproject.toml's.

    Measured live during RULING-414/415 recon: CONTRIBUTING.md said
    'Python 3.13 by default... the package itself requires 3.13+' while
    pyproject.toml had already moved to >=3.14 -- a stranded floor
    statement in exactly the doc a new contributor reads first.
    """
    floor = _requires_python_floor()
    floor_str = f"{floor[0]}.{floor[1]}"
    text = (REPO_ROOT / "CONTRIBUTING.md").read_text()
    assert f"requires {floor_str}+" in text or f">={floor_str}" in text, (
        f"CONTRIBUTING.md does not state the current floor ({floor_str}+) "
        "anywhere findable. It may still be quoting an old floor."
    )


def test_quickstart_states_the_current_floor() -> None:
    """QUICKSTART.md's headline floor claim must match pyproject.toml's."""
    floor = _requires_python_floor()
    floor_str = f"{floor[0]}.{floor[1]}"
    text = (REPO_ROOT / "QUICKSTART.md").read_text()
    assert f"Python {floor_str}" in text, (
        f"QUICKSTART.md does not mention the current floor "
        f"(Python {floor_str}) anywhere. It may still be quoting an old floor."
    )


def test_readme_current_requirement_states_the_floor() -> None:
    """README's '## Requirements' section must lead with the current floor.

    README is allowed to mention an OLD floor for context (e.g. "if you're
    pinned to an older interpreter, stay on 0.5.0, which requires
    >=3.13") -- that is deliberate migration guidance, not drift. What it
    may not do is fail to mention the CURRENT floor as the headline
    requirement.
    """
    floor = _requires_python_floor()
    floor_str = f"{floor[0]}.{floor[1]}"
    text = (REPO_ROOT / "README.md").read_text()
    assert f"Python {floor_str} or newer" in text, (
        f"README.md's Requirements section does not lead with the current "
        f"floor ('Python {floor_str} or newer'). It may be stranded on an "
        "older floor statement."
    )
