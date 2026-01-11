# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/drive/protocols.py
# module: quack_core.integrations.google.drive.protocols
# role: protocols
# neighbors: __init__.py, service.py, models.py
# exports: DrivePermissionsResource, DriveRequest, DriveFilesResource, DriveService, GoogleCredentials
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

"""
Protocol definitions for Google Drive integration.

This module defines protocol classes for Google Drive services and resources,
ensuring proper typing throughout the codebase and avoiding the use of Any.
"""

from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")  # Generic type for result content
R = TypeVar("R")  # Generic type for return values


@runtime_checkable
class DrivePermissionsResource(Protocol):
    """Protocol for Google Drive permissions resource."""

    def create(
        self, fileId: str, body: dict[str, object], fields: str
    ) -> "DriveRequest[dict[str, object]]":
        """
        Create a permission for a file.

        Args:
            fileId: ID of the file.
            body: Permission data.
            fields: Fields to include in the response.

        Returns:
            DriveRequest: Request object for creating permission.
        """
        ...


@runtime_checkable
class DriveRequest(Protocol[R]):
    """Protocol for Google Drive request objects."""

    def execute(self) -> R:
        """
        Execute the request.

        Returns:
            R: The API response.
        """
        ...


@runtime_checkable
class DriveFilesResource(Protocol):
    """Protocol for Google Drive files resource."""

    def create(
        self,
        body: dict[str, object],
        media_body: object | None = None,
        fields: str | None = None,
    ) -> DriveRequest[dict[str, object]]:
        """
        Create a file.

        Args:
            body: File metadata.
            media_body: File content.
            fields: Fields to include in the response.

        Returns:
            DriveRequest: Request object for creating file.
        """
        ...

    def get(
        self, fileId: str, fields: str | None = None
    ) -> DriveRequest[dict[str, object]]:
        """
        Get a file's metadata.

        Args:
            fileId: ID of the file.
            fields: Fields to include in the response.

        Returns:
            DriveRequest: Request object for getting file metadata.
        """
        ...

    def get_media(self, fileId: str) -> DriveRequest[bytes]:
        """
        Download a file's content.

        Args:
            fileId: ID of the file.

        Returns:
            DriveRequest: Request object for downloading file content.
        """
        ...

    def list(
        self,
        q: str | None = None,
        fields: str | None = None,
        page_size: int | None = None,
    ) -> DriveRequest[dict[str, object]]:
        """
        List files.

        Args:
            q: Query string.
            fields: Fields to include in the response.
            page_size: Maximum number of files to return.

        Returns:
            DriveRequest: Request object for listing files.
        """
        ...

    def update(
        self, fileId: str, body: dict[str, object], fields: str | None = None
    ) -> DriveRequest[dict[str, object]]:
        """
        Update a file's metadata.

        Args:
            fileId: ID of the file.
            body: Updated metadata.
            fields: Fields to include in the response.

        Returns:
            DriveRequest: Request object for updating file.
        """
        ...

    def delete(self, fileId: str) -> DriveRequest[None]:
        """
        Delete a file.

        Args:
            fileId: ID of the file.

        Returns:
            DriveRequest: Request object for deleting file.
        """
        ...

    def permissions(self) -> DrivePermissionsResource:
        """
        Get the permissions resource.

        Returns:
            DrivePermissionsResource: The permissions resource.
        """
        ...


@runtime_checkable
class DriveService(Protocol):
    """Protocol for Google Drive service."""

    def files(self) -> DriveFilesResource:
        """
        Get the files resource.

        Returns:
            DriveFilesResource: The files resource.
        """
        ...


@runtime_checkable
class GoogleCredentials(Protocol):
    """Protocol for Google API credentials."""

    token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list[str]
