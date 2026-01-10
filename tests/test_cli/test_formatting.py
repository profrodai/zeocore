# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_cli/test_formatting.py
# role: tests
# neighbors: __init__.py, mocks.py, test_bootstrap.py, test_config.py, test_context.py, test_error.py (+5 more)
# exports: TestColor, TestColorize, TestPrintFunctions, TestTable, TestDictToTable
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

"""
Tests for the CLI formatting module.
"""

import sys
from unittest.mock import patch

from quack_core.interfaces.cli.utils.formatting import (
    Color,
    colorize,
    dict_to_table,
    print_debug,
    print_error,
    print_info,
    print_success,
    print_warning,
    table,
)


class TestColor:
    """Tests for the Color enum."""

    def test_color_values(self) -> None:
        """Test color enum values."""
        # Foreground colors
        assert Color.BLACK == "30"
        assert Color.RED == "31"
        assert Color.GREEN == "32"
        assert Color.YELLOW == "33"
        assert Color.BLUE == "34"
        assert Color.MAGENTA == "35"
        assert Color.CYAN == "36"
        assert Color.WHITE == "37"
        assert Color.RESET == "39"

        # Background colors
        assert Color.BG_BLACK == "40"
        assert Color.BG_RED == "41"
        assert Color.BG_GREEN == "42"
        assert Color.BG_YELLOW == "43"
        assert Color.BG_BLUE == "44"
        assert Color.BG_MAGENTA == "45"
        assert Color.BG_CYAN == "46"
        assert Color.BG_WHITE == "47"
        assert Color.BG_RESET == "49"

        # Styles
        assert Color.BOLD == "1"
        assert Color.DIM == "2"
        assert Color.ITALIC == "3"
        assert Color.UNDERLINE == "4"
        assert Color.BLINK == "5"
        assert Color.REVERSE == "7"
        assert Color.STRIKE == "9"

        # Reset all
        assert Color.RESET_ALL == "0"


class TestColorize:
    """Tests for colorize function."""

    def test_basic_colorization(self) -> None:
        """Test basic text colorization."""
        # Test with foreground color
        with patch("quack_core.interfaces.cli.utils.formatting.supports_color", return_value=True):
            result = colorize("Test text", fg="red")
            assert result == "\033[31mTest text\033[0m"

        # Test with background color
        with patch("quack_core.interfaces.cli.utils.formatting.supports_color", return_value=True):
            result = colorize("Test text", bg="blue")
            assert result == "\033[44mTest text\033[0m"

        # Test with both fg and bg
        with patch("quack_core.interfaces.cli.utils.formatting.supports_color", return_value=True):
            result = colorize("Test text", fg="green", bg="white")
            assert result == "\033[32;47mTest text\033[0m"

    def test_with_styles(self) -> None:
        """Test text with style attributes."""
        # Test with bold
        with patch("quack_core.interfaces.cli.utils.formatting.supports_color", return_value=True):
            result = colorize("Test text", bold=True)
            assert result == "\033[1mTest text\033[0m"

        # Test with multiple styles
        with patch("quack_core.interfaces.cli.utils.formatting.supports_color", return_value=True):
            result = colorize("Test text", fg="blue", bold=True, underline=True)
            assert result == "\033[1;4;34mTest text\033[0m"

    def test_without_color_support(self) -> None:
        """Test behavior when terminal doesn't support color."""
        # When color is not supported, should return the original text
        with patch("quack_core.interfaces.cli.utils.formatting.supports_color", return_value=False):
            result = colorize("Test text", fg="red", bold=True)
            assert result == "Test text"

        # Unless force=True is specified
        with patch("quack_core.interfaces.cli.utils.formatting.supports_color", return_value=False):
            result = colorize("Test text", fg="red", bold=True, force=True)
            assert result == "\033[1;31mTest text\033[0m"

    def test_all_style_combinations(self) -> None:
        """Test various style combinations."""
        with patch("quack_core.interfaces.cli.utils.formatting.supports_color", return_value=True):
            # Test all styles together
            result = colorize(
                "Test text",
                fg="blue",
                bg="white",
                bold=True,
                dim=True,
                underline=True,
                italic=True,
                blink=True,
            )

            # Should include all the codes
            assert "\033[" in result
            assert "1;" in result  # bold
            assert "2;" in result  # dim
            assert "4;" in result  # underline
            assert "3;" in result  # italic
            assert "5;" in result  # blink
            assert "34" in result  # blue
            assert "47" in result  # white bg
            assert "\033[0m" in result  # reset

    def test_colors_with_reset(self) -> None:
        """Test using 'reset' color values."""
        with patch("quack_core.interfaces.cli.utils.formatting.supports_color", return_value=True):
            # Reset foreground color
            result = colorize("Test text", fg="reset")
            assert result == "\033[39mTest text\033[0m"

            # Reset background color
            result = colorize("Test text", bg="reset")
            assert result == "\033[49mTest text\033[0m"

            # Reset both
            result = colorize("Test text", fg="reset", bg="reset")
            assert result == "\033[39;49mTest text\033[0m"


