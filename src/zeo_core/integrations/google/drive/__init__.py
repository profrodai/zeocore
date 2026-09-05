"""
Google Drive integration for zeo_core.

This module provides integration with Google Drive for storing and sharing
files, with a consistent interface for uploading, downloading, and managing content.
"""

from zeo_core.integrations.core.protocols import StorageIntegrationProtocol
from zeo_core.integrations.google.drive.models import DriveFile, DriveFolder
from zeo_core.integrations.google.drive.protocols import DriveDownloadProtocol
from zeo_core.integrations.google.drive.service import GoogleDriveService

__all__ = [
    "GoogleDriveService",
    "DriveFile",
    "DriveFolder",
    "DriveDownloadProtocol",
    "create_integration",
]


def create_integration() -> StorageIntegrationProtocol:
    """
    Create and configure a Google Drive integration.

    This function is used as an entry point for automatic integration discovery.

    Returns:
        StorageIntegrationProtocol: Configured Google Drive service
    """
    return GoogleDriveService()
