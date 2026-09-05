"""
Google integrations package for zeo_core.

This package provides integrations with Google services,
such as Google Drive and Gmail, handling authentication
and API interactions with a consistent interface.

Re-exports the full public surface of its drive/, mail/, and calendar/
subpackages (GoogleDriveService, GoogleMailService, GoogleCalendarService,
and their model classes) in addition to the shared auth/config providers,
so `from zeo_core.integrations.google import GoogleDriveService` works
without needing to know it actually lives one level deeper at
`zeo_core.integrations.google.drive`. Both the shallow (this module) and
deep (`.drive`, `.mail`, `.calendar`) import paths are supported;
`create_integration` is NOT re-exported here since drive/, mail/, and
calendar/ each define their own same-named entry point function --
re-exporting more than one under one name at this level would silently
shadow the others. Use `from zeo_core.integrations.google.drive import
create_integration` (or `.mail`, `.calendar`) for that specific entry
point.
"""

from zeo_core.integrations.google.auth import GoogleAuthProvider
from zeo_core.integrations.google.calendar import (
    Calendar,
    CalendarEvent,
    GoogleCalendarService,
)
from zeo_core.integrations.google.config import GoogleConfigProvider
from zeo_core.integrations.google.drive import (
    DriveFile,
    DriveFolder,
    GoogleDriveService,
)
from zeo_core.integrations.google.mail import GoogleMailService
from zeo_core.integrations.google.ports import (
    DiscoveryGoogleApiClientFactory,
    GoogleApiClientFactory,
    GoogleCredentialSource,
)

__all__ = [
    "GoogleAuthProvider",
    "GoogleConfigProvider",
    "GoogleDriveService",
    "DriveFile",
    "DriveFolder",
    "GoogleMailService",
    "GoogleCalendarService",
    "Calendar",
    "CalendarEvent",
    "DiscoveryGoogleApiClientFactory",
    "GoogleApiClientFactory",
    "GoogleCredentialSource",
]
