# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_cli/test_interaction.py
# role: tests
# neighbors: __init__.py, mocks.py, test_bootstrap.py, test_config.py, test_context.py, test_error.py (+5 more)
# exports: TestConfirm, TestAsk, TestAskChoice, TestWithSpinner
# git_branch: refactor/toolkitWorkflow
# git_commit: 07a259e
# === QV-LLM:END ===

"""
Tests for the CLI interaction module.
"""

import time
from unittest.mock import patch

from quack_core.interfaces.cli.utils.interaction import confirm, ask, ask_choice, \
    with_spinner


class TestConfirm:
    """Tests for confirm function."""

    def test_yes_response(self) -> None:
        """Test with 'yes' response."""
        with patch("builtins.input", return_value="y"):
            result = confirm("Continue?")
            assert result is True

        with patch("builtins.input", return_value="Y"):
            result = confirm("Continue?")
            assert result is True

        with patch("builtins.input", return_value="yes"):
            result = confirm("Continue?")
            assert result is True

    def test_no_response(self) -> None:
        """Test with 'no' response."""
        with patch("builtins.input", return_value="n"):
            result = confirm("Continue?")
            assert result is False

        with patch("builtins.input", return_value="N"):
            result = confirm("Continue?")
            assert result is False

        with patch("builtins.input", return_value="no"):
            result = confirm("Continue?")
            assert result is False

    def test_default_true(self) -> None:
        """Test with default=True."""
        with patch("builtins.input", return_value=""):
            result = confirm("Continue?", default=True)
            assert result is True

    def test_default_false(self) -> None:
        """Test with default=False."""
        with patch("builtins.input", return_value=""):
            result = confirm("Continue?", default=False)
            assert result is False

    def test_prompt_format(self) -> None:
        """Test the format of the prompt."""

        # Define a function to capture the prompt
        def get_prompt(default):
            prompts = []

            def mock_input(prompt):
                prompts.append(prompt)
                return ""

            with patch("builtins.input", mock_input):
                confirm("Continue?", default=default)
                return prompts[0]

        # Test with default=True
        prompt = get_prompt(True)
        assert prompt == "Continue? [Y/n] "

        # Test with default=False
        prompt = get_prompt(False)
        assert prompt == "Continue? [y/N] "

    def test_abort(self) -> None:
        """Test aborting on negative confirmation."""
        # We need to patch the import inside the interaction module
        with patch("builtins.input", return_value="n"):
            # Patch the print_error directly in the module where it's used
            with patch("quack_core.interfaces.cli.utils.interaction.print_error") as mock_print_error:
                with patch("sys.exit") as mock_exit:
                    confirm("Continue?", abort=True, abort_message="Aborted!")

                    # Verify print_error was called and sys.exit
                    mock_print_error.assert_called_once_with("Aborted!", exit_code=1)
                    mock_exit.assert_not_called()  # It's called by print_error

        # Also check that sys.exit is not called for positive confirmation
        with patch("builtins.input", return_value="y"):
            with patch("quack_core.interfaces.cli.utils.interaction.print_error") as mock_print_error:
                with patch("sys.exit") as mock_exit:
                    confirm("Continue?", abort=True, abort_message="Aborted!")

                    # Verify print_error was not called
                    mock_print_error.assert_not_called()
                    mock_exit.assert_not_called()


