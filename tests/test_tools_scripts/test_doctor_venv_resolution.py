"""
Regression coverage for tools/doctor.sh's virtual-environment resolution
(RULING-415 s3e, org corpus: a LOCATION bug, deliberately separate from the
s3e MODEL bug about extras -- that second gap is explicitly out of scope
here).

MEASURED DEFECT (Sparring seat, 2026-09-01): doctor.sh inspected ONLY the
project's own .venv/ and reported "no virtual environment" -- skipping five
of its seven checks -- whenever a perfectly good virtual environment was
active from anywhere else (~/.virtualenvs, conda, direnv, `uv venv --path`,
...). The tool exhibited the exact failure it exists to catch: a confident
report derived from looking in exactly one place. This hits students in a
live-demo setting hardest, since non-default venv layouts are common in a
room of laptops.

These tests shell out to the REAL tools/doctor.sh (same discipline as
tests/test_config/test_gitignore_secrets.py: "these tests shell out to the
real git ... exactly as verification was done by hand", never source-
grepping) with disposable, real venvs built via the stdlib `venv` module
(with_pip=False, near-instant, no network) so the resolution logic itself
is exercised, not a stand-in for it. What is NOT covered here: full package
install/import checks (steps 4-7 of doctor.sh) -- those need a real zeocore
install and are out of scope for a fast unit test; this file is scoped to
the resolution step (step 0 + step 3's report) which is what the defect and
the fix are about.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import venv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCTOR_SH = REPO_ROOT / "tools" / "doctor.sh"


def _make_bare_venv(path: Path) -> Path:
    """Create a real, disposable venv (no pip -- near-instant) and return
    its python executable path."""
    venv.EnvBuilder(with_pip=False, clear=True).create(str(path))
    python = path / "bin" / "python"
    assert python.exists(), f"venv builder did not produce {python}"
    return python


def _run_doctor(
    repo_root: Path, project_venv_python: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    bash = shutil.which("bash") or "bash"
    proc = subprocess.run(  # noqa: S603 -- fixed argv, resolved bash binary, test-only, no shell
        [bash, str(DOCTOR_SH), str(repo_root), str(project_venv_python), ".venv"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    return proc


def _clean_env(**overrides: str) -> dict[str, str]:
    """A minimal, controlled environment: real PATH (bash/tput/python3 must
    resolve) but with any pre-existing VIRTUAL_ENV/CONDA_PREFIX from the
    test runner's own session stripped, so the test's own scenario is the
    only signal doctor.sh can see.

    PATH itself is also scrubbed of any `bin/` directory belonging to an
    ACTIVE venv the test process happens to be running under (e.g. this
    very test suite runs inside .venv/bin/activate'd shell) -- otherwise
    doctor.sh's `python3 on PATH` fallback would pick up the test runner's
    OWN venv and the test could not observe a clean "nothing found" or
    "only .venv/ found" baseline. Real system/pyenv entries are kept.
    """
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)
    env.pop("CONDA_PREFIX", None)

    real_venv = os.environ.get("VIRTUAL_ENV")
    if real_venv:
        venv_bin = str(Path(real_venv) / "bin")
        parts = [p for p in env.get("PATH", "").split(os.pathsep) if p != venv_bin]
        env["PATH"] = os.pathsep.join(parts)

    env.update(overrides)
    return env


class TestDoctorVenvResolution:
    def test_doctor_sh_exists(self) -> None:
        """Sanity: the script this whole module tests is actually there."""
        assert DOCTOR_SH.exists(), f"expected {DOCTOR_SH} to exist"

    def test_default_layout_project_venv_used(self, tmp_path: Path) -> None:
        """No VIRTUAL_ENV/CONDA_PREFIX active, project .venv/ present -->
        doctor reports the project .venv/ plainly, no non-default-env
        warning. This is the pre-existing, unbroken default path."""
        project_venv_python = _make_bare_venv(tmp_path / ".venv")

        result = _run_doctor(tmp_path, project_venv_python, env=_clean_env())

        assert "virtual environment found at .venv/" in result.stdout
        assert "diagnosing a non-default environment" not in result.stdout
        assert "no virtual environment" not in result.stdout

    def test_active_virtual_env_elsewhere_is_used_and_reported(
        self, tmp_path: Path
    ) -> None:
        """THE REGRESSION THIS FIX CLOSES: an active VIRTUAL_ENV pointing
        somewhere other than the project's .venv/ (and no .venv/ present at
        all, matching the reported student scenario) must be FOUND and
        USED, and doctor must say plainly it is diagnosing a non-default
        environment -- never a silent 'no virtual environment'."""
        elsewhere = _make_bare_venv(tmp_path / "elsewhere-venv")
        # No .venv/ created under tmp_path at all -- the reported scenario.
        project_venv_python = tmp_path / ".venv" / "bin" / "python"

        env = _clean_env(VIRTUAL_ENV=str(tmp_path / "elsewhere-venv"))
        result = _run_doctor(tmp_path, project_venv_python, env=env)

        assert "no virtual environment" not in result.stdout
        assert "diagnosing a non-default environment" in result.stdout
        assert str(elsewhere) in result.stdout
        # Downstream checks must not be skipped on the "no venv yet" excuse.
        assert "skipped — no venv yet" not in result.stdout

    def test_conda_prefix_is_honoured_when_no_virtual_env(self, tmp_path: Path) -> None:
        """CONDA_PREFIX is conda's equivalent signal (conda never sets
        VIRTUAL_ENV) -- named explicitly in the reported defect's list of
        layouts doctor was blind to."""
        elsewhere = _make_bare_venv(tmp_path / "conda-env")
        project_venv_python = tmp_path / ".venv" / "bin" / "python"

        env = _clean_env(CONDA_PREFIX=str(tmp_path / "conda-env"))
        result = _run_doctor(tmp_path, project_venv_python, env=env)

        assert "no virtual environment" not in result.stdout
        assert "diagnosing a non-default environment" in result.stdout
        assert str(elsewhere) in result.stdout

    def test_stale_virtual_env_falls_back_to_project_venv(self, tmp_path: Path) -> None:
        """A VIRTUAL_ENV pointing at a directory that no longer exists (a
        dead activation) must not blind doctor to a perfectly good project
        .venv/ -- it should fall through, not fail through."""
        project_venv_python = _make_bare_venv(tmp_path / ".venv")

        env = _clean_env(VIRTUAL_ENV=str(tmp_path / "does-not-exist"))
        result = _run_doctor(tmp_path, project_venv_python, env=env)

        assert "virtual environment found at .venv/" in result.stdout
        assert "diagnosing a non-default environment" not in result.stdout

    def test_no_venv_anywhere_still_fails_honestly(self, tmp_path: Path) -> None:
        """The true-negative case must still fail: resolution must never
        manufacture a venv that does not exist anywhere."""
        project_venv_python = tmp_path / ".venv" / "bin" / "python"

        result = _run_doctor(tmp_path, project_venv_python, env=_clean_env())

        assert "✗ no virtual environment" in result.stdout or (
            "no virtual environment" in result.stdout and "✗" in result.stdout
        )
        # And the downstream checks correctly skip in THIS case only.
        assert "skipped — no venv yet" in result.stdout
