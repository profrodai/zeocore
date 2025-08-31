# quack-core/src/quack-core/cli/interaction.py
"""
User interaction utilities for CLI applications.

This module provides functions for interactive CLI features like
prompts, confirmations, and user input collection.
"""

import getpass
from collections.abc import Callable
from typing import TypeVar, overload

from quack_core.cli.formatting import print_error

T = TypeVar("T")  # Generic type for flexible typing


def confirm(
    prompt: str,
    default: bool = False,
    abort: bool = False,
    abort_message: str = "Operation aborted by user.",
) -> bool:
    """
    Ask for user confirmation.

    Args:
        prompt: The prompt to display
        default: Default response if user presses Enter
        abort: Whether to abort (sys.exit) on negative confirmation
        abort_message: Message to display if aborting

    Returns:
        True if confirmed, False otherwise
    """
    suffix = " [Y/n]" if default else " [y/N]"
    response = input(f"{prompt}{suffix} ").lower().strip()

    if not response:
        result = default
    else:
        result = response.startswith("y")

    if abort and not result:
        print_error(abort_message, exit_code=1)

    return result


@overload
def ask(
    prompt: str,
    default: None = None,
    validate: Callable[[str], bool] | None = None,
    hide_input: bool = False,
    required: bool = False,
) -> str: ...


@overload
def ask(
    prompt: str,
    default: str,
    validate: Callable[[str], bool] | None = None,
    hide_input: bool = False,
    required: bool = False,
) -> str: ...


def ask(
    prompt: str,
    default: str | None = None,
    validate: Callable[[str], bool] | None = None,
    hide_input: bool = False,
    required: bool = False,
) -> str:
    """
    Ask the user for input with optional validation.

    Args:
        prompt: The prompt to display
        default: Default value if user presses Enter
        validate: Optional validation function that returns True for valid input
        hide_input: Whether to hide user input (for passwords)
        required: Whether input is required (cannot be empty)

    Returns:
        User input
    """
    suffix = f" [{default}]" if default is not None else ""
    prompt_str = f"{prompt}{suffix}: "

    while True:
        value = getpass.getpass(prompt_str) if hide_input else input(prompt_str)

        if not value:
            if default is not None:
                return default
            elif not required:
                return ""
            else:
                print_error("Input is required. Please try again.")
                continue

        if validate is not None and not validate(value):
            print_error("Invalid input. Please try again.")
            continue

        return value


def ask_choice(
    prompt: str,
    choices: list[str],
    default: int | None = None,
    allow_custom: bool = False,
) -> str:
    """
    Ask the user to select from a list of choices.

    Args:
        prompt: The prompt to display
        choices: List of choices to present
        default: Default choice index if user presses Enter
        allow_custom: Whether to allow custom input not in choices

    Returns:
        Selected choice
    """
    # Display choices
    print(f"{prompt}")
    for i, choice in enumerate(choices, 1):
        default_note = " (default)" if default == i - 1 else ""
        print(f"{i}. {choice}{default_note}")

    if allow_custom:
        print(f"{len(choices) + 1}. Enter custom value")

    while True:
        default_str = f" [{default + 1}]" if default is not None else ""
        selection = input(f"Enter selection{default_str}: ").strip()

        if not selection and default is not None:
            return choices[default]

        try:
            index = int(selection) - 1
            if 0 <= index < len(choices):
                return choices[index]
            elif allow_custom and index == len(choices):
                return input("Enter custom value: ").strip()
            else:
                print_error(
                    f"Please enter a number between 1 "
                    f"and {len(choices) + (1 if allow_custom else 0)}"
                )
        except ValueError:
            if allow_custom and selection:
                return selection
            print_error("Please enter a valid number")


def with_spinner(
    desc: str = "Processing",
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to show a spinner while a function is running.

    Args:
        desc: Description to show next to the spinner

    Returns:
        A decorator that wraps a function and displays a spinner during its execution
    """
    import itertools
    import sys
    import threading
    import time
    from functools import wraps

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: object, **kwargs: object) -> T:
            spinner = itertools.cycle(["-", "\\", "|", "/"])
            spinning = True

            def spin() -> None:
                while spinning:
                    sys.stdout.write(f"\r{desc} {next(spinner)}")
                    sys.stdout.flush()
                    time.sleep(0.1)
                sys.stdout.write("\r" + " " * (len(desc) + 2) + "\r")
                sys.stdout.flush()

            thread = threading.Thread(target=spin)
            thread.daemon = True
            thread.start()

            try:
                return func(*args, **kwargs)
            finally:
                spinning = False
                thread.join()

        return wrapper

    return decorator
