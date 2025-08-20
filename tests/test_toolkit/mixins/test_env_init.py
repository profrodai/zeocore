# quack-core/tests/test_toolkit/mixins/test_env_init.py
"""
Tests for the ToolEnvInitializerMixin.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from quackcore.integrations.core import IntegrationResult
from quackcore.toolkit.mixins.env_init import ToolEnvInitializerMixin


class TestToolEnvInitializerMixin(unittest.TestCase):
    """
    Test cases for ToolEnvInitializerMixin using unittest.
    """

    @patch("importlib.import_module")
    def test_initialize_environment_success(self, mock_import: MagicMock) -> None:
        """
        Test that _initialize_environment correctly initializes the environment.
        """
        # Setup
        mixin = ToolEnvInitializerMixin()
        mock_module = MagicMock()
        mock_module.initialize.return_value = None
        mock_import.return_value = mock_module

        # Test
        result = mixin._initialize_environment("test_tool")

        # Assertions
        self.assertTrue(result.success)
        self.assertIn("Successfully initialized test_tool", result.message)
        mock_import.assert_called_once_with("test_tool")
        mock_module.initialize.assert_called_once()

    @patch("importlib.import_module")
    def test_initialize_environment_with_result(self, mock_import: MagicMock) -> None:
        """
        Test that _initialize_environment returns IntegrationResult from initialize.
        """
        # Setup
        mixin = ToolEnvInitializerMixin()
        mock_module = MagicMock()

        custom_result = IntegrationResult.success_result(
            message="Custom initialization message"
        )

        mock_module.initialize.return_value = custom_result
        mock_import.return_value = mock_module

        # Test
        result = mixin._initialize_environment("test_tool")

        # Assertions
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Custom initialization message")
        mock_import.assert_called_once_with("test_tool")
        mock_module.initialize.assert_called_once()

    @patch("importlib.import_module")
    def test_initialize_environment_no_initialize(self, mock_import: MagicMock) -> None:
        """
        Test that _initialize_environment handles modules without initialize.
        """
        # Setup
        mixin = ToolEnvInitializerMixin()
        mock_module = MagicMock(spec=[])  # No initialize method
        mock_import.return_value = mock_module

        # Test
        result = mixin._initialize_environment("test_tool")

        # Assertions
        self.assertTrue(result.success)
        self.assertIn("no initialize function found", result.message)
        mock_import.assert_called_once_with("test_tool")

    @patch("importlib.import_module")
    def test_initialize_environment_import_error(self, mock_import: MagicMock) -> None:
        """
        Test that _initialize_environment handles import errors.
        """
        # Setup
        mixin = ToolEnvInitializerMixin()
        mock_import.side_effect = ImportError("Module not found")

        # Test
        result = mixin._initialize_environment("test_tool")

        # Assertions
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Module not found")
        self.assertIn("Failed to import test_tool", result.message)
        mock_import.assert_called_once_with("test_tool")

    @patch("importlib.import_module")
    def test_initialize_environment_other_error(self, mock_import: MagicMock) -> None:
        """
        Test that _initialize_environment handles general exceptions during initialization.
        """
        # Setup
        mixin = ToolEnvInitializerMixin()
        mock_module = MagicMock()
        mock_module.initialize.side_effect = Exception("Initialization failed")
        mock_import.return_value = mock_module

        # Test
        result = mixin._initialize_environment("test_tool")

        # Assertions
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Initialization failed")
        self.assertIn("Error initializing test_tool", result.message)
        mock_import.assert_called_once_with("test_tool")
        mock_module.initialize.assert_called_once()


# Pytest-style tests

@pytest.fixture
def tool_env_initializer_mixin() -> ToolEnvInitializerMixin:
    """Fixture that creates a ToolEnvInitializerMixin."""
    return ToolEnvInitializerMixin()


class TestToolEnvInitializerMixinWithPytest:
    """
    Test cases for ToolEnvInitializerMixin using pytest fixtures.
    """

    @patch("importlib.import_module")
    def test_initialize_environment_success_pytest(self, mock_import: MagicMock, tool_env_initializer_mixin: ToolEnvInitializerMixin) -> None:
        """Test that _initialize_environment correctly initializes the environment."""
        # Setup
        mock_module = MagicMock()
        mock_module.initialize.return_value = None
        mock_import.return_value = mock_module

        # Test
        result = tool_env_initializer_mixin._initialize_environment("test_tool")

        # Assertions
        assert result.success
        assert "Successfully initialized test_tool" in result.message
        mock_import.assert_called_once_with("test_tool")
        mock_module.initialize.assert_called_once()

    @patch("importlib.import_module")
    def test_initialize_environment_with_result_pytest(self, mock_import: MagicMock, tool_env_initializer_mixin: ToolEnvInitializerMixin) -> None:
        """Test that _initialize_environment returns IntegrationResult from initialize."""
        # Setup
        mock_module = MagicMock()

        custom_result = IntegrationResult.success_result(
            message="Custom initialization message"
        )

        mock_module.initialize.return_value = custom_result
        mock_import.return_value = mock_module

        # Test
        result = tool_env_initializer_mixin._initialize_environment("test_tool")

        # Assertions
        assert result.success
        assert result.message == "Custom initialization message"
        mock_import.assert_called_once_with("test_tool")
        mock_module.initialize.assert_called_once()

    @patch("importlib.import_module")
    def test_initialize_environment_no_initialize_pytest(self, mock_import: MagicMock, tool_env_initializer_mixin: ToolEnvInitializerMixin) -> None:
        """Test that _initialize_environment handles modules without initialize."""
        # Setup
        mock_module = MagicMock(spec=[])  # No initialize method
        mock_import.return_value = mock_module

        # Test
        result = tool_env_initializer_mixin._initialize_environment("test_tool")

        # Assertions
        assert result.success
        assert "no initialize function found" in result.message
        mock_import.assert_called_once_with("test_tool")

    @patch("importlib.import_module")
    def test_initialize_environment_import_error_pytest(self, mock_import: MagicMock, tool_env_initializer_mixin: ToolEnvInitializerMixin) -> None:
        """Test that _initialize_environment handles import errors."""
        # Setup
        mock_import.side_effect = ImportError("Module not found")

        # Test
        result = tool_env_initializer_mixin._initialize_environment("test_tool")

        # Assertions
        assert not result.success
        assert result.error == "Module not found"
        assert "Failed to import test_tool" in result.message
        mock_import.assert_called_once_with("test_tool")

    @patch("importlib.import_module")
    def test_initialize_environment_other_error_pytest(self, mock_import: MagicMock, tool_env_initializer_mixin: ToolEnvInitializerMixin) -> None:
        """Test that _initialize_environment handles general exceptions during initialization."""
        # Setup
        mock_module = MagicMock()
        mock_module.initialize.side_effect = Exception("Initialization failed")
        mock_import.return_value = mock_module

        # Test
        result = tool_env_initializer_mixin._initialize_environment("test_tool")

        # Assertions
        assert not result.success
        assert result.error == "Initialization failed"
        assert "Error initializing test_tool" in result.message
        mock_import.assert_called_once_with("test_tool")
        mock_module.initialize.assert_called_once()
