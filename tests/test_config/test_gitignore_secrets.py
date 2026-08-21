"""Behavioural regression coverage for the config-secrets-hardening charter's
item 2 (`.gitignore` config-YAML patterns, RULING-356 s4.2).

The charter is explicit: "File modes and gitignore matches are BEHAVIOURAL
claims: prove them with `stat` and `git check-ignore -v`, not by reading
source." These tests shell out to the real `git check-ignore` against the
real repo `.gitignore`, exactly as that verification was done by hand while
authoring the fix -- a change to `.gitignore` that silently regresses this
coverage is caught by running git, not by grepping a pattern string.

Scope: `config/loader.py:52-57` (`DEFAULT_CONFIG_LOCATIONS`) names four
default config-file locations. Only two are repo-relative and thus coverable
by a repo-local `.gitignore` at all: `./zeo_config.yaml` and
`./config/zeo_config.yaml`. `~/.zeo/config.yaml` and `/etc/zeo/config.yaml`
sit outside any repo tree and cannot be reached by this file; that is stated
here rather than silently assumed.
"""

import shutil
import subprocess
from pathlib import Path

import pytest


def _repo_root() -> Path:
    """Walk up from this file to the directory holding .git, same discipline
    `zeo_core.config.utils.find_project_root` uses for its own root-finding
    (not reused directly to avoid coupling the test to the app's own logic
    under test elsewhere in the suite)."""
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("no .git found walking up from test file")


def _check_ignore(rel_path: str, *, no_index: bool = False) -> tuple[int, str]:
    """Run `git check-ignore -v` and return (exit_code, stdout).

    Semantics MEASURED on git 2.55.0, not assumed (two wrong guesses were
    made and corrected before these notes were written):

    - WITHOUT `--no-index`: git skips ignore rules for TRACKED files, so a
      tracked path always exits 1 with empty output no matter what
      `.gitignore` says. An assertion on a tracked path therefore cannot
      fail -- verified by mutation: deleting `!.env.example` did not turn
      such a test red.
    - WITH `--no-index`: the rules are consulted regardless of tracking, and
      exit 0 means SOME pattern matched -- INCLUDING a negation. So exit code
      alone cannot distinguish "ignored" from "whitelisted"; the winning rule
      printed in the output is the real signal.

    Hence: use `no_index=True` for any tracked path, and assert on WHICH rule
    won rather than on the exit code alone.
    """
    root = _repo_root()
    argv = [shutil.which("git") or "git", "check-ignore", "-v"]
    if no_index:
        argv.append("--no-index")
    argv.append(rel_path)
    proc = subprocess.run(  # noqa: S603 -- fixed argv, resolved git binary, test-only, no shell
        argv,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout.strip()


pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")


class TestDefaultConfigLocationsAreIgnored:
    """The two repo-relative default config locations must be matched by a
    gitignore rule -- exit 0 from `git check-ignore` means "would be
    ignored", exit 1 means "not ignored" (a real secret-bearing YAML file
    dropped at one of these exact paths would be commit-able)."""

    def test_root_zeo_config_yaml_is_ignored(self) -> None:
        code, output = _check_ignore("zeo_config.yaml")
        assert code == 0, (
            f"./zeo_config.yaml is NOT ignored (git check-ignore exit {code}); "
            "a secret-bearing config file at this default location would be "
            "committable. .gitignore output: " + output
        )
        assert "zeo_config.yaml" in output

    def test_config_dir_zeo_config_yaml_is_ignored(self) -> None:
        code, output = _check_ignore("config/zeo_config.yaml")
        assert code == 0, (
            f"./config/zeo_config.yaml is NOT ignored (git check-ignore exit "
            f"{code}); a secret-bearing config file at this default location "
            "would be committable. .gitignore output: " + output
        )
        assert "config/zeo_config.yaml" in output


class TestPatternDoesNotSwallowUnrelatedFiles:
    """The fix must be narrow: it must not blanket-ignore every YAML under
    config/, nor every zeo_config.yaml anywhere in the tree (e.g. a
    legitimately-tracked sample under examples/) -- only the two exact
    default-location paths."""

    def test_other_yaml_under_config_dir_not_ignored(self) -> None:
        code, _ = _check_ignore("config/other_settings.yaml")
        assert code == 1, "an unrelated file under config/ must not be ignored"

    def test_same_filename_under_examples_not_ignored(self) -> None:
        code, _ = _check_ignore("examples/zeo_config.yaml")
        assert code == 1, (
            "a same-named file outside the repo root/config/ default "
            "locations (e.g. a committed sample under examples/) must not "
            "be swallowed by the pattern"
        )

    def test_nested_config_dir_not_ignored(self) -> None:
        code, _ = _check_ignore("subdir/config/zeo_config.yaml")
        assert code == 1, (
            "the pattern is anchored to the repo root's config/, not any "
            "config/ directory anywhere in the tree"
        )


class TestEnvExampleStillWhitelisted:
    """Regression guard: the pre-existing `!.env.example` whitelist
    (.gitignore:42 before this change) must survive untouched -- it is the
    one file secrets docs point users at to copy.

    See `_check_ignore`'s docstring for the measured `git check-ignore`
    semantics these assertions rely on.

    An earlier revision asserted via `git add --dry-run`, which prints
    `add '<path>'` only for an UNTRACKED file. It passed while `.env.example`
    was still uncommitted and failed for every reader afterwards -- an
    assertion on a transient state rather than on the property. The
    replacement asserts on which gitignore rule WINS, and is mutation-tested:
    deleting `!.env.example` from `.gitignore` turns it red.
    """

    def test_env_example_rule_is_not_ignored_when_untracked(self) -> None:
        """The whitelist RULE must survive, tested where git will actually
        evaluate it.

        `--no-index` is load-bearing. Once a file is tracked, git skips
        ignore rules for it entirely and `check-ignore` returns 1 no matter
        what `.gitignore` says -- so asserting on the tracked path passes
        even with `!.env.example` deleted (verified by mutation: removing the
        negation did not fail the assertion). `--no-index` forces the rules
        to be consulted, which is the thing under test.
        """
        code, output = _check_ignore(".env.example", no_index=True)
        assert code == 0, (
            "expected a matching rule to be reported under --no-index; "
            f"got exit={code} output={output!r}"
        )
        assert output.endswith("!.env.example\t.env.example"), (
            "the WINNING rule for `.env.example` must be the `!` whitelist, "
            f"not an ignore rule; got: {output!r}"
        )

    def test_a_plain_dotenv_is_still_ignored_when_untracked(self) -> None:
        """Control for the test above: same code path, opposite expectation.
        If this ever returns 1, the `.env` rules have stopped working and the
        test above would be passing vacuously."""
        code, output = _check_ignore(".env.local", no_index=True)
        assert code == 0, (
            f"`.env.local` must match an ignore rule; got exit={code} output={output!r}"
        )
        assert not output.startswith("!") and "!.env.example" not in output, (
            f"`.env.local` must be IGNORED, not whitelisted; got: {output!r}"
        )

    def test_env_example_is_actually_tracked(self) -> None:
        """Complements the rule check with the outcome: the file is really in
        the index, not merely ignorable-in-principle."""
        root = _repo_root()
        proc = subprocess.run(  # noqa: S603
            [
                shutil.which("git") or "git",
                "ls-files",
                "--error-unmatch",
                ".env.example",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, (
            ".env.example must be tracked in the index -- "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )

    def test_env_itself_is_still_ignored(self) -> None:
        code, output = _check_ignore(".env")
        assert code == 0, ".env itself must still be ignored"
        assert "!.env.example" not in output
