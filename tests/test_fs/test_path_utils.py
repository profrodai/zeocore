# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_fs/test_path_utils.py
# role: tests
# neighbors: __init__.py, test_atomic_wrapping.py, test_operations.py, test_results.py, test_service.py, test_utils.py
# exports: TestPathUtils
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

"""
Tests for the internal path utility functions.
"""

from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import pytest
from quack_core.core.fs import DataResult, PathResult
from quack_core.core.fs._internal.path_utils import _extract_path_str, _safe_path_str


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
            success=True,
            path=Path("a.txt"),
            is_valid=True,
            is_absolute=False,
            exists=False
        )
        assert _extract_path_str(result) == "a.txt"

    def test_extract_path_str_with_data_result_path(self):
        """Test extracting a path string from a DataResult with a path-like data."""
        result = DataResult(
            success=True,
            path=Path("ignored"),  # This should be ignored
            data=Path("b.txt"),    # This should be used
            format="path"
        )
        assert _extract_path_str(result) == "b.txt"

    def test_extract_path_str_with_data_result_string(self):
        """Test extracting a path string from a DataResult with a string data."""
        result = DataResult(
            success=True,
            path=Path("ignored"),  # This should be ignored
            data="c.txt",          # This should be used
            format="path"
        )
        assert _extract_path_str(result) == "c.txt"

    def test_extract_path_str_with_invalid_data_result(self):
        """Test that extracting from a DataResult with non-path data raises TypeError."""
        # Create a dummy path since None isn't allowed for path
        result = DataResult(success=True, path=Path("."), data=42, format="integer")
        with pytest.raises(TypeError):
            _extract_path_str(result)

    def test_extract_path_str_with_failed_result(self):
        """Test that extracting from a failed Result raises ValueError."""
        result = PathResult(
            success=False,
            path=Path("a.txt"),
            is_valid=False,
            is_absolute=False,
            exists=False
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
        """Test safe_path with a valid path."""
        assert _safe_path_str(Path("test.txt")) == "test.txt"

    def test_safe_path_with_invalid_object(self):
        """Test safe_path with an invalid object."""
        with patch('quack_core.core.fs._internal.path_utils.logger') as mock_logger:
            assert _safe_path_str(object()) is None
            mock_logger.warning.assert_called_once()

    def test_safe_path_with_custom_default(self):
        """Test safe_path with a custom default value."""
        with patch('quack_core.core.fs._internal.path_utils.logger') as mock_logger:
            assert _safe_path_str(object(), default="/fallback") == "/fallback"
            mock_logger.warning.assert_called_once()

    def test_safe_path_with_failed_result(self):
        """Test safe_path with a failed result."""
        with patch('quack_core.core.fs._internal.path_utils.logger') as mock_logger:
            result = PathResult(
                success=False,
                path=Path("a.txt"),
                is_valid=False,
                is_absolute=False,
                exists=False
            )
            assert _safe_path_str(result, default="default.txt") == "default.txt"
            mock_logger.warning.assert_called_once()
