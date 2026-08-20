"""
Google integrations package for zeo_core.

This package provides integrations with Google services,
such as Google Drive and Gmail, handling authentication
and API interactions with a consistent interface.

Re-exports the full public surface of its drive/ and mail/ subpackages
(GoogleDriveService, GoogleMailService, and their model classes) in
addition to the shared auth/config providers, so
`from zeo_core.integrations.google import GoogleDriveService` works
without needing to know it actually lives one level deeper at
`zeo_core.integrations.google.drive`. Both the shallow (this module) and
deep (`.drive`, `.mail`) import paths are supported; `create_integration`
is NOT re-exported here since drive/ and mail/ each define their own
same-named entry point function -- re-exporting both under one name at
this level would silently shadow one with the other. Use
`from zeo_core.integrations.google.drive import create_integration` (or
`.mail`) for that specific entry point.
"""

from zeo_core.integrations.google.auth import GoogleAuthProvider
from zeo_core.integrations.google.config import GoogleConfigProvider
from zeo_core.integrations.google.drive import (
    DriveFile,
    DriveFolder,
    GoogleDriveService,
)
from zeo_core.integrations.google.mail import GoogleMailService

__all__ = [
    "GoogleAuthProvider",
    "GoogleConfigProvider",
    "GoogleDriveService",
    "DriveFile",
    "DriveFolder",
    "GoogleMailService",
]
