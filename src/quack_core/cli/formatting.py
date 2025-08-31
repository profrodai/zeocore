# quack-core/src/quack-core/cli/formatting.py
"""
Text formatting utilities for CLI applications.

This module provides functions for formatting text output in CLI applications,
including color formatting, table rendering, and general message formatting.
"""

import sys
from collections.abc import Mapping
from enum import Enum
from typing import Literal

from quack_core.cli.terminal import get_terminal_size, supports_color, truncate_text


class Color(str, Enum):
    """ANSI color codes."""

    # Foreground colors
    BLACK = "30"
    RED = "31"
    GREEN = "32"
    YELLOW = "33"
    BLUE = "34"
    MAGENTA = "35"
    CYAN = "36"
    WHITE = "37"
    RESET = "39"

    # Background colors
    BG_BLACK = "40"
    BG_RED = "41"
    BG_GREEN = "42"
    BG_YELLOW = "43"
    BG_BLUE = "44"
    BG_MAGENTA = "45"
    BG_CYAN = "46"
    BG_WHITE = "47"
    BG_RESET = "49"

    # Styles
    BOLD = "1"
    DIM = "2"
    ITALIC = "3"
    UNDERLINE = "4"
    BLINK = "5"
    REVERSE = "7"
    STRIKE = "9"

    # Reset all
    RESET_ALL = "0"


def colorize(
    text: str,
    fg: Literal[
        "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white", "reset"
    ]
    | None = None,
    bg: Literal[
        "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white", "reset"
    ]
    | None = None,
    bold: bool = False,
    dim: bool = False,
    underline: bool = False,
    italic: bool = False,
    blink: bool = False,
    force: bool = False,
) -> str:
    """
    Add ANSI color and style to text.

    Args:
        text: The text to colorize
        fg: Foreground color
        bg: Background color
        bold: Whether to make the text bold
        dim: Whether to make the text dim
        underline: Whether to underline the text
        italic: Whether to italicize the text
        blink: Whether to make the text blink
        force: Whether to force color even if the terminal doesn't support it

    Returns:
        Colorized text
    """
    if not (force or supports_color()):
        return text

    fg_codes = {
        "black": Color.BLACK,
        "red": Color.RED,
        "green": Color.GREEN,
        "yellow": Color.YELLOW,
        "blue": Color.BLUE,
        "magenta": Color.MAGENTA,
        "cyan": Color.CYAN,
        "white": Color.WHITE,
        "reset": Color.RESET,
    }

    bg_codes = {
        "black": Color.BG_BLACK,
        "red": Color.BG_RED,
        "green": Color.BG_GREEN,
        "yellow": Color.BG_YELLOW,
        "blue": Color.BG_BLUE,
        "magenta": Color.BG_MAGENTA,
        "cyan": Color.BG_CYAN,
        "white": Color.BG_WHITE,
        "reset": Color.BG_RESET,
    }

    codes: list[str] = []

    if bold:
        codes.append(Color.BOLD)
    if dim:
        codes.append(Color.DIM)
    if underline:
        codes.append(Color.UNDERLINE)
    if italic:
        codes.append(Color.ITALIC)
    if blink:
        codes.append(Color.BLINK)
    if fg:
        codes.append(fg_codes[fg])
    if bg:
        codes.append(bg_codes[bg])

    if not codes:
        return text

    return f"\033[{';'.join(codes)}m{text}\033[0m"


def print_error(message: str, *, exit_code: int | None = None) -> None:
    """
    Print an error message to stderr.

    Args:
        message: The error message
        exit_code: If provided, exit with this code after printing
    """
    print(colorize(f"Error: {message}", fg="red", bold=True), file=sys.stderr)

    if exit_code is not None:
        sys.exit(exit_code)


def print_warning(message: str) -> None:
    """
    Print a warning message to stderr.

    Args:
        message: The warning message
    """
    print(colorize(f"Warning: {message}", fg="yellow"), file=sys.stderr)


def print_success(message: str) -> None:
    """
    Print a success message.

    Args:
        message: The success message
    """
    print(colorize(f"✓ {message}", fg="green"))


def print_info(message: str) -> None:
    """
    Print an informational message.

    Args:
        message: The informational message
    """
    print(colorize(f"ℹ {message}", fg="blue"))


def print_debug(message: str) -> None:
    """
    Print a debug message.

    Only prints if the QUACK_DEBUG environment variable is set.

    Args:
        message: The debug message
    """
    import os

    if os.environ.get("QUACK_DEBUG") == "1":
        print(colorize(f"DEBUG: {message}", fg="magenta", dim=True))


