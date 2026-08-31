"""
Tests for zeo_core.config.dotenv_loader -- RULING-407 item 4: `.env` SHALL
actually load. `.env.example` has always documented `.env` as "the
documented home for secrets in ZeoCore," but nothing in `src/` imported
`dotenv` before this fix -- the documented path was inert.

Real files, real `python-dotenv` calls (no mocking of `dotenv` itself): the
whole point of this feature is that a real `.env` file's contents land in
`os.environ`, so a test that mocks `load_dotenv` would prove nothing about
whether the documented path actually works.
"""

from collections.abc import Generator
from pathlib import Path

import pytest

from zeo_core.config.dotenv_loader import load_dotenv_file


@pytest.fixture(autouse=True)
def _clean_probe_env_vars() -> Generator[None]:
    """Every test below uses env var names prefixed ZEOCORE_DOTENV_TEST_ so
    they can never collide with a real secret name -- this fixture removes
    them before AND after each test so no test's .env leaks into another
    test via a real inherited process environment."""
    import os

    names = [k for k in os.environ if k.startswith("ZEOCORE_DOTENV_TEST_")]
    for name in names:
        del os.environ[name]
    yield
    names = [k for k in os.environ if k.startswith("ZEOCORE_DOTENV_TEST_")]
    for name in names:
        del os.environ[name]


class TestLoadDotenvFile:
    def test_loads_explicit_path_into_process_environment(self, tmp_path: Path) -> None:
        import os

        env_file = tmp_path / ".env"
        env_file.write_text("ZEOCORE_DOTENV_TEST_TOKEN=abc123\n")

        result = load_dotenv_file(env_file)

        assert result is True
        assert os.environ["ZEOCORE_DOTENV_TEST_TOKEN"] == "abc123"  # noqa: S105 -- fake test value

    def test_missing_file_returns_false_and_does_not_raise(
        self, tmp_path: Path
    ) -> None:
        missing = tmp_path / "does-not-exist" / ".env"
        # python-dotenv's own load_dotenv treats an explicit nonexistent
        # path as "nothing to load", not an error -- "no .env present" is a
        # normal, expected state (e.g. production env injection), never a
        # crash.
        result = load_dotenv_file(missing)
        assert result is False

    def test_searches_upward_from_cwd_when_no_path_given(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import os

        (tmp_path / ".env").write_text("ZEOCORE_DOTENV_TEST_FOUND=yes\n")
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)

        result = load_dotenv_file()

        assert result is True
        assert os.environ["ZEOCORE_DOTENV_TEST_FOUND"] == "yes"

    def test_no_dotenv_anywhere_above_cwd_returns_false(self, tmp_path: Path) -> None:
        # An isolated tmp_path tree with no .env file anywhere in it or its
        # ancestors up to filesystem root would be flaky to assert against
        # directly (CI/dev machines may have unrelated .env files above
        # tmp_path) -- instead, point find_dotenv at a directory that
        # provably has no .env of its own and pass usecwd explicitly via an
        # explicit nonexistent dotenv_path instead, which is the same
        # "nothing found" contract without depending on ancestor state.
        result = load_dotenv_file(tmp_path / ".env")
        assert result is False

    def test_default_search_finds_nothing_returns_false(self) -> None:
        """The dotenv_path=None branch's own "nothing found at all" case
        (find_dotenv(usecwd=True) returning ""), isolated from real
        ancestor-directory state by mocking find_dotenv directly -- this
        tests OUR glue logic's handling of an empty return, not
        python-dotenv's own upward-search algorithm (already exercised for
        real by test_searches_upward_from_cwd_when_no_path_given above)."""
        from unittest.mock import patch

        with patch(
            "zeo_core.config.dotenv_loader.find_dotenv", return_value=""
        ) as mock_find:
            result = load_dotenv_file()
            assert result is False
            mock_find.assert_called_once_with(usecwd=True)

    def test_default_does_not_override_existing_env_var(self, tmp_path: Path) -> None:
        import os

        os.environ["ZEOCORE_DOTENV_TEST_PRESET"] = "already-set"
        env_file = tmp_path / ".env"
        env_file.write_text("ZEOCORE_DOTENV_TEST_PRESET=from-dotenv\n")

        load_dotenv_file(env_file)

        assert os.environ["ZEOCORE_DOTENV_TEST_PRESET"] == "already-set"

    def test_override_true_replaces_existing_env_var(self, tmp_path: Path) -> None:
        import os

        os.environ["ZEOCORE_DOTENV_TEST_PRESET"] = "already-set"
        env_file = tmp_path / ".env"
        env_file.write_text("ZEOCORE_DOTENV_TEST_PRESET=from-dotenv\n")

        load_dotenv_file(env_file, override=True)

        assert os.environ["ZEOCORE_DOTENV_TEST_PRESET"] == "from-dotenv"

    def test_empty_dotenv_file_returns_false(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("")

        result = load_dotenv_file(env_file)

        assert result is False

    def test_pathlib_path_and_str_both_accepted(self, tmp_path: Path) -> None:
        import os

        env_file = tmp_path / ".env"
        env_file.write_text("ZEOCORE_DOTENV_TEST_STRPATH=works\n")

        result = load_dotenv_file(str(env_file))

        assert result is True
        assert os.environ["ZEOCORE_DOTENV_TEST_STRPATH"] == "works"
