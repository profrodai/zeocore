# quack-core/src/quack_core/integrations/google/mail/operations/auth.py
"""
Authentication _operations for Google Mail integration.

This module provides functions for authenticating with the Gmail API
and initializing the service.
"""

from quack_core.errors import QuackApiError
from quack_core.integrations.google.mail.protocols import GmailService, GoogleCredentials


def initialize_gmail_service(credentials: GoogleCredentials) -> GmailService:
    """
    Initialize the Gmail API service with provided credentials.

    Args:
        credentials: Google API credentials.

    Returns:
        GmailService: Initialized Gmail service object.

    Raises:
        QuackApiError: If service initialization fails.
    """
    try:
        from googleapiclient.discovery import build

        return build("gmail", "v1", credentials=credentials)
    except Exception as api_error:
        raise QuackApiError(
            f"Failed to initialize Gmail API: {api_error}",
            service="Gmail",
            api_method="build",
            original_error=api_error,
        ) from api_error
