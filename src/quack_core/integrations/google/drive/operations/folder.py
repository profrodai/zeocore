# quack-core/src/quack-core/integrations/google/drive/operations/folder.py
"""
Folder _operations for Google Drive integration.

This module provides functions for managing folders in Google Drive,
including creating folders and deleting files or folders.
"""

import logging

from quack_core.errors import QuackApiError
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.google.drive.operations.permissions import (
    set_file_permissions,
)
from quack_core.integrations.google.drive.protocols import DriveService
from quack_core.integrations.google.drive.utils.api import execute_api_request


def create_folder(
    drive_service: DriveService,
    folder_name: str,
    parent_id: str | None = None,
    make_public: bool = True,
    logger: logging.Logger | None = None,
) -> IntegrationResult[str]:
    """
    Create a folder in Google Drive.

    Args:
        drive_service: Google Drive service object.
        folder_name: Name of the folder to create.
        parent_id: Optional parent folder ID.
        make_public: Whether to make the folder publicly accessible.
        logger: Optional logger instance.

    Returns:
        IntegrationResult with the folder ID.
    """
    # Create local logger variable instead of using module logger
    local_logger = logger or logging.getLogger(__name__)

    try:
        # Prepare folder metadata
        folder_metadata: dict[str, object] = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            folder_metadata["parents"] = [parent_id]

        # Create folder using execute_api_request
        folder = execute_api_request(
            drive_service.files().create(
                body=folder_metadata, fields="id, webViewLink"
            ),
            "Failed to create folder in Google Drive",
            "files.create",
        )

        folder_id = str(folder["id"])

        # Set permissions if needed
        if make_public:
            # Pass the logger parameter directly - this is important for testing
            perm_result = set_file_permissions(
                drive_service, folder_id, "reader", "anyone", logger
            )
            if not perm_result.success:
                local_logger.warning(f"Failed to set permissions: {perm_result.error}")

        return IntegrationResult.success_result(
            content=folder_id,
            message=f"Folder created successfully with ID: {folder_id}",
        )

    except QuackApiError as e:
        local_logger.error(f"API error during folder creation: {e}")
        return IntegrationResult.error_result(f"API error: {e}")
    except Exception as e:
        local_logger.error(f"Failed to create folder: {e}")
        return IntegrationResult.error_result(
            f"Failed to create folder in Google Drive: {e}"
        )


def delete_file(
    drive_service: DriveService,
    fileId: str,
    permanent: bool = False,
    logger: logging.Logger | None = None,
) -> IntegrationResult[bool]:
    """
    Delete a file or folder from Google Drive.

    Args:
        drive_service: Google Drive service object.
        fileId: ID of the file or folder to delete.
        permanent: Whether to permanently delete or move to trash.
        logger: Optional logger instance.

    Returns:
        IntegrationResult indicating success.
    """
    local_logger = logger or logging.getLogger(__name__)

    try:
        if permanent:
            # Permanently delete - Use delete method directly
            execute_api_request(
                drive_service.files().delete(fileId=fileId),
                "Failed to delete file from Google Drive",
                "files.delete",
            )
        else:
            # Move to trash
            execute_api_request(
                drive_service.files().update(fileId=fileId, body={"trashed": True}),
                "Failed to trash file in Google Drive",
                "files.update",
            )

        action = "permanently deleted" if permanent else "moved to trash"
        message = f"File {action} successfully: {fileId}"

        return IntegrationResult.success_result(
            content=True,
            message=message,
        )

    except QuackApiError as e:
        local_logger.error(f"API error during file deletion: {e}")
        return IntegrationResult.error_result(f"API error: {e}")
    except Exception as e:
        local_logger.error(f"Failed to delete file: {e}")
        return IntegrationResult.error_result(
            f"Failed to delete file from Google Drive: {e}"
        )
