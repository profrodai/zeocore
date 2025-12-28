# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/mocks/__init__.py
# role: tests
# neighbors: base.py, credentials.py, download.py, media.py, requests.py, resources.py (+1 more)
# exports: GenericApiRequestMock, MockDriveRequest, MockDrivePermissionsResource, MockDriveFilesResource, MockDriveService, create_mock_drive_service, create_error_drive_service, MockGoogleCredentials (+6 more)
# git_branch: refactor/newHeaders
# git_commit: 175956c
# === QV-LLM:END ===

"""
Mock objects for Google Drive integration testing.

This module brings together all mock implementations from submodules,
making them available through a single import.
"""

# Import from base module
from tests.test_integrations.google.drive.mocks.base import (
    GenericApiRequestMock,
)

# Import from credentials module
from tests.test_integrations.google.drive.mocks.credentials import (
    MockGoogleCredentials,
    create_credentials,
)
from tests.test_integrations.google.drive.mocks.download import (
    MockDownloadOperations,
    mock_download_file,
)

# Import from media module
from tests.test_integrations.google.drive.mocks.media import (
    MockDownloadStatus,
    MockMediaDownloader,
    create_mock_media_io_base_download,
)

# Import from requests module
from tests.test_integrations.google.drive.mocks.requests import (
    MockDriveRequest,
)
from tests.test_integrations.google.drive.mocks.resources import (
    MockDriveFilesResource,
    MockDrivePermissionsResource,
)

# Import from services module
from tests.test_integrations.google.drive.mocks.services import (
    MockDriveService,
    create_error_drive_service,
    create_mock_drive_service,
)

# Import from download module


# Import from resources module


# Export everything that should be available at the package level
__all__ = [
    # Base mocks
    "GenericApiRequestMock",
    # Request mocks
    "MockDriveRequest",
    # Resource mocks
    "MockDrivePermissionsResource",
    "MockDriveFilesResource",
    # Service mocks
    "MockDriveService",
    "create_mock_drive_service",
    "create_error_drive_service",
    # Credential mocks
    "MockGoogleCredentials",
    "create_credentials",
    # Media mocks
    "MockDownloadStatus",
    "MockMediaDownloader",
    "create_mock_media_io_base_download",
    # Download operation mocks
    "MockDownloadOperations",
    "mock_download_file",
]