class TestPrintFunctions:
    """Tests for print_* functions."""

    def test_print_error(self) -> None:
        """Test print_error function."""
        with patch("builtins.print") as mock_print:
            with patch("quack_core.interfaces.cli.utils.formatting.colorize") as mock_colorize:
                mock_colorize.return_value = "COLORIZED ERROR"

                # Test basic error
                print_error("Test error")

                # Verify colorize was called with the right parameters
                mock_colorize.assert_called_once_with(
                    "Error: Test error", fg="red", bold=True
                )

                # Verify print was called with colorized text to stderr
                mock_print.assert_called_once_with("COLORIZED ERROR", file=sys.stderr)

        # Test with exit code
        with patch("builtins.print"):
            with patch("quack_core.interfaces.cli.utils.formatting.colorize"):
                with patch("sys.exit") as mock_exit:
                    print_error("Exit error", exit_code=2)

                    # Verify sys.exit was called with the right code
                    mock_exit.assert_called_once_with(2)

    def test_print_warning(self) -> None:
        """Test print_warning function."""
        with patch("builtins.print") as mock_print:
            with patch("quack_core.interfaces.cli.utils.formatting.colorize") as mock_colorize:
                mock_colorize.return_value = "COLORIZED WARNING"

                print_warning("Test warning")

                # Verify colorize was called with the right parameters
                mock_colorize.assert_called_once_with(
                    "Warning: Test warning", fg="yellow"
                )

                # Verify print was called with colorized text to stderr
                mock_print.assert_called_once_with("COLORIZED WARNING", file=sys.stderr)

    def test_print_success(self) -> None:
        """Test print_success function."""
        with patch("builtins.print") as mock_print:
            with patch("quack_core.interfaces.cli.utils.formatting.colorize") as mock_colorize:
                mock_colorize.return_value = "COLORIZED SUCCESS"

                print_success("Test success")

                # Verify colorize was called with the right parameters
                mock_colorize.assert_called_once_with("✓ Test success", fg="green")

                # Verify print was called with colorized text
                mock_print.assert_called_once_with("COLORIZED SUCCESS")

    def test_print_info(self) -> None:
        """Test print_info function."""
        with patch("builtins.print") as mock_print:
            with patch("quack_core.interfaces.cli.utils.formatting.colorize") as mock_colorize:
                mock_colorize.return_value = "COLORIZED INFO"

                print_info("Test info")

                # Verify colorize was called with the right parameters
                mock_colorize.assert_called_once_with("ℹ Test info", fg="blue")

                # Verify print was called with colorized text
                mock_print.assert_called_once_with("COLORIZED INFO")

    def test_print_debug(self) -> None:
        """Test print_debug function."""
        # Test when QUACK_DEBUG is not set
        with patch("builtins.print") as mock_print:
            with patch.dict("os.environ", {}, clear=True):
                print_debug("Test debug")

                # Should not print anything
                mock_print.assert_not_called()

        # Test when QUACK_DEBUG is set
        with patch("builtins.print") as mock_print:
            with patch("quack_core.interfaces.cli.utils.formatting.colorize") as mock_colorize:
                with patch.dict("os.environ", {"QUACK_DEBUG": "1"}):
                    mock_colorize.return_value = "COLORIZED DEBUG"

                    print_debug("Test debug")

                    # Verify colorize was called with the right parameters
                    mock_colorize.assert_called_once_with(
                        "DEBUG: Test debug", fg="magenta", dim=True
                    )

                    # Verify print was called with colorized text
                    mock_print.assert_called_once_with("COLORIZED DEBUG")


