# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/drive/service.py
# module: quack_core.integrations.google.drive.service
# role: service
# neighbors: __init__.py, models.py, protocols.py
# exports: GoogleDriveService
# git_branch: refactor/newHeaders
# git_commit: bd13631
# === QV-LLM:END ===

"""
Google Drive integration service for quack_core.

This module provides the main service class for Google Drive integration,
handling file _operations, folder management, and permissions.
"""

import io
import logging
from collections.abc import Mapping
from typing import Any, TypeVar

from quack_core.lib.errors import (
    QuackApiError,
    QuackBaseAuthError,
    QuackIntegrationError,
)
from quack_core.lib.fs.service import standalone
from quack_core.integrations.core.base import BaseIntegrationService
from quack_core.integrations.core.protocols import StorageIntegrationProtocol
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.google.auth import GoogleAuthProvider
from quack_core.integrations.google.config import GoogleConfigProvider
from quack_core.integrations.google.drive.models import DriveFile, DriveFolder
from quack_core.lib.paths import service as paths_service

NoneType = type(None)
T = TypeVar("T")  # Generic type for result content


class GoogleDriveService(BaseIntegrationService, StorageIntegrationProtocol):
    """Integration service for Google Drive."""

    SCOPES: list[str] = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive.metadata.readonly",
    ]

    def __init__(
        self,
        client_secrets_file: str | None = None,
        credentials_file: str | None = None,
        shared_folder_id: str | None = None,
        config_path: str | None = None,
        scopes: list[str] | None = None,
        log_level: int = logging.INFO,
    ) -> None:
        """
        Initialize the Google Drive integration service.

        Args:
            client_secrets_file: Path to client secrets file.
            credentials_file: Path to credentials file.
            shared_folder_id: ID of shared folder.
            config_path: Path to configuration file.
            scopes: OAuth scopes for API access.
            log_level: Logging level.
        """
        config_provider = GoogleConfigProvider("drive", log_level)
        super().__init__(
            config_provider = config_provider,
            auth_provider = None,
            config = None,
            config_path = config_path,
            log_level = log_level)

        self.config: dict[str, Any] = self._initialize_config(
            client_secrets_file, credentials_file, shared_folder_id
        )
        self.scopes: list[str] = scopes or self.SCOPES
        self.auth_provider = GoogleAuthProvider(
            client_secrets_file=self.config["client_secrets_file"],
            credentials_file=self.config["credentials_file"],
            scopes=self.scopes,
            log_level=log_level,
        )
        self.drive_service: Any = None
        self.shared_folder_id: str | None = self.config.get("shared_folder_id")

    @property
    def name(self) -> str:
        """Get the name of the integration."""
        return "GoogleDrive"

    def _initialize_config(
        self,
        client_secrets_file: str | None,
        credentials_file: str | None,
        shared_folder_id: str | None,
    ) -> dict[str, Any]:
        """
        Initialize configuration from parameters or config file.

        Args:
            client_secrets_file: Path to client secrets file.
            credentials_file: Path to credentials file.
            shared_folder_id: ID of shared folder.

        Returns:
            dict: Configuration dictionary.

        Raises:
            QuackIntegrationError: If configuration initialization fails.
        """
        if client_secrets_file and credentials_file:
            return {
                "client_secrets_file": client_secrets_file,
                "credentials_file": credentials_file,
                "shared_folder_id": shared_folder_id,
            }

        config_result = self.config_provider.load_config(self.config_path)
        if not config_result.success or not config_result.content:
            default_config = self.config_provider.get_default_config()
            if not self.config_provider.validate_config(default_config):
                raise QuackIntegrationError(
                    "Failed to load configuration and default configuration is invalid",
                    {"provider": self.config_provider.name},
                )
            return default_config

        config = config_result.content
        if client_secrets_file:
            config["client_secrets_file"] = client_secrets_file
        if credentials_file:
            config["credentials_file"] = credentials_file
        if shared_folder_id:
            config["shared_folder_id"] = shared_folder_id
        return config

    def initialize(self) -> IntegrationResult[NoneType]:
        """
        Initialize the Google Drive service.

        Returns:
            IntegrationResult: Result of initialization.
        """
        try:
            init_result = super().initialize()
            if not init_result.success:
                return init_result

            try:
                credentials = self.auth_provider.get_credentials()

            except QuackBaseAuthError as auth_error:
                self.logger.error(f"Authentication failed: {auth_error}")
                return IntegrationResult.error_result(
                    f"Failed to authenticate with Google Drive: {auth_error}"
                )

            try:
                from googleapiclient.discovery import build

                self.drive_service = build("drive", "v3", credentials=credentials)
            except Exception as api_error:
                raise QuackApiError(
                    f"Failed to initialize Google Drive API: {api_error}",
                    service="Google Drive",
                    api_method="build",
                    original_error=api_error,
                ) from api_error

            self._initialized = True
            return IntegrationResult.success_result(
                message="Google Drive service initialized successfully"
            )

        except QuackApiError as e:
            self.logger.error(f"API error during initialization: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except QuackBaseAuthError as e:
            self.logger.error(f"Authentication error during initialization: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Drive service: {e}")
            return IntegrationResult.error_result(
                f"Failed to initialize Google Drive service: {e}"
            )

    # --- Helper Methods for Refactoring ---

    def _resolve_file_details(
            self, file_path: str, remote_path: str | None, parent_folder_id: str | None
    ) -> tuple[Any, str, str | None, str]:
        """Resolve file details for upload."""
        from quack_core.lib.fs.service import standalone

        # Extract clean paths using our new helper
        path_obj_result = paths_service.resolve_project_path(file_path)
        if not path_obj_result.success:
            raise QuackIntegrationError(
                f"Failed to resolve path: {path_obj_result.error}")

        # Extract the clean path as a string from the path_obj_result
        path_obj = standalone.extract_path_from_result(path_obj_result)

        file_info = standalone.get_file_info(path_obj)
        if not file_info.success or not file_info.exists:
            raise QuackIntegrationError(f"File not found: {file_path}")

        # Determine the filename to use
        if remote_path and not remote_path.startswith("/"):
            filename = remote_path
        else:
            # Get filename from path by splitting on /
            path_parts = str(path_obj).split("/")
            filename = path_parts[-1] if path_parts else "file"

        folder_id = parent_folder_id or self.shared_folder_id
        mime_type = standalone.get_mime_type(path_obj) or "application/octet-stream"
        return path_obj, filename, folder_id, mime_type

    def _resolve_download_path(
            self, file_metadata: dict[str, Any], local_path: str | None
    ) -> str:
        """
        Resolve the local path for file download.

        Args:
            file_metadata: File metadata from Google Drive.
            local_path: Optional local path to save the file.

        Returns:
            str: The resolved download path.
        """
        file_name = str(file_metadata.get("name", "downloaded_file"))

        if local_path is None:
            # Create a temp directory using fs.create_temp_directory
            temp_dir_result = standalone.create_temp_directory(prefix="quackcore_gdrive_")
            temp_dir = temp_dir_result.data if hasattr(temp_dir_result,
                                                       "data") else temp_dir_result
            # Use fs.join_path for path joining
            joined_path_result = standalone.join_path(temp_dir, file_name)
            return str(joined_path_result.data if hasattr(joined_path_result,
                                                          "data") else joined_path_result)

        # Resolve the local path
        local_path_obj_result = paths_service.resolve_project_path(local_path)
        if not local_path_obj_result.success:
            raise QuackIntegrationError(
                f"Failed to resolve local path: {local_path_obj_result.error}")
        local_path_obj = local_path_obj_result.path

        file_info = standalone.get_file_info(local_path_obj)

        if file_info.success and file_info.exists:
            # Handle different cases depending on whether local_path is a directory or file
            if file_info.is_dir:
                # If it's a directory, join the file name to it
                joined_path_result = standalone.join_path(local_path_obj, file_name)
                return str(joined_path_result.data if hasattr(joined_path_result,
                                                              "data") else joined_path_result)
            else:
                # If it's a file, use the path as is
                return str(local_path_obj)

        # If the path doesn't exist, assume it's a file path the user wants to create
        return str(local_path_obj)

    def _build_query(self, remote_path: str | None, pattern: str | None) -> str:
        """
        Build the query string for listing files.

        Args:
            remote_path: Optional folder ID to list files from.
            pattern: Optional filename pattern to filter results.

        Returns:
            str: The query string.
        """
        query_parts: list[str] = []
        folder_id = remote_path or self.shared_folder_id
        if folder_id:
            query_parts.append(f"'{folder_id}' in parents")
        query_parts.append("trashed = false")
        if pattern:
            if "*" in pattern:
                name_pattern = pattern.replace("*", "")
                if name_pattern:
                    query_parts.append(f"name contains '{name_pattern}'")
            else:
                query_parts.append(f"name = '{pattern}'")
        return " and ".join(query_parts)

    def _execute_upload(
        self, file_metadata: dict[str, Any], media: Any
    ) -> dict[str, Any]:
        """
        Execute the file upload to Google Drive.

        Args:
            file_metadata: File metadata for upload.
            media: Media content to upload.

        Returns:
            dict: The API response.

        Raises:
            QuackApiError: If upload fails.
        """
        try:
            file = (
                self.drive_service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id, webViewLink, webContentLink",
                )
                .execute()
            )
            return file
        except Exception as api_error:
            raise QuackApiError(
                f"Failed to upload file to Google Drive: {api_error}",
                service="Google Drive",
                api_method="files.create",
                original_error=api_error,
            ) from api_error

    def download_file(
        self, remote_id: str, local_path: str | None = None
    ) -> IntegrationResult[str]:
        """
        Download a file from Google Drive.

        Args:
            remote_id: ID of the file to download.
            local_path: Optional local path to save the file.

        Returns:
            IntegrationResult with the local file path.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            # First, get file metadata to determine filename
            try:
                file_metadata = (
                    self.drive_service.files()
                    .get(fileId=remote_id, fields="name, mimeType")
                    .execute()
                )
            except Exception as api_error:
                self.logger.error(f"Failed to get file metadata: {api_error}")
                return IntegrationResult.error_result(
                    f"Failed to get file metadata from Google Drive: {api_error}"
                )

            # Resolve the download path
            download_path = self._resolve_download_path(file_metadata, local_path)

            # Ensure parent directory exists
            parent_dir = standalone.join_path(download_path).parent
            parent_result = standalone.create_directory(parent_dir, exist_ok=True)
            if not parent_result.success:
                return IntegrationResult.error_result(
                    f"Failed to create directory: {parent_result.error}"
                )

            # Download the file content
            try:
                request = self.drive_service.files().get_media(fileId=remote_id)
                from googleapiclient.http import MediaIoBaseDownload

                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)

                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    self.logger.debug(
                        f"Download progress: {int(status.progress() * 100)}%"
                    )
            except Exception as download_error:
                self.logger.error(f"Failed to download file: {download_error}")
                return IntegrationResult.error_result(
                    f"Failed to download file from Google Drive: {download_error}"
                )

            # Reset pointer to beginning of the buffer and read content
            fh.seek(0)
            file_content = fh.read()

            # Write file to disk using fs module
            write_result = standalone.write_binary(download_path, file_content)
            if not write_result.success:
                return IntegrationResult.error_result(
                    f"Failed to write file: {write_result.error}"
                )

            return IntegrationResult.success_result(
                content=download_path,
                message=f"File downloaded successfully to {download_path}",
            )

        except Exception as e:
            self.logger.error(f"Unexpected error during file download: {e}")
            return IntegrationResult.error_result(
                f"Failed to download file from Google Drive: {e}"
            )

    def list_files(
        self, remote_path: str | None = None, pattern: str | None = None
    ) -> IntegrationResult[list[Mapping]]:
        """
        List files in Google Drive.

        Args:
            remote_path: Optional folder ID to list files from.
            pattern: Optional filename pattern to filter results.

        Returns:
            IntegrationResult with the list of files.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            query = self._build_query(remote_path, pattern)
            try:
                response = (
                    self.drive_service.files()
                    .list(
                        q=query,
                        fields=(
                            "files(id, name, mimeType, webViewLink, webContentLink, "
                            "size, createdTime, modifiedTime, parents, shared, trashed)"
                        ),
                        page_size=100,
                    )
                    .execute()
                )
            except Exception as api_error:
                raise QuackApiError(
                    f"Failed to list files from Google Drive: {api_error}",
                    service="Google Drive",
                    api_method="files.list",
                    original_error=api_error,
                ) from api_error

            files: list = []
            for item in response.get("files", []):
                if item["mimeType"] == "application/vnd.google-apps.folder":
                    files.append(DriveFolder.from_api_response(item))
                else:
                    files.append(DriveFile.from_api_response(item))

            return IntegrationResult.success_result(
                content=[file.model_dump() for file in files],
                message=f"Listed {len(files)} files",
            )

        except QuackApiError as e:
            self.logger.error(f"API error during listing files: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except QuackBaseAuthError as e:
            self.logger.error(f"Authentication error during listing files: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to list files: {e}")
            return IntegrationResult.error_result(
                f"Failed to list files from Google Drive: {e}"
            )

    def create_folder(
        self, folder_name: str, parent_path: str | None = None
    ) -> IntegrationResult[str]:
        """
        Create a folder in Google Drive.

        Args:
            folder_name: Name of the folder to create.
            parent_path: Optional parent folder ID.

        Returns:
            IntegrationResult with the folder ID.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            parent_id = parent_path or self.shared_folder_id
            folder_metadata: dict[str, Any] = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_id:
                folder_metadata["parents"] = [parent_id]

            try:
                folder = (
                    self.drive_service.files()
                    .create(body=folder_metadata, fields="id, webViewLink")
                    .execute()
                )
            except Exception as api_error:
                raise QuackApiError(
                    f"Failed to create folder in Google Drive: {api_error}",
                    service="Google Drive",
                    api_method="files.create",
                    original_error=api_error,
                ) from api_error

            if self.config.get("public_sharing", True):
                perm_result = self.set_file_permissions(folder["id"])
                if not perm_result.success:
                    self.logger.warning(
                        f"Failed to set permissions: {perm_result.error}"
                    )

            return IntegrationResult.success_result(
                content=folder["id"],
                message=f"Folder created successfully with ID: {folder['id']}",
            )

        except QuackApiError as e:
            self.logger.error(f"API error during folder creation: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except QuackBaseAuthError as e:
            self.logger.error(f"Authentication error during folder creation: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to create folder: {e}")
            return IntegrationResult.error_result(
                f"Failed to create folder in Google Drive: {e}"
            )

    def set_file_permissions(
        self, fileId: str, role: str | None = None, type_: str = "anyone"
    ) -> IntegrationResult[bool]:
        """
        Set permissions for a file or folder.

        Args:
            fileId: ID of the file or folder.
            role: Permission role (e.g., "reader", "writer").
            type_: Permission type (e.g., "anyone", "user").

        Returns:
            IntegrationResult indicating success.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            role = role or self.config.get("default_share_access", "reader")
            permission = {"type": type_, "role": role, "allowFileDiscovery": True}
            try:
                self.drive_service.permissions().create(
                    fileId=fileId, body=permission, fields="id"
                ).execute()
            except Exception as api_error:
                raise QuackApiError(
                    f"Failed to set permissions in Google Drive: {api_error}",
                    service="Google Drive",
                    api_method="permissions.create",
                    original_error=api_error,
                ) from api_error

            return IntegrationResult.success_result(
                content=True, message=f"Permission set successfully: {role} for {type_}"
            )

        except QuackApiError as e:
            self.logger.error(f"API error during setting permissions: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except QuackBaseAuthError as e:
            self.logger.error(f"Authentication error during setting permissions: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to set permissions: {e}")
            return IntegrationResult.error_result(
                f"Failed to set permissions in Google Drive: {e}"
            )

    def get_sharing_link(self, fileId: str) -> IntegrationResult[str]:
        """
        Get the sharing link for a file.

        Args:
            fileId: ID of the file.

        Returns:
            IntegrationResult with the sharing link.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            try:
                file_metadata = (
                    self.drive_service.files()
                    .get(fileId=fileId, fields="webViewLink, webContentLink")
                    .execute()
                )
            except Exception as api_error:
                raise QuackApiError(
                    f"Failed to get file metadata from Google Drive: {api_error}",
                    service="Google Drive",
                    api_method="files.get",
                    original_error=api_error,
                ) from api_error

            link = (
                file_metadata.get("webViewLink")
                or file_metadata.get("webContentLink")
                or f"https://drive.google.com/file/d/{fileId}/view"
            )
            return IntegrationResult.success_result(
                content=link, message="Got sharing link successfully"
            )

        except QuackApiError as e:
            self.logger.error(f"API error during getting sharing link: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except QuackBaseAuthError as e:
            self.logger.error(f"Authentication error during getting sharing link: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to get sharing link: {e}")
            return IntegrationResult.error_result(
                f"Failed to get sharing link from Google Drive: {e}"
            )

    def delete_file(
        self, fileId: str, permanent: bool = False
    ) -> IntegrationResult[bool]:
        """
        Delete a file from Google Drive.

        Args:
            fileId: ID of the file or folder.
            permanent: Whether to permanently delete or move to trash.

        Returns:
            IntegrationResult indicating success.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            try:
                if permanent:
                    self.drive_service.files().delete(fileId=fileId).execute()
                else:
                    self.drive_service.files().update(
                        fileId=fileId, body={"trashed": True}
                    ).execute()
            except Exception as api_error:
                api_method = "files.delete" if permanent else "files.update"
                raise QuackApiError(
                    f"Failed to delete file from Google Drive: {api_error}",
                    service="Google Drive",
                    api_method=api_method,
                    original_error=api_error,
                ) from api_error

            return IntegrationResult.success_result(
                content=True, message=f"File deleted successfully: {fileId}"
            )

        except QuackApiError as e:
            self.logger.error(f"API error during file deletion: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except QuackBaseAuthError as e:
            self.logger.error(f"Authentication error during file deletion: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to delete file: {e}")
            return IntegrationResult.error_result(
                f"Failed to delete file from Google Drive: {e}"
            )

    def get_file_info(
        self, remote_id: str, fields: str | None = None
    ) -> IntegrationResult[dict[str, Any]]:
        """
        Retrieve file metadata from Google Drive.

        Args:
            remote_id: The ID of the file in Google Drive
            fields: Optional fields to retrieve (defaults to basic metadata)

        Returns:
            IntegrationResult containing file metadata
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            # Default fields if not specified
            default_fields = (
                "id,name,mimeType,parents,webViewLink,webContentLink,"
                "size,createdTime,modifiedTime,shared,trashed"
            )

            file_metadata = (
                self.drive_service.files()
                .get(fileId=remote_id, fields=fields or default_fields)
                .execute()
            )

            return IntegrationResult.success_result(
                content=file_metadata, message="File metadata retrieved successfully"
            )

        except Exception as api_error:
            self.logger.error(f"Failed to retrieve file metadata: {api_error}")
            return IntegrationResult.error_result(
                f"Failed to retrieve file metadata: {api_error}"
            )


    # --- End of Helper Methods ---

    def upload_file(
        self,
        file_path: str,
        remote_path: str | None = None,
        description: str | None = None,
        parent_folder_id: str | None = None,
        public: bool | None = None,
    ) -> IntegrationResult[str]:
        """
        Upload a file to Google Drive.

        Args:
            file_path: Path to the file to upload.
            remote_path: Optional remote path or name.
            description: Optional file description.
            parent_folder_id: Optional parent folder ID.
            public: Whether to make the file publicly accessible.

        Returns:
            IntegrationResult with the file ID or sharing link.
        """
        if init_error := self._ensure_initialized():
            return init_error

        try:
            try:
                path_obj, filename, folder_id, mime_type = self._resolve_file_details(
                    file_path, remote_path, parent_folder_id
                )
            except QuackIntegrationError as e:
                return IntegrationResult.error_result(str(e))

            file_metadata: dict[str, Any] = {
                "name": filename,
                "mimeType": mime_type,
            }

            if description:
                file_metadata["description"] = description

            if folder_id:
                file_metadata["parents"] = [folder_id]

            media_content = standalone.read_binary(path_obj)
            if not media_content.success:
                return IntegrationResult.error_result(
                    f"Failed to read file: {media_content.error}"
                )

            from googleapiclient.http import MediaInMemoryUpload

            media = MediaInMemoryUpload(
                media_content.content, mimetype=mime_type, resumable=True
            )
            file = self._execute_upload(file_metadata, media)

            config_public = self.config.get("public_sharing", True)
            make_public = public if public is not None else config_public
            if make_public:
                # file["id"] is expected to be a str here.
                perm_result = self.set_file_permissions(file["id"])
                if not perm_result.success:
                    self.logger.warning(
                        f"Failed to set permissions: {perm_result.error}"
                    )

            link = (
                file.get("webViewLink")
                or file.get("webContentLink")
                or f"https://drive.google.com/file/d/{file['id']}/view"
            )
            return IntegrationResult.success_result(
                content=link,
                message=f"File uploaded successfully with ID: {file['id']}",
            )

        except QuackApiError as e:
            self.logger.error(f"API error during file upload: {e}")
            return IntegrationResult.error_result(f"API error: {e}")
        except QuackBaseAuthError as e:
            self.logger.error(f"Authentication error during file upload: {e}")
            return IntegrationResult.error_result(f"Authentication error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to upload file: {e}")
            return IntegrationResult.error_result(
                f"Failed to upload file to Google Drive: {e}"
            )
