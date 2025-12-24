# quack-core/src/quack_core/integrations/google/mail/__init__.py
"""
Google Mail integration for quack_core.

This module provides integration with Gmail, allowing for email
retrieval, listing, and management through a consistent interface.
"""

from quack_core.integrations.core.protocols import IntegrationProtocol
from quack_core.integrations.google.mail.service import GoogleMailService

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
