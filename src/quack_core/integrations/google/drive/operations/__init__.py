# quack-core/src/quack-core/integrations/google/drive/operations/__init__.py
"""
Operations package for Google Drive integration.

This package contains specialized modules for different Google Drive _operations,
such as uploading, downloading, listing files, and managing permissions.
"""

from quack_core.integrations.google.drive.operations import (
    download,
    folder,
    list_files,
    permissions,
    upload,
)

__all__ = [
    "download",
    "folder",
    "list_files",
    "permissions",
    "upload",
]