class TestAsk:
    """Tests for ask function."""

    def test_basic_input(self) -> None:
        """Test basic input collection."""
        with patch("builtins.input", return_value="test input"):
            result = ask("Enter value")
            assert result == "test input"

    def test_with_default(self) -> None:
        """Test with default value."""
        with patch("builtins.input", return_value=""):
            result = ask("Enter value", default="default value")
            assert result == "default value"

        with patch("builtins.input", return_value="custom input"):
            result = ask("Enter value", default="default value")
            assert result == "custom input"

    def test_with_validation(self) -> None:
        """Test with validation function."""

        # Define a validation function
        def is_numeric(value):
            return value.isdigit()

        # Test with valid input
        with patch("builtins.input", return_value="123"):
            result = ask("Enter number", validate=is_numeric)
            assert result == "123"

        # Test with invalid input followed by valid input
        with patch("builtins.input", side_effect=["abc", "123"]):
            with patch("quack_core.interfaces.cli.utils.interaction.print_error") as mock_print_error:
                result = ask("Enter number", validate=is_numeric)

                assert result == "123"
                mock_print_error.assert_called_once()

    def test_with_hidden_input(self) -> None:
        """Test with hidden input (passwords)."""
        with patch("getpass.getpass", return_value="secret"):
            result = ask("Enter password", hide_input=True)
            assert result == "secret"

    def test_required_input(self) -> None:
        """Test with required input."""
        # Test with empty input followed by valid input
        with patch("builtins.input", side_effect=["", "valid input"]):
            with patch("quack_core.interfaces.cli.utils.interaction.print_error") as mock_print_error:
                result = ask("Enter value", required=True)

                assert result == "valid input"
                mock_print_error.assert_called_once()

        # Test with default value and required=True, empty input
        with patch("builtins.input", return_value=""):
            result = ask("Enter value", default="default value", required=True)
            assert result == "default value"

        # Test with not required (empty input is valid)
        with patch("builtins.input", return_value=""):
            result = ask("Enter value", required=False)
            assert result == ""

    def test_prompt_format(self) -> None:
        """Test the format of the prompt."""

        # Define a function to capture the prompt
        def get_prompt(default=None):
            prompts = []

            def mock_input(prompt):
                prompts.append(prompt)
                return ""

            with patch("builtins.input", mock_input):
                ask("Enter value", default=default)
                return prompts[0]

        # Test with no default
        prompt = get_prompt()
        assert prompt == "Enter value: "

        # Test with default
        prompt = get_prompt("default")
        assert prompt == "Enter value [default]: "


class TestAskChoice:
    """Tests for ask_choice function."""

    def test_basic_choice(self) -> None:
        """Test basic choice selection."""
        choices = ["option1", "option2", "option3"]

        # Select the first option
        with patch("builtins.input", return_value="1"):
            result = ask_choice("Select option", choices)
            assert result == "option1"

        # Select the second option
        with patch("builtins.input", return_value="2"):
            result = ask_choice("Select option", choices)
            assert result == "option2"

    def test_with_default(self) -> None:
        """Test with default choice."""
        choices = ["option1", "option2", "option3"]

        # Select the default option (press Enter)
        with patch("builtins.input", return_value=""):
            result = ask_choice("Select option", choices, default=1)
            assert result == "option2"  # Default is index 1

        # Override the default
        with patch("builtins.input", return_value="3"):
            result = ask_choice("Select option", choices, default=0)
            assert result == "option3"

    def test_with_custom_value(self) -> None:
        """Test with custom value option."""
        choices = ["option1", "option2"]

        # Select the custom option and enter a value
        with patch("builtins.input", side_effect=["3", "custom value"]):
            result = ask_choice("Select option", choices, allow_custom=True)
            assert result == "custom value"

        # Enter a custom value directly
        with patch("builtins.input", return_value="custom directly"):
            result = ask_choice("Select option", choices, allow_custom=True)
            assert result == "custom directly"

    def test_invalid_input(self) -> None:
        """Test handling invalid input."""
        choices = ["option1", "option2"]

        # Invalid input (out of range) followed by valid input
        with patch("builtins.input", side_effect=["5", "1"]):
            with patch("quack_core.interfaces.cli.utils.interaction.print_error") as mock_print_error:
                result = ask_choice("Select option", choices)

                assert result == "option1"
                mock_print_error.assert_called_once()

        # Non-numeric input followed by valid input
        with patch("builtins.input", side_effect=["abc", "2"]):
            with patch("quack_core.interfaces.cli.utils.interaction.print_error") as mock_print_error:
                result = ask_choice("Select option", choices)

                assert result == "option2"
                mock_print_error.assert_called_once()

    def test_display_format(self) -> None:
        """Test the display format of choices."""
        choices = ["option1", "option2"]

        # Capture all print calls
        print_buffer = []

        with patch("builtins.print") as mock_print:
            mock_print.side_effect = lambda *args: print_buffer.append(
                " ".join(str(arg) for arg in args)
            )

            with patch("builtins.input", return_value="1"):
                ask_choice("Select option", choices)

                # Verify the prompt and choices were printed correctly
                assert "Select option" in print_buffer[0]
                assert "1. option1" in print_buffer[1]
                assert "2. option2" in print_buffer[2]

        # Test with default value
        print_buffer = []

        with patch("builtins.print") as mock_print:
            mock_print.side_effect = lambda *args: print_buffer.append(
                " ".join(str(arg) for arg in args)
            )

            with patch("builtins.input", return_value=""):
                ask_choice("Select option", choices, default=0)

                # Verify default is indicated
                assert "1. option1 (default)" in print_buffer[1]

        # Test with custom option
        print_buffer = []

        with patch("builtins.print") as mock_print:
            mock_print.side_effect = lambda *args: print_buffer.append(
                " ".join(str(arg) for arg in args)
            )

            with patch("builtins.input", side_effect=["3", "custom"]):
                ask_choice("Select option", choices, allow_custom=True)

                # Verify custom option is shown
                assert f"{len(choices) + 1}. Enter custom value" in print_buffer[3]


