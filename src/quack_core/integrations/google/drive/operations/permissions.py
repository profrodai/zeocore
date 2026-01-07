# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/drive/operations/permissions.py
# module: quack_core.integrations.google.drive.operations.permissions
# role: operations
# neighbors: __init__.py, download.py, folder.py, list_files.py, upload.py
# exports: set_file_permissions, get_sharing_link
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

"""
Permission _operations for Google Drive integration.

This module provides functions for managing file permissions in Google Drive,
including setting permissions and retrieving sharing links.
"""

import logging
from typing import Any

from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.google.drive.protocols import DriveService

# Import the api.api module itself, not just the function
from quack_core.integrations.google.drive.utils import api
from quack_core.core.errors import QuackApiError


def set_file_permissions(
    drive_service: DriveService,
    fileId: str,
    role: str = "reader",
    type_: str = "anyone",
    logger: logging.Logger | None = None,
) -> IntegrationResult[bool]:
    """
    Set permissions for a file or folder in Google Drive.

    Args:
        drive_service: Google Drive service object.
        fileId: ID of the file or folder.
        role: Permission role (e.g., "reader", "writer").
        type_: Permission type (e.g., "anyone", "user").
        logger: Optional logger instance.

    Returns:
        IntegrationResult indicating success.
    """
    local_logger = logger or logging.getLogger(__name__)

    try:
        # Create permission object
        permission: dict[str, Any] = {
            "type": type_,
            "role": role,
            "allowFileDiscovery": True,
        }

        # Create the request
        request = (
            drive_service.files()
            .permissions()
            .create(fileId=fileId, body=permission, fields="id")
        )

        # Use the module import to call the function - this should make patching work
        api.execute_api_request(
            request,
            "Failed to set permissions in Google Drive",
            "permissions.create",
        )

        return IntegrationResult.success_result(
            content=True, message=f"Permission set successfully: {role} for {type_}"
        )

    except QuackApiError as e:
        local_logger.error(f"API error during setting permissions: {e}")
        return IntegrationResult.error_result(f"API error: {e}")
    except Exception as e:
        local_logger.error(f"Failed to set permissions: {e}")
        return IntegrationResult.error_result(
            f"Failed to set permissions in Google Drive: {e}"
        )


def get_sharing_link(
    drive_service: DriveService,
    fileId: str,
    logger: logging.Logger | None = None,
) -> IntegrationResult[str]:
    """
    Get the sharing link for a file in Google Drive.

    Args:
        drive_service: Google Drive service object.
        fileId: ID of the file.
        logger: Optional logger instance.

    Returns:
        IntegrationResult with the sharing link.
    """
    local_logger = logger or logging.getLogger(__name__)

    try:
        # Get file metadata with link information
        file_metadata = api.execute_api_request(
            drive_service.files().get(
                fileId=fileId, fields="webViewLink, webContentLink"
            ),
            "Failed to get file metadata from Google Drive",
            "files.get",
        )

        # Extract link with explicit type annotation
        link: str = (
            str(file_metadata.get("webViewLink", ""))
            or str(file_metadata.get("webContentLink", ""))
            or f"https://drive.google.com/file/d/{fileId}/view"
        )

        return IntegrationResult.success_result(
            content=link, message="Got sharing link successfully"
        )

    except QuackApiError as e:
        local_logger.error(f"API error during getting sharing link: {e}")
        return IntegrationResult.error_result(f"API error: {e}")
    except Exception as e:
        local_logger.error(f"Failed to get sharing link: {e}")
        return IntegrationResult.error_result(
            f"Failed to get sharing link from Google Drive: {e}"
        )
