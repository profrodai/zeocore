# quack-core/tests/test_cli/test_terminal.py
"""
Tests for the CLI terminal module.
"""

import os
import sys
from unittest.mock import MagicMock, patch

from quackcore.cli.terminal import (
    get_terminal_size,
    supports_color,
    truncate_text,
)


class TestGetTerminalSize:
    """Tests for get_terminal_size function."""

    def test_with_shutil(self) -> None:
        """Test using shutil.get_terminal_size."""
        with patch("shutil.get_terminal_size") as mock_get_size:
            mock_terminal_size = MagicMock()
            mock_terminal_size.columns = 80
            mock_terminal_size.lines = 24
            mock_get_size.return_value = mock_terminal_size

            columns, lines = get_terminal_size()

            assert columns == 80
            assert lines == 24
            mock_get_size.assert_called_once_with((80, 24))

    def test_with_import_error(self) -> None:
        """Test handling ImportError for shutil."""
        with patch("shutil.get_terminal_size", side_effect=ImportError):
            columns, lines = get_terminal_size()

            # Should return default values
            assert columns == 80
            assert lines == 24

    def test_with_os_error(self) -> None:
        """Test handling OSError from shutil."""
        with patch("shutil.get_terminal_size", side_effect=OSError):
            columns, lines = get_terminal_size()

            # Should return default values
            assert columns == 80
            assert lines == 24


class TestSupportsColor:
    """Tests for supports_color function."""

    def test_with_no_color_env(self) -> None:
        """Test with NO_COLOR environment variable set."""
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            assert supports_color() is False

    def test_with_no_color_flag(self) -> None:
        """Test with --no-color flag in sys.argv."""
        with patch.object(sys, "argv", ["program", "--no-color"]):
            assert supports_color() is False

    def test_with_tty(self) -> None:
        """Test with stdout being a TTY."""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(sys, "argv", ["program"]):
                # Mock sys.stdout.isatty to return True
                mock_stdout = MagicMock()
                mock_stdout.isatty.return_value = True

                with patch.object(sys, "stdout", mock_stdout):
                    assert supports_color() is True

    def test_with_no_tty(self) -> None:
        """Test with stdout not being a TTY."""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(sys, "argv", ["program"]):
                # Mock sys.stdout.isatty to return False
                mock_stdout = MagicMock()
                mock_stdout.isatty.return_value = False

                with patch.object(sys, "stdout", mock_stdout):
                    # Without any other indicators, should return False
                    assert supports_color() is False

    def test_with_github_actions(self) -> None:
        """Test with GitHub Actions environment."""
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            with patch.object(sys, "argv", ["program"]):
                # Even without TTY, should return True in GitHub Actions
                mock_stdout = MagicMock()
                mock_stdout.isatty.return_value = False

                with patch.object(sys, "stdout", mock_stdout):
                    assert supports_color() is True

    def test_with_ci_force_colors(self) -> None:
        """Test with CI environment and force colors."""
        with patch.dict(os.environ, {"CI": "true", "CI_FORCE_COLORS": "1"}):
            with patch.object(sys, "argv", ["program"]):
                # Even without TTY, should return True with CI_FORCE_COLORS
                mock_stdout = MagicMock()
                mock_stdout.isatty.return_value = False

                with patch.object(sys, "stdout", mock_stdout):
                    assert supports_color() is True


class TestTruncateText:
    """Tests for truncate_text function."""

    def test_without_truncation(self) -> None:
        """Test when text doesn't need truncation."""
        text = "Short text"
        result = truncate_text(text, 20)

        # Text should remain unchanged
        assert result == text

    def test_with_truncation(self) -> None:
        """Test when text needs truncation."""
        text = "This is a long text that will be truncated"
        max_length = 20
        indicator = "..."

        result = truncate_text(text, max_length)

        # Text should be truncated to max_length (including indicator)
        assert len(result) == max_length
        # Should end with the indicator
        assert result.endswith(indicator)
        # Should start with the beginning of the original text
        assert result.startswith(text[: max_length - len(indicator)])

    def test_with_custom_indicator(self) -> None:
        """Test with custom truncation indicator."""
        text = "This is a long text that will be truncated"
        max_length = 20
        indicator = "[...]"

        result = truncate_text(text, max_length, indicator)

        # Text should be truncated to max_length (including indicator)
        assert len(result) == max_length
        # Should end with the custom indicator
        assert result.endswith(indicator)
        # Should start with the beginning of the original text
        assert result.startswith(text[: max_length - len(indicator)])

    def test_edge_cases(self) -> None:
        """Test edge cases for truncation."""
        # Empty text
        assert truncate_text("", 10) == ""

        # Text exactly at max length
        text = "Exact size"
        assert truncate_text(text, len(text)) == text

        # Text one character longer than max_length
        text = "One longer"
        assert len(truncate_text(text, len(text) - 1)) == len(text) - 1

        # Indicator longer than max_length
        text = "Short"
        assert truncate_text(text, 2, "...") == ".."