class TestWithSpinner:
    """Tests for with_spinner decorator."""

    def test_basic_usage(self) -> None:
        """Test basic usage of the spinner decorator."""

        # Define a function with the decorator
        @with_spinner()
        def slow_function():
            return "result"

        # Mock necessary functions
        with patch("sys.stdout.write") as mock_write:
            with patch("sys.stdout.flush"):
                with patch("time.sleep"):
                    # Call the function
                    result = slow_function()

                    # Verify the spinner was displayed and the function executed
                    assert result == "result"
                    mock_write.assert_called()  # Should write the spinner

    def test_with_long_running_function(self) -> None:
        """Test with a long-running function."""

        # Define a function that takes a bit of time
        @with_spinner(desc="Working")
        def long_function():
            # Simulate work
            time.sleep(0.2)
            return "done"

        # Capture actual behavior using a real thread
        # This is a more comprehensive test than just mocking
        with patch("sys.stdout.write") as mock_write:
            with patch("sys.stdout.flush"):
                # Call the function
                result = long_function()

                # Verify the function executed and spinner was displayed
                assert result == "done"
                assert mock_write.call_count > 1  # Should write multiple spinner frames

    def test_spinner_cleanup(self) -> None:
        """Test that spinner is cleaned up after function execution."""

        @with_spinner()
        def normal_function():
            return "normal result"

        @with_spinner()
        def error_function():
            raise ValueError("Test error")

        # Test normal function
        with patch("sys.stdout.write") as mock_write:
            with patch("sys.stdout.flush"):
                with patch("time.sleep"):
                    normal_function()

                    # Verify spinner was cleared at the end
                    # Last call should include whitespace to clear the spinner
                    assert " " in mock_write.call_args_list[-1][0][0]

        # Test function that raises exception
        with patch("sys.stdout.write") as mock_write:
            with patch("sys.stdout.flush"):
                with patch("time.sleep"):
                    try:
                        error_function()
                    except ValueError:
                        pass

                    # Verify spinner was still cleared even with exception
                    assert " " in mock_write.call_args_list[-1][0][0]

    def test_custom_description(self) -> None:
        """Test with custom spinner description."""

        @with_spinner(desc="Custom Processing")
        def custom_function():
            return "custom result"

        # Capture the spinner text
        with patch("sys.stdout.write") as mock_write:
            with patch("sys.stdout.flush"):
                with patch("time.sleep"):
                    custom_function()

                    # Verify the custom description was used
                    first_write = mock_write.call_args_list[0][0][0]
                    assert "Custom Processing" in first_write
