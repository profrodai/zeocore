"""
Google Mail integration for zeo_core.

This module provides integration with Gmail, allowing for email
retrieval, listing, and management through a consistent interface.
"""

from zeo_core.integrations.core.protocols import IntegrationProtocol
from zeo_core.integrations.google.mail.service import GoogleMailService

__all__ = [
    "GoogleMailService",
    "create_integration",
]


def create_integration() -> IntegrationProtocol:
    """
    Create and configure a Google Mail integration.

    This function is used as an entry point for automatic integration discovery.

    Returns:
        IntegrationProtocol: Configured Google Mail service
    """
    return GoogleMailService()