class TestTable:
    """Tests for table function."""

    def test_basic_table(self) -> None:
        """Test basic table formatting."""
        headers = ["Name", "Age", "City"]
        rows = [
            ["Alice", "30", "New York"],
            ["Bob", "25", "Los Angeles"],
            ["Charlie", "35", "Chicago"],
        ]

        result = table(headers, rows)

        # Verify table has the right format
        lines = result.strip().split("\n")
        assert len(lines) >= 7  # Header row + separator lines + data rows

        # Check that it contains a header separator
        assert "+" in lines[0]
        assert "+" in lines[2]

        # Check that it contains the headers
        assert "Name" in lines[1]
        assert "Age" in lines[1]
        assert "City" in lines[1]

        # Check that it contains the data
        assert "Alice" in result
        assert "Bob" in result
        assert "Charlie" in result
        assert "New York" in result
        assert "Los Angeles" in result
        assert "Chicago" in result

    def test_with_title_and_footer(self) -> None:
        """Test table with title and footer."""
        headers = ["Name", "Value"]
        rows = [["Test1", "100"], ["Test2", "200"]]

        result = table(headers, rows, title="Test Table", footer="Footer Notes")

        # Verify title and footer are included
        lines = result.strip().split("\n")

        # Title should be in the second line
        assert "Test Table" in lines[1]

        # Footer should be in the second-to-last line
        assert "Footer Notes" in lines[-2]

    def test_with_max_width(self) -> None:
        """Test table with max_width constraint."""
        headers = ["Column1", "Column2", "Column3"]
        rows = [
            ["Value1", "Value2", "Value3"],
            ["LongValue1", "LongValue2", "LongValue3"],
        ]

        # Test with small max_width
        with patch("quack_core.interfaces.cli.utils.formatting.get_terminal_size") as mock_get_size:
            mock_get_size.return_value = (40, 24)  # width, height

            result = table(headers, rows, max_width=20)

            # Verify the table is constrained
            for line in result.strip().split("\n"):
                assert len(line) <= 20

    def test_with_empty_rows(self) -> None:
        """Test table with empty rows."""
        headers = ["Name", "Value"]
        rows = []

        result = table(headers, rows)

        # Should return empty string
        assert result == ""

    def test_with_truncation(self) -> None:
        """Test that long cell values are truncated."""
        headers = ["Name", "Description"]
        rows = [["Test", "This is a very long description that should be truncated"]]

        with patch("quack_core.interfaces.cli.utils.formatting.get_terminal_size") as mock_get_size:
            mock_get_size.return_value = (30, 24)  # width, height

            with patch("quack_core.interfaces.cli.utils.formatting.truncate_text") as mock_truncate:
                mock_truncate.side_effect = (
                    lambda text, width: text[:width] + "..."
                    if len(text) > width
                    else text
                )

                result = table(headers, rows, max_width=30)

                # Verify truncate_text was called
                assert mock_truncate.called

                # Description should be truncated - check column contents
                # In a constrained table with max_width=30, the Description column
                # will have width for ~11 characters plus "..." based on our mock
                lines = result.strip().split("\n")
                description_cell = ""
                for line in lines:
                    if "Test" in line and "|" in line:
                        parts = line.split("|")
                        if len(parts) > 2:
                            description_cell = parts[2].strip()

                # Verify our mock truncation happened
                assert "..." in description_cell
                # Verify at least some of the description is visible
                assert "This is" in description_cell


class TestDictToTable:
    """Tests for dict_to_table function."""

    def test_basic_dict_to_table(self) -> None:
        """Test basic dictionary to table conversion."""
        data = {
            "name": "Test Project",
            "version": "1.0.0",
            "author": "Test Author",
        }

        with patch("quack_core.interfaces.cli.utils.formatting.table") as mock_table:
            mock_table.return_value = "MOCKED TABLE"

            result = dict_to_table(data)

            # Verify table was called with the right parameters
            args, kwargs = mock_table.call_args
            headers = args[0]
            rows = args[1]

            # Headers should be "Key" and "Value"
            assert headers == ["Key", "Value"]

            # Rows should contain the dictionary items
            assert ["name", "Test Project"] in rows
            assert ["version", "1.0.0"] in rows
            assert ["author", "Test Author"] in rows

            # Verify result is the mocked table
            assert result == "MOCKED TABLE"

    def test_with_title(self) -> None:
        """Test with title parameter."""
        data = {"key1": "value1", "key2": "value2"}

        with patch("quack_core.interfaces.cli.utils.formatting.table") as mock_table:
            dict_to_table(data, title="Test Title")

            # Verify title was passed to table
            _, kwargs = mock_table.call_args
            assert kwargs["title"] == "Test Title"

    def test_with_nested_data(self) -> None:
        """Test with nested data structures."""
        data = {
            "name": "Test Project",
            "config": {"debug": True, "verbose": False},
            "versions": [1, 2, 3],
        }

        with patch("quack_core.interfaces.cli.utils.formatting.table") as mock_table:
            dict_to_table(data)

            # Verify table was called with stringified nested structures
            args, _ = mock_table.call_args
            rows = args[1]

            # Find the row with the config key
            config_row = next(row for row in rows if row[0] == "config")
            versions_row = next(row for row in rows if row[0] == "versions")

            # The value should be the string representation
            assert config_row[1] == "{'debug': True, 'verbose': False}"
            assert versions_row[1] == "[1, 2, 3]"
