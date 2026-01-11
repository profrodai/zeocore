# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/core/test_get_service.py
# role: tests
# neighbors: __init__.py, test_protocol_inheritance.py, test_protocols.py, test_registry.py, test_registry_discovery.py, test_results.py
# exports: MockDriveService, MockMailService, TestGetIntegrationService
# git_branch: feat/9-make-setup-work
# git_commit: 8234fdcd
# === QV-LLM:END ===

"""
Tests for the get_integration_service function.
"""

import unittest
from unittest.mock import patch

from quack_core.integrations.core import get_integration_service
from quack_core.integrations.core.base import BaseIntegrationService


class MockDriveService(BaseIntegrationService):
    """
    Mock implementation of a Drive service for testing.
    """

    @property
    def name(self) -> str:
        return "MockDriveService"


class MockMailService(BaseIntegrationService):
    """
    Mock implementation of a Mail service for testing.
    """

    @property
    def name(self) -> str:
        return "MockMailService"


class TestGetIntegrationService(unittest.TestCase):
    """
    Test cases for get_integration_service.
    """

    @patch("quack_core.integrations.core.registry")
    def test_get_integration_service_found(self, mock_registry):
        """
        Test that get_integration_service returns the correct service when found.
        """
        # Setup mock registry
        mock_drive_service = MockDriveService()
        mock_registry.get_integration_by_type.return_value = [mock_drive_service]

        # Call the function
        result = get_integration_service(MockDriveService)

        # Assertions
        self.assertEqual(result, mock_drive_service)
        mock_registry.get_integration_by_type.assert_called_once_with(MockDriveService)

    @patch("quack_core.integrations.core.registry")
    def test_get_integration_service_not_found(self, mock_registry):
        """
        Test that get_integration_service returns None when no matching service is found.
        """
        # Setup mock registry
        mock_registry.get_integration_by_type.return_value = []

        # Call the function
        result = get_integration_service(MockDriveService)

        # Assertions
        self.assertIsNone(result)
        mock_registry.get_integration_by_type.assert_called_once_with(MockDriveService)

    @patch("quack_core.integrations.core.registry")
    def test_get_integration_service_returns_first_match(self, mock_registry):
        """
        Test that get_integration_service returns the first matching service when multiple are found.
        """
        # Setup mock registry with multiple services
        class DriveService1(MockDriveService):
            @property
            def name(self) -> str:
                return "DriveService1"

        class DriveService2(MockDriveService):
            @property
            def name(self) -> str:
                return "DriveService2"

        mock_drive_service1 = DriveService1()
        mock_drive_service2 = DriveService2()

        mock_registry.get_integration_by_type.return_value = [
            mock_drive_service1,
            mock_drive_service2
        ]

        # Call the function
        result = get_integration_service(MockDriveService)

        # Assertions
        self.assertEqual(result, mock_drive_service1)
        mock_registry.get_integration_by_type.assert_called_once_with(MockDriveService)

    @patch("quack_core.integrations.core.registry")
    def test_get_integration_service_type_mismatch(self, mock_registry):
        """
        Test that get_integration_service correctly filters by type.
        """
        # Setup mock registry
        mock_mail_service = MockMailService()
        mock_registry.get_integration_by_type.return_value = [mock_mail_service]

        # Call the function, but ask for a different type
        # In a real scenario, the registry would filter this, but we're mocking it
        # So we're testing the additional type check in get_integration_service
        mock_registry.get_integration_by_type.return_value = [mock_mail_service]
        mock_mail_service.__class__ = MockMailService  # Ensure isinstance check works

        # Call the function
        result = get_integration_service(MockDriveService)

        # Assertions
        self.assertIsNone(result)
        mock_registry.get_integration_by_type.assert_called_once_with(MockDriveService)


if __name__ == "__main__":
    unittest.main()
