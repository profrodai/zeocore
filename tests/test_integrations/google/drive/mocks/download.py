# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/mocks/download.py
# role: tests
# neighbors: __init__.py, base.py, credentials.py, media.py, requests.py, resources.py (+1 more)
# exports: MockDownloadOperations, mock_download_file
# git_branch: refactor/toolkitWorkflow
# git_commit: 234aec0
# === QV-LLM:END ===

"""
Mock classes for Google Drive download _operations.
"""

import logging
from typing import Any

from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.google.drive.protocols import DriveService


def mock_download_file(
    drive_service: DriveService,
    remote_id: str,
    local_path: str | None = None,
    logger: logging.Logger | None = None,
) -> IntegrationResult[str]:
    """
    Mock implementation for download_file that matches the expected signature.

    Args:
        drive_service: Google Drive service object.
        remote_id: ID of the file to download.
        local_path: Optional local path to save the file.
        logger: Optional logger instance.

    Returns:
        IntegrationResult with the local file path.
    """
    # Default path if not provided
    result_path = local_path or f"/tmp/mock_file_{remote_id}.txt"

    # Return success result
    return IntegrationResult.success_result(
        content=result_path,
        message=f"Mock file downloaded successfully to {result_path}",
    )


class MockDownloadOperations:
    """
    Mock class to replace the _operations/download.py module.

    This provides replacement functions with matching signatures
    to the real download _operations module.
    """

    @staticmethod
    def resolve_download_path(
        file_metadata: dict[str, Any], local_path: str | None = None
    ) -> str:
        """
        Mock implementation for resolve_download_path.

        Args:
            file_metadata: File metadata from Google Drive.
            local_path: Optional local path to save the file.

        Returns:
            str: The resolved download path.
        """
        file_name = file_metadata.get("name", "mock_file.txt")

        if local_path is None:
            return f"/tmp/{file_name}"

        return f"{local_path}/{file_name}" if local_path.endswith("/") else local_path

    @staticmethod
    def download_file(
        drive_service: DriveService,
        remote_id: str,
        local_path: str | None = None,
        logger: str | None = None,
    ) -> IntegrationResult[str]:
        """
        Mock implementation for download_file.

        Args:
            drive_service: Google Drive service object.
            remote_id: ID of the file to download.
            local_path: Optional local path to save the file.
            logger: Optional logger instance.

        Returns:
            IntegrationResult with the local file path.
        """
        # Default path if not provided
        result_path = local_path or f"/tmp/mock_file_{remote_id}.txt"

        # Return success result
        return IntegrationResult.success_result(
            content=result_path,
            message=f"Mock file downloaded successfully to {result_path}",
        )
