# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/drive/operations/list_files.py
# module: quack_core.integrations.google.drive.operations.list_files
# role: module
# neighbors: __init__.py, download.py, folder.py, permissions.py, upload.py
# exports: list_files
# git_branch: feat/9-make-setup-work
# git_commit: 8234fdcd
# === QV-LLM:END ===

"""
File listing _ops for Google Drive integration.

This module provides functions for listing files and folders in Google Drive,
including query building and result formatting.
"""

import logging
from collections.abc import Iterable, Mapping

from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.google.drive.models import DriveFile, DriveFolder
from quack_core.integrations.google.drive.protocols import DriveService
from quack_core.integrations.google.drive.utils.api import execute_api_request
from quack_core.integrations.google.drive.utils.query import build_query
from quack_core.core.errors import QuackApiError
from quack_core.core.logging import get_logger


def list_files(
    drive_service: DriveService,
    folder_id: str | None = None,
    pattern: str | None = None,
    logger: logging.Logger | None = None,
) -> IntegrationResult[list[Mapping]]:
    """
    List files in Google Drive.

    Args:
        drive_service: Google Drive service object.
        folder_id: Optional folder ID to list files from.
        pattern: Optional filename pattern to filter results.
        logger: Optional logger instance.

    Returns:
        IntegrationResult containing a list of file information dictionaries.
    """
    local_logger = get_logger(__name__) or logger(__name__)

    try:
        # Build query string
        query = build_query(folder_id, pattern)

        # Execute list request
        response = execute_api_request(
            drive_service.files().list(
                q=query,
                fields=(
                    "files(id, name, mimeType, webViewLink, webContentLink, "
                    "size, createdTime, modifiedTime, parents, shared, trashed)"
                ),
                page_size=100,
            ),
            "Failed to list files from Google Drive",
            "files.list",
        )

        # Process results - add explicit type checking and casting
        files = []

        # Get the files from the response with proper type handling
        files_data = response.get("files")

        # Handle the case where files might not be present or not iterable
        if not isinstance(files_data, Iterable):
            files_data = []

        for item in files_data:
            if isinstance(item, dict):
                if item.get("mimeType") == "application/vnd.google-apps.folder":
                    files.append(DriveFolder.from_api_response(item))
                else:
                    files.append(DriveFile.from_api_response(item))

        # Create the typed list for the return value
        file_maps: list[Mapping] = [file.model_dump() for file in files]

        return IntegrationResult.success_result(
            content=file_maps,
            message=f"Listed {len(files)} files",
        )

    except QuackApiError as e:
        local_logger.error(f"API error during listing files: {e}")
        return IntegrationResult.error_result(f"API error: {e}")
    except Exception as e:
        local_logger.error(f"Failed to list files: {e}")
        return IntegrationResult.error_result(
            f"Failed to list files from Google Drive: {e}"
        )
