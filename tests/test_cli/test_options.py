# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_cli/test_options.py
# role: tests
# neighbors: __init__.py, mocks.py, test_bootstrap.py, test_config.py, test_context.py, test_error.py (+5 more)
# exports: TestResolveCliArgs
# git_branch: refactor/toolkitWorkflow
# git_commit: 82e6d2b
# === QV-LLM:END ===

"""
Tests for CLI option handling.

This module contains tests for the command line interface option parsing
and resolving functionality.
"""


from hypothesis import given
from hypothesis import strategies as st

from quack_core.interfaces.cli.utils.options import resolve_cli_args


class TestResolveCliArgs:
    """Tests for the resolve_cli_args function."""

    def test_empty_args(self):
        """Test that an empty args list returns empty dict."""
        result = resolve_cli_args([])
        assert result == {}

    def test_single_flag(self):
        """Test that a single flag is resolved correctly."""
        result = resolve_cli_args(["--verbose"])
        assert result == {"verbose": True}

    def test_multiple_flags(self):
        """Test that multiple flags are resolved correctly."""
        result = resolve_cli_args(["--verbose", "--debug"])
        assert result == {"verbose": True, "debug": True}

    def test_key_value_pair(self):
        """Test that a key-value pair is resolved correctly."""
        result = resolve_cli_args(["--config", "config.yaml"])
        assert result == {"config": "config.yaml"}

    def test_multiple_key_value_pairs(self):
        """Test that multiple key-value pairs are resolved correctly."""
        result = resolve_cli_args(
            ["--config", "config.yaml", "--log-level", "debug"]
        )
        assert result == {"config": "config.yaml", "log-level": "debug"}

    def test_mixed_flags_and_values(self):
        """Test that a mix of flags and key-value pairs is resolved correctly."""
        result = resolve_cli_args(
            ["--verbose", "--config", "config.yaml", "--debug"]
        )
        assert result == {
            "verbose": True,
            "config": "config.yaml",
            "debug": True,
        }

    def test_shorthand_flag(self):
        """Test that shorthand flags are resolved correctly."""
        result = resolve_cli_args(["-v"])
        assert result == {"v": True}

    def test_shorthand_key_value(self):
        """Test that shorthand key-value pairs are resolved correctly."""
        result = resolve_cli_args(["-c", "config.yaml"])
        assert result == {"c": "config.yaml"}

    def test_shorthand_condensed(self):
        """Test that condensed shorthand flags are resolved correctly."""
        result = resolve_cli_args(["-vd"])
        assert result == {"v": True, "d": True}

    def test_shorthand_condensed_with_value(self):
        """Test that condensed shorthand flags with a value are resolved."""
        result = resolve_cli_args(["-vdc", "config.yaml"])
        assert result == {"v": True, "d": True, "c": "config.yaml"}

    def test_equals_sign_value(self):
        """Test that values with equals signs are resolved correctly."""
        result = resolve_cli_args(["--config=config.yaml"])
        assert result == {"config": "config.yaml"}

    def test_equals_sign_multiple_values(self):
        """Test that multiple values with equals signs are resolved correctly."""
        result = resolve_cli_args(
            ["--config=config.yaml", "--log-level=debug"]
        )
        assert result == {"config": "config.yaml", "log-level": "debug"}

    def test_equals_sign_mixed(self):
        """Test that mixed equals signs and space separations are resolved."""
        result = resolve_cli_args(
            ["--config=config.yaml", "--log-level", "debug"]
        )
        assert result == {"config": "config.yaml", "log-level": "debug"}

    def test_positional_args(self):
        """Test that positional arguments are resolved correctly."""
        result = resolve_cli_args(["command", "--verbose"])
        assert result == {"": ["command"], "verbose": True}

    def test_multiple_positional_args(self):
        """Test that multiple positional arguments are resolved correctly."""
        result = resolve_cli_args(["command", "subcommand", "--verbose"])
        assert result == {"": ["command", "subcommand"], "verbose": True}

    def test_subcmd_args(self):
        """Test that sub-command arguments are resolved correctly."""
        result = resolve_cli_args(["command", "arg1", "--verbose"])
        assert result == {"": ["command", "arg1"], "verbose": True}

    def test_subcmd_args_with_values(self):
        """Test that sub-command arguments with values are resolved correctly."""
        result = resolve_cli_args(
            ["command", "arg1", "--verbose", "--config", "config.yaml"]
        )
        assert result == {
            "": ["command", "arg1"],
            "verbose": True,
            "config": "config.yaml",
        }

    def test_subcmd_with_dash(self):
        """Test that sub-commands with dashes are not treated as flags."""
        result = resolve_cli_args(["command", "-arg1"])
        assert result == {"": ["command", "-arg1"]}

    def test_subcmd_with_equals(self):
        """Test that sub-commands with equals are not treated as key-value pairs."""
        result = resolve_cli_args(["command", "arg1=value1"])
        assert result == {"": ["command", "arg1=value1"]}

    def test_special_dash_dash_separator(self):
        """Test handling of -- separator for positional arguments."""
        result = resolve_cli_args(["--verbose", "--", "--not-a-flag"])
        assert result == {"verbose": True, "": ["--not-a-flag"]}

    def test_special_dash_dash_with_values(self):
        """Test -- separator with mixed arguments."""
        result = resolve_cli_args(
            ["--config", "config.yaml", "--", "positional", "--not-a-flag"]
        )
        assert result == {
            "config": "config.yaml",
            "": ["positional", "--not-a-flag"],
        }

    def test_special_dash_dash_at_end(self):
        """Test that -- at the end is ignored."""
        result = resolve_cli_args(["--verbose", "--config", "config.yaml", "--"])
        assert result == {"verbose": True, "config": "config.yaml"}

    def test_special_dash_dash_empty(self):
        """Test that -- with nothing after it is ignored."""
        result = resolve_cli_args(["--verbose", "--"])
        assert result == {"verbose": True}

    def test_dash_value(self):
        """Test that a dash value is treated as a value, not a flag."""
        result = resolve_cli_args(["--config", "-"])
        assert result == {"config": "-"}

    def test_dash_value_multiple(self):
        """Test multiple parameters with dash values."""
        result = resolve_cli_args(["--config", "-", "--log-level", "-"])
        assert result == {"config": "-", "log-level": "-"}

    # Fix the problematic property-based test
    @given(
        st.dictionaries(
            st.sampled_from(["config", "log-level", "environment", "base-dir"]),
            # Avoid using '--' as a value since it's a special case
            st.text(min_size=1, max_size=20).filter(lambda x: x != "--"),
            min_size=0,
            max_size=4,
        )
    )
    def test_property_based_values(self, arg_dict: dict[str, str]) -> None:
        """Test property-based testing for arguments with values."""
        # Convert dictionary to CLI arguments
        args = []
        for key, value in arg_dict.items():
            args.extend([f"--{key}", value])

        result = resolve_cli_args(args)

        # Check that all arguments were processed correctly
        for key, value in arg_dict.items():
            # Handle the special case where value is '-'
            if value == '-':
                assert result.get(key) == '-'
            else:
                assert result.get(key) == value

    @given(
        st.lists(
            st.sampled_from(["verbose", "debug", "quiet", "help"]),
            min_size=0,
            max_size=4,
            unique=True,
        )
    )
    def test_property_based_flags(self, flags: list[str]) -> None:
        """Test property-based testing for flags."""
        # Convert list to CLI arguments
        args = [f"--{flag}" for flag in flags]

        result = resolve_cli_args(args)

        # Check that all flags were processed correctly
        for flag in flags:
            assert result.get(flag) is True

    @given(
        st.dictionaries(
            st.sampled_from(["a", "b", "c", "d"]),
            st.text(min_size=1, max_size=10),
            min_size=0,
            max_size=4,
        )
    )
    def test_property_based_shorthand(self, arg_dict: dict[str, str]) -> None:
        """Test property-based testing for shorthand arguments."""
        # Convert dictionary to CLI arguments
        args = []
        for key, value in arg_dict.items():
            args.extend([f"-{key}", value])

        result = resolve_cli_args(args)

        # Check that all arguments were processed correctly
        for key, value in arg_dict.items():
            assert result.get(key) == value

    @given(
        st.lists(
            st.sampled_from(["command", "subcommand", "arg1", "arg2"]),
            min_size=0,
            max_size=4,
            unique=True,
        )
    )
    def test_property_based_positional(self, args: list[str]) -> None:
        """Test property-based testing for positional arguments."""
        # Add a flag to ensure we're not just testing empty lists
        cli_args = args + ["--verbose"]

        result = resolve_cli_args(cli_args)

        # Check that positional arguments were processed correctly
        if args:
            assert "" in result
            assert result[""] == args
        assert result.get("verbose") is True

    def test_value_after_positional(self):
        """Test that values after positional arguments are handled correctly."""
        result = resolve_cli_args(["command", "--config", "config.yaml"])
        assert result == {"": ["command"], "config": "config.yaml"}

    def test_mixed_complex_case(self):
        """Test a complex mix of different argument types."""
        args = [
            "command",
            "subcommand",
            "--verbose",
            "-dc",
            "config.yaml",
            "--log-level=debug",
            "--",
            "--not-a-flag",
            "-not-shorthand",
        ]
        result = resolve_cli_args(args)
        expected = {
            "": ["command", "subcommand", "--not-a-flag", "-not-shorthand"],
            "verbose": True,
            "d": True,
            "c": "config.yaml",
            "log-level": "debug",
        }
        assert result == expected

    def test_handling_empty_value(self):
        """Test handling of empty values."""
        result = resolve_cli_args(["--config", ""])
        assert result == {"config": ""}

    def test_handling_spaces_in_value(self):
        """Test handling of values with spaces."""
        result = resolve_cli_args(["--message", "Hello World"])
        assert result == {"message": "Hello World"}

    def test_flag_at_end(self):
        """Test that a flag at the end is handled correctly."""
        result = resolve_cli_args(["--config", "config.yaml", "--verbose"])
        assert result == {"config": "config.yaml", "verbose": True}

    def test_missing_value(self):
        """Test that a missing value is handled gracefully."""
        # Flag at the end is interpreted as a flag, not a missing value
        result = resolve_cli_args(["--config"])
        assert result == {"config": True}
