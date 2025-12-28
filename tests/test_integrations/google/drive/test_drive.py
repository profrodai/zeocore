# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/test_drive.py
# role: tests
# neighbors: __init__.py, mocks.py, test_drive_models.py, test_drive_service_delete.py, test_drive_service_download.py, test_drive_service_files.py (+6 more)
# exports: TestDriveModels, TestGoogleDriveServiceDelete, TestGoogleDriveServiceDownload, TestGoogleDriveServiceFiles, TestGoogleDriveServiceFolders, TestGoogleDriveServiceInit, TestGoogleDriveServiceList, TestGoogleDriveServicePermissions (+9 more)
# git_branch: refactor/newHeaders
# git_commit: 7d82586
# === QV-LLM:END ===

"""
Main entry point for Google Drive integration tests.

This file imports all the specific test modules to ensure they are discovered
by pytest when running the test suite.
"""

# Import test classes from _operations submodules
from tests.test_integrations.google.drive.operations.test_operations_download import (
    TestDriveOperationsDownload,
)
from tests.test_integrations.google.drive.operations.test_operations_folder import (
    TestDriveOperationsFolder,
)
from tests.test_integrations.google.drive.operations.test_operations_list_files import (
    TestDriveOperationsListFiles,
)
from tests.test_integrations.google.drive.operations.test_operations_permissions import (
    TestDriveOperationsPermissions,
)
from tests.test_integrations.google.drive.operations.test_operations_upload import (
    TestDriveOperationsUpload,
)

# Import test modules to ensure they are discovered by pytest
from tests.test_integrations.google.drive.test_drive_models import (
    TestDriveModels,
)
from tests.test_integrations.google.drive.test_drive_service_delete import (
    TestGoogleDriveServiceDelete,
)
from tests.test_integrations.google.drive.test_drive_service_download import (
    TestGoogleDriveServiceDownload,
)
from tests.test_integrations.google.drive.test_drive_service_files import (
    TestGoogleDriveServiceFiles,
)
from tests.test_integrations.google.drive.test_drive_service_folders import (
    TestGoogleDriveServiceFolders,
)
from tests.test_integrations.google.drive.test_drive_service_init import (
    TestGoogleDriveServiceInit,
)
from tests.test_integrations.google.drive.test_drive_service_list import (
    TestGoogleDriveServiceList,
)
from tests.test_integrations.google.drive.test_drive_service_permissions import (
    TestGoogleDriveServicePermissions,
)
from tests.test_integrations.google.drive.test_drive_service_upload import (
    TestGoogleDriveServiceUpload,
)
from tests.test_integrations.google.drive.test_protocols import (
    TestDriveProtocols,
)
from tests.test_integrations.google.drive.utils.test_utils_api import (
    TestDriveUtilsApi,
)
from tests.test_integrations.google.drive.utils.test_utils_query import (
    TestDriveUtilsQuery,
)

# Export the test classes for direct import
__all__ = [
    "TestDriveModels",
    "TestGoogleDriveServiceDelete",
    "TestGoogleDriveServiceDownload",
    "TestGoogleDriveServiceFiles",
    "TestGoogleDriveServiceFolders",
    "TestGoogleDriveServiceInit",
    "TestGoogleDriveServiceList",
    "TestGoogleDriveServicePermissions",
    "TestGoogleDriveServiceUpload",
    "TestDriveOperationsDownload",
    "TestDriveOperationsFolder",
    "TestDriveOperationsListFiles",
    "TestDriveOperationsPermissions",
    "TestDriveOperationsUpload",
    "TestDriveProtocols",
    "TestDriveUtilsApi",
    "TestDriveUtilsQuery",
]
