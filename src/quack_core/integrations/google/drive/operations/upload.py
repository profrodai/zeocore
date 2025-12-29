# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/drive/operations/upload.py
# module: quack_core.integrations.google.drive.operations.upload
# role: operations
# neighbors: __init__.py, download.py, folder.py, list_files.py, permissions.py
# exports: initialize_drive_service, resolve_file_details, upload_file
# git_branch: refactor/toolkitWorkflow
# git_commit: 07a259e
# === QV-LLM:END ===

"""
Upload _operations for Google Drive integration.

This module provides functions for uploading files to Google Drive,
including file metadata handling and media upload.
All file paths are handled as strings. Filesystem _operations such as
reading a file or obtaining file metadata are delegated to the QuackCore FS API.
"""

import logging

from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

from quack_core.lib.errors import QuackApiError, QuackIntegrationError
from quack_core.lib.fs.service import standalone
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.google.drive.operations import permissions
from quack_core.integrations.google.drive.protocols import (
    DriveService,
    GoogleCredentials,
)
from quack_core.integrations.google.drive.utils.api import execute_api_request
from quack_core.lib.paths import service as paths_service


def initialize_drive_service(credentials: GoogleCredentials) -> DriveService:
    """
    Initialize the Google Drive service with provided credentials.

    Args:
        credentials: Google API credentials.

    Returns:
        DriveService: Initialized Drive service object.

    Raises:
        QuackApiError: If service initialization fails.
    """
    try:
        return build("drive", "v3", credentials=credentials)
    except Exception as api_error:
        raise QuackApiError(
            f"Failed to initialize Google Drive API: {api_error}",
            service="Google Drive",
            api_method="build",
            original_error=api_error,
        ) from api_error


def resolve_file_details(
        file_path: str, remote_path: str | None, parent_folder_id: str | None
) -> tuple[str, str, str | None, str]:
    """
    Resolve file details for upload.

    Args:
        file_path: Path to the file to upload (as a string).
        remote_path: Optional remote path or name.
        parent_folder_id: Optional parent folder ID.

    Returns:
        A tuple containing the resolved path, filename, folder ID, and MIME type as strings.

    Raises:
        QuackIntegrationError: If the file does not exist.
    """
    # Delegate to the resolver to convert the provided file path into a project path.
    resolve_result = paths_service.resolve_project_path(file_path)
    if not resolve_result.success:
        raise QuackIntegrationError(f"Failed to resolve path: {resolve_result.error}")
    resolved_path = resolve_result.path

    # Get file information
    file_info = standalone.get_file_info(resolved_path)
    if not file_info.success or not file_info.exists:
        raise QuackIntegrationError(f"File not found: {file_path}")

    # Determine the filename to use
    if remote_path and not remote_path.startswith("/"):
        filename = remote_path
    else:
        # Get the filename from the path
        path_parts = str(resolved_path).split("/")
        filename = path_parts[-1] if path_parts else "file"

    # Get the MIME type and add folder ID
    mime_type = standalone.get_mime_type(resolved_path) or "application/octet-stream"
    return resolved_path, filename, parent_folder_id, mime_type


def upload_file(
        drive_service: DriveService,
        file_path: str,
        remote_path: str | None = None,
        description: str | None = None,
        parent_folder_id: str | None = None,
        make_public: bool = True,
        logger: logging.Logger | None = None,
) -> IntegrationResult[str]:
    """
    Upload a file to Google Drive.

    Args:
        drive_service: Google Drive service object.
        file_path: Path to the file to upload (as a string).
        remote_path: Optional remote path or name.
        description: Optional file description.
        parent_folder_id: Optional parent folder ID.
        make_public: Whether to make the file publicly accessible.
        logger: Optional logger instance.

    Returns:
        IntegrationResult with the file ID or sharing link as a string.
    """
    logger = logger or logging.getLogger(__name__)

    try:
        # Resolve file details (all paths are handled as strings)
        resolved_path, filename, folder_id, mime_type = resolve_file_details(
            file_path, remote_path, parent_folder_id
        )

        # Prepare file metadata for the upload
        file_metadata: dict[str, object] = {
            "name": filename,
            "mimeType": mime_type,
        }
        if description is not None:
            file_metadata["description"] = description
        if folder_id:
            file_metadata["parents"] = [folder_id]

        # Read file content as binary using our FS API (which expects a string path)
        media_content = standalone.read_binary(resolved_path)
        if not media_content.success:
            return IntegrationResult.error_result(
                f"Failed to read file: {media_content.error}"
            )

        # Create a media upload object
        media = MediaInMemoryUpload(
            media_content.content, mimetype=mime_type, resumable=True
        )

        # Execute the file creation/upload on Google Drive via our API wrapper
        file = execute_api_request(
            drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink, webContentLink",
            ),
            "Failed to upload file to Google Drive",
            "files.create",
        )

        # Convert file ID to string
        fileId = str(file["id"])

        # Set file permissions if requested
        if make_public:
            perm_result = permissions.set_file_permissions(
                drive_service, fileId, "reader", "anyone", logger
            )
            if not perm_result.success:
                logger.warning(f"Failed to set permissions: {perm_result.error}")

        # Extract a usable link from the returned file data
        link: str = (
                str(file.get("webViewLink", ""))
                or str(file.get("webContentLink", ""))
                or f"https://drive.google.com/file/d/{fileId}/view"
        )

        return IntegrationResult.success_result(
            content=link,
            message=f"File uploaded successfully with ID: {fileId}",
        )

    except QuackApiError as e:
        logger.error(f"API error during file upload: {e}")
        return IntegrationResult.error_result(f"API error: {e}")
    except QuackIntegrationError as e:
        logger.error(f"Integration error during file upload: {e}")
        return IntegrationResult.error_result(str(e))
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        return IntegrationResult.error_result(
            f"Failed to upload file to Google Drive: {e}"
        )
