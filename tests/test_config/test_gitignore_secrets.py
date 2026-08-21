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


def _check_ignore(rel_path: str) -> tuple[int, str]:
    root = _repo_root()
    proc = subprocess.run(  # noqa: S603 -- fixed argv, resolved git binary, test-only, no shell
        [shutil.which("git") or "git", "check-ignore", "-v", rel_path],
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

    NOTE on `git check-ignore` semantics, learned writing this test: `-v`
    reports exit 0 whenever ANY pattern matches the path, INCLUDING a
    negation (`!`) pattern -- exit 0 does not by itself mean "ignored". The
    real behavioural signal for a negated match is that the LAST matching
    line is the `!`-prefixed one; `git status --porcelain` / `git add -n`
    confirm the actual outcome directly and are used here instead of relying
    on exit-code alone.
    """

    def test_env_example_is_trackable_per_git_add_dry_run(self) -> None:
        root = _repo_root()
        proc = subprocess.run(  # noqa: S603
            [shutil.which("git") or "git", "add", "--dry-run", ".env.example"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0
        assert "add '.env.example'" in proc.stdout, (
            "`git add -n .env.example` did not report it as addable -- "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )

    def test_env_example_check_ignore_last_match_is_the_negation(self) -> None:
        code, output = _check_ignore(".env.example")
        assert code == 0
        assert output.endswith("!.env.example\t.env.example"), (
            "expected the whitelist negation to be the (last) matching "
            f"rule; got: {output!r}"
        )

    def test_env_itself_is_still_ignored(self) -> None:
        code, output = _check_ignore(".env")
        assert code == 0, ".env itself must still be ignored"
        assert "!.env.example" not in output
