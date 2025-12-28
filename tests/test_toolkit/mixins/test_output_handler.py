# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_toolkit/mixins/test_output_handler.py
# role: tests
# neighbors: __init__.py, test_env_init.py, test_integration_enabled.py, test_lifecycle.py
# exports: CustomOutputFormatMixin, TestOutputFormatMixin, TestOutputFormatMixinWithPytest, output_format_mixin, custom_output_format_mixin
# git_branch: refactor/newHeaders
# git_commit: 175956c
# === QV-LLM:END ===

"""
Tests for the OutputFormatMixin.
"""

import unittest

import pytest

from quack_core.toolkit.mixins.output_handler import OutputFormatMixin


class CustomOutputFormatMixin(OutputFormatMixin):
    """Custom implementation of OutputFormatMixin for testing."""

    def _get_output_extension(self) -> str:
        return ".csv"


class TestOutputFormatMixin(unittest.TestCase):
    """
    Test cases for OutputFormatMixin using unittest.
    """

    def test_get_output_extension(self) -> None:
        """
        Test that _get_output_extension returns the default extension.
        """
        mixin = OutputFormatMixin()
        self.assertEqual(mixin._get_output_extension(), ".json")

    def test_get_output_writer(self) -> None:
        """
        Test that get_output_writer returns None by default.
        """
        mixin = OutputFormatMixin()
        self.assertIsNone(mixin.get_output_writer())

    def test_custom_output_extension(self) -> None:
        """
        Test that a subclass can override _get_output_extension.
        """
        mixin = CustomOutputFormatMixin()
        self.assertEqual(mixin._get_output_extension(), ".csv")


# Pytest-style tests

@pytest.fixture
def output_format_mixin() -> OutputFormatMixin:
    """Fixture that creates an OutputFormatMixin."""
    return OutputFormatMixin()


@pytest.fixture
def custom_output_format_mixin() -> CustomOutputFormatMixin:
    """Fixture that creates a CustomOutputFormatMixin."""
    return CustomOutputFormatMixin()


class TestOutputFormatMixinWithPytest:
    """
    Test cases for OutputFormatMixin using pytest fixtures.
    """

    def test_output_format_default_extension(self,
                                             output_format_mixin: OutputFormatMixin) -> None:
        """Test the default extension from OutputFormatMixin."""
        assert output_format_mixin._get_output_extension() == ".json"

    def test_output_format_custom_extension(self,
                                            custom_output_format_mixin: CustomOutputFormatMixin) -> None:
        """Test a custom extension from a subclass of OutputFormatMixin."""
        assert custom_output_format_mixin._get_output_extension() == ".csv"

    def test_output_format_writer(self, output_format_mixin: OutputFormatMixin) -> None:
        """Test that get_output_writer returns None by default."""
        assert output_format_mixin.get_output_writer() is None