def table(
    headers: list[str],
    rows: list[list[str]],
    max_width: int | None = None,
    title: str | None = None,
    footer: str | None = None,
) -> str:
    """
    Format data as a text table.

    Args:
        headers: Table headers
        rows: Table rows
        max_width: Maximum width of the table in characters
        title: Optional title for the table
        footer: Optional footer for the table

    Returns:
        Formatted table as a string
    """
    if not rows:
        return ""

    all_rows = [headers] + rows

    # Get terminal width if max_width is not specified or too large
    term_width, _ = get_terminal_size()
    if max_width is None or max_width > term_width:
        max_width = term_width

    # Set minimum column width to ensure cell content is visible
    min_column_width = 5

    # Calculate initial column widths based on content
    col_widths = [
        max(min_column_width, max(len(str(row[i])) for row in all_rows))
        for i in range(len(headers))
    ]

    # Calculate the space required for borders and padding
    # Each column has '| ' at start and ' ' at end
    padding_per_column = 3  # '| ' = 2, ' ' = 1
    border_chars = len(headers) + 1  # One '+' between each column and at start/end

    # Calculate total width including borders and padding
    total_width = (
        sum(col_widths)
        + (padding_per_column * len(headers))
        - len(headers)
        + border_chars
    )

    # Adjust column widths if the table exceeds max_width
    if max_width and total_width > max_width:
        # Calculate available space for content
        available_width = max_width - (
            border_chars + (padding_per_column * len(headers)) - len(headers)
        )

        # Calculate how much space we need to trim
        excess = sum(col_widths) - available_width

        if excess > 0:
            # Get columns that can be shrunk (width > min_column_width)
            shrinkable_cols = [
                (i, w) for i, w in enumerate(col_widths) if w > min_column_width
            ]
            shrinkable_width = sum(w for _, w in shrinkable_cols) - (
                len(shrinkable_cols) * min_column_width
            )

            # If we can't shrink enough, set all columns to minimum width
            if shrinkable_width < excess:
                # Prioritize the columns - keep the first column wider if possible
                col_widths = [min_column_width] * len(col_widths)

                # If we have extra space, allocate more to important columns
                if available_width > len(col_widths) * min_column_width:
                    extra = available_width - (len(col_widths) * min_column_width)
                    # Give extra space to the first column, then distribute rest evenly
                    if extra > 0:
                        first_extra = min(
                            extra, 7
                        )  # Give up to 7 extra chars to first column
                        col_widths[0] += first_extra
                        extra -= first_extra

                        # Distribute remaining extra space
                        if extra > 0 and len(col_widths) > 1:
                            per_col = extra // (len(col_widths) - 1)
                            for i in range(1, len(col_widths)):
                                col_widths[i] += per_col
            else:
                # We can shrink enough - distribute the reduction proportionally
                for i, width in enumerate(col_widths):
                    if width > min_column_width:
                        # Calculate the proportion of this column to the total shrinkable width
                        shrinkable = width - min_column_width
                        reduction = int((shrinkable / shrinkable_width) * excess)

                        # Ensure we don't reduce below minimum
                        col_widths[i] = max(min_column_width, width - reduction)

    # Create the separator line
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

    # Double-check that the separator fits within max_width
    if max_width and len(separator) > max_width:
        # If we still exceed max_width, make one final adjustment
        available_width = max_width - (
            border_chars + len(headers) * 2
        )  # absolute minimum
        col_widths = [max(1, available_width // len(headers))] * len(headers)
        separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

    result: list[str] = []

    if title:
        # Make sure title fits within the separator length
        title_max_width = len(separator) - 4
        if len(title) > title_max_width:
            title = truncate_text(title, title_max_width)

        title_line = f"| {title.center(len(separator) - 4)} |"
        result.extend([separator, title_line, separator])
    else:
        result.append(separator)

    # Create header row with complete header content
    header_row = "|"
    for h, w in zip(headers, col_widths, strict=True):
        # Make sure each header is visible by using a shorter truncation if needed
        header_text = truncate_text(h, w)
        header_row += f" {header_text.ljust(w)} |"

    result.append(header_row)
    result.append(separator)

    # Create data rows
    for row in rows:
        str_row = [str(cell) if cell is not None else "" for cell in row]
        while len(str_row) < len(col_widths):
            str_row.append("")

        data_row = "|"
        for cell, w in zip(str_row, col_widths, strict=True):
            cell_text = truncate_text(cell, w)
            data_row += f" {cell_text.ljust(w)} |"

        result.append(data_row)

    result.append(separator)

    if footer:
        # Make sure footer fits within the separator length
        footer_max_width = len(separator) - 4
        if len(footer) > footer_max_width:
            footer = truncate_text(footer, footer_max_width)

        footer_line = f"| {footer.ljust(len(separator) - 4)} |"
        result.extend([footer_line, separator])

    return "\n".join(result)


def dict_to_table(data: Mapping[str, object], title: str | None = None) -> str:
    """
    Convert a dictionary to a formatted table.

    Args:
        data: Dictionary to convert
        title: Optional title for the table

    Returns:
        Formatted table as a string
    """
    headers = ["Key", "Value"]
    rows = [[str(k), str(v)] for k, v in data.items()]
    return table(headers, rows, title=title)
