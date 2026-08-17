"""
Authentication _ops for Google Mail integration.

This module provides functions for authenticating with the Gmail API
and initializing the service.
"""

from typing import cast

from zeo_core.core.errors import ZeoApiError
from zeo_core.integrations.google.mail.protocols import (
    GmailService,
    GoogleCredentials,
)


def initialize_gmail_service(credentials: GoogleCredentials) -> GmailService:
    """
    Initialize the Gmail API service with provided credentials.

    Args:
        credentials: Google API credentials.

    Returns:
        GmailService: Initialized Gmail service object.

    Raises:
        ZeoApiError: If service initialization fails.
    """
    try:
        from googleapiclient.discovery import build

        # build() returns Any; drive/operations/upload.py:45 already
        # established cast(<ServiceProtocol>, build(...)) as this repo's
        # idiom for the identical googleapiclient discovery pattern.
        return cast(GmailService, build("gmail", "v1", credentials=credentials))
    except Exception as api_error:
        raise ZeoApiError(
            f"Failed to initialize Gmail API: {api_error}",
            service="Gmail",
            api_method="build",
            original_error=api_error,
        ) from api_error
