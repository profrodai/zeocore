# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/drive/models.py
# module: quack_core.integrations.google.drive.models
# role: models
# neighbors: __init__.py, service.py, protocols.py
# exports: DrivePermission, DriveFile, DriveFolder
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

"""
Data models for Google Drive integration.

This module provides Pydantic models for Google Drive files and folders,
standardizing the representation of Drive resources.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DrivePermission(BaseModel):
    """Model for Google Drive file permissions."""

    id: str | None = Field(None, description="Permission ID")
    type: str = Field(
        "anyone", description="Type of the permission (anyone, user, etc.)"
    )
    role: str = Field("reader", description="Role (reader, writer, etc.)")
    email_address: str | None = Field(
        None, description="Email address for user-specific permissions"
    )
    domain: str | None = Field(
        None, description="Domain for domain-specific permissions"
    )
    allow_file_discovery: bool = Field(
        True, description="Whether the file can be discovered through search"
    )


class DriveFile(BaseModel):
    """Model for Google Drive file information."""

    id: str = Field(..., description="File ID")
    name: str = Field(..., description="File name")
    mime_type: str = Field(..., description="MIME type")
    parents: list[str] = Field(default_factory=list, description="Parent folder IDs")
    web_view_link: str | None = Field(None, description="Web view link")
    web_content_link: str | None = Field(None, description="Web content link")
    size: int | None = Field(None, description="File size in bytes")
    created_time: datetime | None = Field(None, description="Creation time")
    modified_time: datetime | None = Field(None, description="Last modification time")
    permissions: list[DrivePermission] = Field(
        default_factory=list, description="File permissions"
    )
    shared: bool = Field(False, description="Whether the file is shared")
    trashed: bool = Field(False, description="Whether the file is in the trash")

    @classmethod
    def from_api_response(cls, response: dict[str, Any]) -> "DriveFile":
        """
        Create a DriveFile instance from a Google Drive API response.

        Args:
            response: Google Drive API response dictionary

        Returns:
            DriveFile: File information
        """
        # Parse dates if they exist
        created_time = None
        if "createdTime" in response:
            try:
                created_time = datetime.fromisoformat(
                    response["createdTime"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        modified_time = None
        if "modifiedTime" in response:
            try:
                modified_time = datetime.fromisoformat(
                    response["modifiedTime"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # Extract permissions
        permissions = []
        if "permissions" in response and isinstance(response["permissions"], list):
            for perm in response["permissions"]:
                permissions.append(
                    DrivePermission(
                        id=perm.get("id"),
                        type=perm.get("type", "anyone"),
                        role=perm.get("role", "reader"),
                        email_address=perm.get("emailAddress"),
                        domain=perm.get("domain"),
                        allow_file_discovery=perm.get("allowFileDiscovery", True),
                    )
                )

        # Convert size to int if present and handle possible strings
        size = None
        if "size" in response:
            try:
                size = int(response["size"])
            except (ValueError, TypeError):
                pass

        return cls(
            id=response.get("id", ""),
            name=response.get("name", ""),
            mime_type=response.get("mimeType", ""),
            parents=response.get("parents", []),
            web_view_link=response.get("webViewLink"),
            web_content_link=response.get("webContentLink"),
            size=size,
            created_time=created_time,
            modified_time=modified_time,
            permissions=permissions,
            shared=response.get("shared", False),
            trashed=response.get("trashed", False),
        )


class DriveFolder(DriveFile):
    """Model for Google Drive folder information."""

    folder_color_rgb: str | None = Field(None, description="Folder color in RGB format")

    @classmethod
    def from_api_response(cls, response: dict[str, Any]) -> "DriveFolder":
        """
        Create a DriveFolder instance from a Google Drive API response.

        Args:
            response: Google Drive API response dictionary

        Returns:
            DriveFolder: Folder information
        """
        file = DriveFile.from_api_response(response)

        # Ensure it's a folder
        if not file.mime_type.endswith("folder"):
            file.mime_type = "application/vnd.google-apps.folder"

        return cls(
            **file.model_dump(),
            folder_color_rgb=response.get("folderColorRgb"),
        )
