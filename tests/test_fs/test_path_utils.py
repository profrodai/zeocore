# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_fs/test_path_utils.py
# === QV-LLM:END ===

"""
Tests for the internal path utility functions.

Note: `_extract_path_str`/`safe_path_str` live in `quack_core.core.fs.normalize`
now, not `_internal.path_utils` (that module never existed under this name in
this repo's history; the low-level string-extraction logic was consolidated
into `normalize.py`, the documented "Single Source of Truth for coercing
inputs into Paths"). The public `safe_path_str` (no leading underscore) is the
current equivalent of the old private `_safe_path_str` -- same try/except/
default-on-failure contract, confirmed by reading `normalize.py` in full.
"""

from pathlib import Path
from unittest import TestCase

import pytest
from quack_core.core.fs import DataResult, PathResult
from quack_core.core.fs.normalize import _extract_path_str, safe_path_str


class TestPathUtils(TestCase):
    """Tests for the path utility functions."""

    def test_extract_path_str_with_path(self):
        """Test extracting a path string from a Path object."""
        path = Path("test.txt")
        assert _extract_path_str(path) == "test.txt"

    def test_extract_path_str_with_string(self):
        """Test extracting a path string from a string."""
        path = "test.txt"
        assert _extract_path_str(path) == "test.txt"

    def test_extract_path_str_with_path_result(self):
        """Test extracting a path string from a PathResult object."""
        result = PathResult(
            ok=True,
            path=Path("a.txt"),
            is_valid=True,
            is_absolute=False,
            exists=False,
        )
        assert _extract_path_str(result) == "a.txt"

    def test_extract_path_str_with_data_result_path(self):
        """Test extracting a path string from a DataResult with a path-like data."""
        result = DataResult(
            ok=True,
            path=Path("ignored"),  # This should be ignored
            data=Path("b.txt"),  # This should be used
            format="path",
        )
        assert _extract_path_str(result) == "b.txt"

    def test_extract_path_str_with_data_result_string(self):
        """Test extracting a path string from a DataResult with a string data."""
        result = DataResult(
            ok=True,
            path=Path("ignored"),  # This should be ignored
            data="c.txt",  # This should be used
            format="path",
        )
        assert _extract_path_str(result) == "c.txt"

    def test_extract_path_str_with_non_path_data_falls_back_to_path(self):
        """Test that a DataResult with non-path-like `.data` falls back to `.path`
        rather than raising.

        NOTE (fs-internals-fix): the old assertion here expected `TypeError` when
        `data` was a non-path type (e.g. an int). Reading `normalize.py`'s
        `_extract_path_str` in full: it deliberately only trusts `.data` "if it is
        explicitly a string or path-like ... prevents treating arbitrary payloads
        (dicts, lists) as paths" (comment in source) and otherwise falls through to
        `.path`. So a non-path `data` with a usable `.path` set does NOT raise --
        it silently prefers `.path`. This is current, intentional doctrine (not a
        regression to work around), so the test is corrected to assert the actual
        fallback behavior instead of a raise that no longer happens.
        """
        result = DataResult(
            ok=True, path=Path("fallback.txt"), data=42, format="integer"
        )
        assert _extract_path_str(result) == "fallback.txt"

    def test_extract_path_str_with_invalid_data_result(self):
        """Test that extracting from a DataResult with neither usable `.data` nor
        `.path` raises TypeError."""
        result = DataResult(ok=True, path=None, data=42, format="integer")
        with pytest.raises(TypeError):
            _extract_path_str(result)

    def test_extract_path_str_with_failed_result(self):
        """Test that extracting from a failed Result raises ValueError."""
        result = PathResult(
            ok=False,
            path=Path("a.txt"),
            is_valid=False,
            is_absolute=False,
            exists=False,
        )
        with pytest.raises(ValueError):
            _extract_path_str(result)

    def test_extract_path_str_with_invalid_object(self):
        """Test that extracting from an invalid object raises TypeError."""
        with pytest.raises(TypeError):
            _extract_path_str(object())

    def test_extract_path_str_with_value_method(self):
        """Test extracting from an object with a value method."""

        class ResultWithValue:
            success = True

            def value(self):
                return "unwrapped.txt"

        result = ResultWithValue()
        assert _extract_path_str(result) == "unwrapped.txt"

    def test_extract_path_str_with_unwrap_method(self):
        """Test extracting from an object with an unwrap method."""

        class ResultWithUnwrap:
            success = True

            def unwrap(self):
                return Path("unwrapped.txt")

        result = ResultWithUnwrap()
        assert _extract_path_str(result) == "unwrapped.txt"

    def test_extract_path_str_with_nested_unwrapping(self):
        """Test extracting from nested result objects that need unwrapping."""

        class InnerResult:
            success = True

            def value(self):
                return Path("inner.txt")

        class OuterResult:
            success = True

            def value(self):
                return InnerResult()

        result = OuterResult()
        assert _extract_path_str(result) == "inner.txt"

    def test_safe_path_with_valid_path(self):
        """Test safe_path_str with a valid path."""
        assert safe_path_str(Path("test.txt")) == "test.txt"

    def test_safe_path_with_invalid_object(self):
        """Test safe_path_str with an invalid object.

        NOTE (fs-internals-fix): the old private `_safe_path_str` (in a
        `_internal.path_utils` module that no history in this repo shows ever
        existing) logged a `logger.warning` on every fallback. The current
        `normalize.safe_path_str`, read in full, has NO logger at all --
        confirmed no `_internal` module defines one either. That specific
        logging behavior is genuinely gone, not renamed; the three
        `mock_logger.warning.assert_called_once()` assertions from the old
        file are dropped rather than faked against a logger that isn't
        called. The behavior this subtest actually pins -- an invalid object
        falls back to the default instead of raising -- still holds and is
        kept.
        """
        assert safe_path_str(object()) is None

    def test_safe_path_with_custom_default(self):
        """Test safe_path_str with a custom default value."""
        assert safe_path_str(object(), default="/fallback") == "/fallback"

    def test_safe_path_with_failed_result(self):
        """Test safe_path_str with a failed Result (ok=False)."""
        result = PathResult(
            ok=False,
            path=Path("a.txt"),
            is_valid=False,
            is_absolute=False,
            exists=False,
        )
        assert safe_path_str(result, default="default.txt") == "default.txt"
