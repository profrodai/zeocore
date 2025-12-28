# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_toolkit/mixins/test_integration_enabled.py
# role: tests
# neighbors: __init__.py, test_env_init.py, test_lifecycle.py, test_output_handler.py
# exports: MockIntegrationService, AnotherMockService, TestIntegrationEnabledMixin, TestIntegrationEnabledMixinWithPytest, integration_enabled_mixin
# git_branch: refactor/newHeaders
# git_commit: 72778e2
# === QV-LLM:END ===

"""
Tests for the IntegrationEnabledMixin.
"""

import unittest
from collections.abc import Generator
from typing import TypeVar
from unittest.mock import MagicMock, patch

import pytest

# Import the module directly to allow correct patching
import quack_core.integrations.core
from quack_core.integrations.core.base import BaseIntegrationService
from quack_core.toolkit.mixins.integration_enabled import IntegrationEnabledMixin


class MockIntegrationService(BaseIntegrationService):
    """
    Mock implementation of BaseIntegrationService for testing.
    """

    @property
    def name(self) -> str:
        return "mock_service"

    def __init__(self) -> None:
        super().__init__()
        self.initialized = False

    def initialize(self) -> None:
        self.initialized = True


class AnotherMockService(BaseIntegrationService):
    """
    Another mock implementation of BaseIntegrationService for testing.
    """

    @property
    def name(self) -> str:
        return "another_service"


T = TypeVar("T", bound=BaseIntegrationService)


class TestIntegrationEnabledMixin(unittest.TestCase):
    """
    Test cases for IntegrationEnabledMixin using unittest.
    """

    @patch.object(quack_core.integrations.core, "get_integration_service")
    def test_resolve_integration(self, mock_get_integration: MagicMock) -> None:
        """
        Test that resolve_integration correctly resolves the integration service.
        """

        # Setup
        class TestMixin(IntegrationEnabledMixin[MockIntegrationService]):
            pass

        mixin = TestMixin()
        mock_service = MockIntegrationService()
        mock_get_integration.return_value = mock_service

        # Test
        result = mixin.resolve_integration(MockIntegrationService)

        # Assertions
        self.assertEqual(result, mock_service)
        self.assertTrue(mock_service.initialized)
        mock_get_integration.assert_called_once_with(MockIntegrationService)

    @patch.object(quack_core.integrations.core, "get_integration_service")
    def test_resolve_integration_none(self, mock_get_integration: MagicMock) -> None:
        """
        Test that resolve_integration handles None return from get_integration_service.
        """

        # Setup
        class TestMixin(IntegrationEnabledMixin[MockIntegrationService]):
            pass

        mixin = TestMixin()
        mock_get_integration.return_value = None

        # Test
        result = mixin.resolve_integration(MockIntegrationService)

        # Assertions
        self.assertIsNone(result)
        mock_get_integration.assert_called_once_with(MockIntegrationService)

    @patch.object(quack_core.integrations.core, "get_integration_service")
    def test_resolve_integration_no_initialize(self,
                                               mock_get_integration: MagicMock) -> None:
        """
        Test that resolve_integration works with a service that doesn't have initialize.
        """

        # Setup
        class TestMixin(IntegrationEnabledMixin[AnotherMockService]):
            pass

        mixin = TestMixin()
        mock_service = AnotherMockService()
        mock_get_integration.return_value = mock_service

        # Test
        result = mixin.resolve_integration(AnotherMockService)

        # Assertions
        self.assertEqual(result, mock_service)
        mock_get_integration.assert_called_once_with(AnotherMockService)

    @patch.object(quack_core.integrations.core, "get_integration_service")
    def test_integration_property(self, mock_get_integration: MagicMock) -> None:
        """
        Test that the integration property works correctly.
        """

        # Setup
        class TestMixin(IntegrationEnabledMixin[MockIntegrationService]):
            pass

        mixin = TestMixin()
        mock_service = MockIntegrationService()
        mock_get_integration.return_value = mock_service

        # First call resolve_integration to properly set up the integration service
        mixin.resolve_integration(MockIntegrationService)

        # Reset mock to test if integration property uses the cached service
        mock_get_integration.reset_mock()

        # Test - access should use cached value
        result = mixin.integration

        # Assertions
        self.assertEqual(result, mock_service)
        mock_get_integration.assert_not_called()  # Should use cached value


@pytest.fixture
def integration_enabled_mixin() -> Generator[
    IntegrationEnabledMixin[MockIntegrationService], None, None]:
    """Fixture that creates an IntegrationEnabledMixin."""

    class TestMixin(IntegrationEnabledMixin[MockIntegrationService]):
        pass

    # Create the service instance before patching
    mock_service = MockIntegrationService()
    mock_service.initialize()  # Initialize it

    # Start a patch that will affect all code in this context
    with patch.object(quack_core.integrations.core, "get_integration_service",
                      return_value=mock_service) as mock_get_integration:
        # Initialize the mixin
        mixin = TestMixin()

        # Call resolve_integration to ensure the service is set
        mixin.resolve_integration(MockIntegrationService)

        yield mixin


class TestIntegrationEnabledMixinWithPytest:
    """
    Test cases for IntegrationEnabledMixin using pytest fixtures.
    """

    def test_integration_mixin_resolve(
            self,
            integration_enabled_mixin: IntegrationEnabledMixin[MockIntegrationService]
    ) -> None:
        """Test resolving an integration service."""
        # Patch the get_integration_service function before the test
        with patch.object(quack_core.integrations.core,
                          "get_integration_service") as mock_get_integration:
            # Setup
            mock_service = MockIntegrationService()
            mock_get_integration.return_value = mock_service

            # Test - calling resolve again
            result = integration_enabled_mixin.resolve_integration(
                MockIntegrationService)

            # Assertions
            assert result == mock_service
            assert mock_service.initialized
            mock_get_integration.assert_called_once_with(MockIntegrationService)

    def test_integration_mixin_property(
            self,
            integration_enabled_mixin: IntegrationEnabledMixin[MockIntegrationService]
    ) -> None:
        """Test the integration property."""
        # Get the service from the integration property
        result = integration_enabled_mixin.integration

        # Assertions - it should not be None because we called resolve_integration in the fixture
        assert result is not None
        assert isinstance(result, MockIntegrationService)
        assert result.initialized
