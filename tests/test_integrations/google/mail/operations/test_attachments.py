# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/mail/operations/test_attachments.py
# role: operations
# neighbors: __init__.py, test_auth.py, test_email.py
# exports: TestGmailAttachmentOperations
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

"""
Tests for Gmail attachment operations.
"""

import base64
import logging
import os
from unittest.mock import MagicMock, patch

from quack_core.integrations.google.mail.operations import attachments
from quack_core.core.fs import FileInfoResult, OperationResult, WriteResult

from tests.test_integrations.google.mail.mocks import (
    create_mock_gmail_service,
)


class TestGmailAttachmentOperations:
    """Test cases for Gmail attachment operations."""

    def test_process_message_parts(self, tmp_path) -> None:
        """Test processing message parts."""
        # Get mock Gmail service
        gmail_service = create_mock_gmail_service()

        logger = logging.getLogger("test_gmail")
        msg_id = "msg123"
        storage_path = str(tmp_path)

        # Test with HTML content and attachments
        parts = [
            {
                "mimeType": "text/html",
                "body": {
                    "data": base64.urlsafe_b64encode(
                        b"<html><body>Test</body></html>"
                    ).decode()
                },
            },
            {
                "filename": "test.pdf",
                "mimeType": "application/pdf",
                "body": {"attachmentId": "att123"},
            },
        ]

        # Mock the handle_attachment function to avoid actual file operations
        with patch(
            "quack_core.integrations.google.mail.operations.attachments.handle_attachment"
        ) as mock_handle:
            mock_handle.return_value = str(tmp_path / "test.pdf")

            html_content, attachment_paths = attachments.process_message_parts(
                gmail_service, "me", parts, msg_id, storage_path, logger
            )

            assert html_content == "<html><body>Test</body></html>"
            assert len(attachment_paths) == 1
            assert attachment_paths[0] == str(tmp_path / "test.pdf")
            mock_handle.assert_called_once()

    def test_handle_attachment(self) -> None:
        """Test handling an attachment."""
        # Get mock Gmail service
        gmail_service = create_mock_gmail_service()

        logger = logging.getLogger("test_gmail")
        msg_id = "msg1"
        storage_path = "/path/to/storage"

        # Set up attachment data
        attachment_data = base64.urlsafe_b64encode(b"PDF content").decode()

        # Test with inline data
        part = {
            "filename": "test.pdf",
            "mimeType": "application/pdf",
            "body": {"data": attachment_data, "size": 11},
        }

        # Create mocks with proper return values
        mock_dir_result = MagicMock(spec=OperationResult)
        mock_dir_result.success = True

        mock_write_result = MagicMock(spec=WriteResult)
        mock_write_result.success = True

        mock_file_info = MagicMock(spec=FileInfoResult)
        mock_file_info.exists = False
        mock_file_info.success = True

        # We need to understand and mock the entire call chain to prevent real filesystem access
        # Looking at the error, we need to ensure that all filesystem operations are properly mocked

        # Mock the entire module to prevent any real filesystem operations
        with (
            patch.dict(os.environ, {"TESTING": "True"}),
            patch(
                "quack_core.integrations.google.mail.operations.attachments.clean_filename",
                side_effect=lambda x: x,
            ),
            patch(
                "quack_core.integrations.google.mail.operations.attachments.standalone"
            ) as mock_fs,
            patch(
                "quack_core.integrations.google.mail.operations.attachments.base64"
            ) as mock_base64,
            patch("pathlib.Path") as mock_path,
        ):
            # Configure all the filesystem mocks
            mock_fs.create_directory.return_value = mock_dir_result
            mock_fs.get_file_info.return_value = mock_file_info
            mock_fs.join_path.return_value = "/path/to/storage/test.pdf"
            mock_fs.split_path.return_value = ["path", "to", "storage", "test.pdf"]

            # Configure filesystem service
            mock_fs_service = MagicMock()
            mock_fs_service.write_binary.return_value = mock_write_result
            mock_fs.service.FileSystemService.return_value = mock_fs_service

            # Configure path mocks
            path_instance = MagicMock()
            path_instance.parent = "/path/to"
            path_instance.__str__.return_value = "/path/to/storage/test.pdf"
            mock_path.return_value = path_instance

            # Configure base64 mock for decoding attachment data
            mock_base64.urlsafe_b64decode.return_value = b"PDF content"

            # Execute the function under test
            path = attachments.handle_attachment(
                gmail_service,
                "me",
                part,
                msg_id,
                storage_path,
                logger,
            )

            # Assert the result
            assert path == "/path/to/storage/test.pdf"

            # Verify mocks were called correctly
            mock_fs.create_directory.assert_called_once()
            mock_fs.get_file_info.assert_called_once()
            mock_fs.join_path.assert_called_once_with(storage_path, "test.pdf")

    def test_handle_attachment_with_attachment_id(self) -> None:
        """Test handling an attachment with attachment ID."""
        # Get mock Gmail service
        gmail_service = create_mock_gmail_service()

        logger = logging.getLogger("test_gmail")
        msg_id = "msg1"
        storage_path = "/path/to/storage"

        # Test with attachment ID
        part = {
            "filename": "test2.pdf",
            "mimeType": "application/pdf",
            "body": {"attachmentId": "att123", "size": 11},
        }

        # Create mocks with proper return values
        mock_dir_result = MagicMock(spec=OperationResult)
        mock_dir_result.success = True

        mock_write_result = MagicMock(spec=WriteResult)
        mock_write_result.success = True

        mock_file_info = MagicMock(spec=FileInfoResult)
        mock_file_info.exists = False
        mock_file_info.success = True

        # Mock the necessary modules and functions
        with (
            patch.dict(os.environ, {"TESTING": "True"}),
            patch(
                "quack_core.integrations.google.mail.operations.attachments.clean_filename",
                side_effect=lambda x: x,
            ),
            patch(
                "quack_core.integrations.google.mail.operations.attachments.standalone"
            ) as mock_fs,
            patch(
                "quack_core.integrations.google.mail.operations.attachments.base64"
            ) as mock_base64,
            patch("pathlib.Path") as mock_path,
            patch(
                "quack_core.integrations.google.mail.operations.attachments.execute_api_request"
            ) as mock_execute,
        ):
            # Configure filesystem mocks
            mock_fs.create_directory.return_value = mock_dir_result
            mock_fs.get_file_info.return_value = mock_file_info
            mock_fs.join_path.return_value = "/path/to/storage/test2.pdf"
            mock_fs.split_path.return_value = ["path", "to", "storage", "test2.pdf"]

            # Configure filesystem service
            mock_fs_service = MagicMock()
            mock_fs_service.write_binary.return_value = mock_write_result
            mock_fs.service.FileSystemService.return_value = mock_fs_service

            # Configure path mocks
            path_instance = MagicMock()
            path_instance.parent = "/path/to"
            path_instance.__str__.return_value = "/path/to/storage/test2.pdf"
            mock_path.return_value = path_instance

            # Configure API request mock for attachment retrieval
            mock_execute.return_value = {
                "data": base64.urlsafe_b64encode(b"PDF content").decode()
            }

            # Configure base64 mock for decoding attachment data
            mock_base64.urlsafe_b64decode.return_value = b"PDF content"

            # Execute the function under test
            path = attachments.handle_attachment(
                gmail_service,
                "me",
                part,
                msg_id,
                storage_path,
                logger,
            )

            # Assert the result
            assert path == "/path/to/storage/test2.pdf"

            # Verify mocks were called correctly
            mock_fs.create_directory.assert_called_once()
            mock_fs.get_file_info.assert_called_once()
            mock_fs.join_path.assert_called_once_with(storage_path, "test2.pdf")
            mock_execute.assert_called_once()

    def test_handle_attachment_with_filename_collision(self) -> None:
        """Test handling an attachment with filename collision."""
        # Get mock Gmail service
        gmail_service = create_mock_gmail_service()

        logger = logging.getLogger("test_gmail")
        msg_id = "msg1"
        storage_path = "/path/to/storage"

        # Test with a filename that already exists
        part = {
            "filename": "test2.pdf",
            "mimeType": "application/pdf",
            "body": {"attachmentId": "att123", "size": 11},
        }

        # Create mocks for collision scenario
        mock_dir_result = MagicMock(spec=OperationResult)
        mock_dir_result.success = True

        mock_write_result = MagicMock(spec=WriteResult)
        mock_write_result.success = True

        mock_file_info_collision = MagicMock(spec=FileInfoResult)
        mock_file_info_collision.exists = True
        mock_file_info_collision.success = True

        mock_file_info_no_collision = MagicMock(spec=FileInfoResult)
        mock_file_info_no_collision.exists = False
        mock_file_info_no_collision.success = True

        # Mock the necessary modules and functions
        with (
            patch.dict(os.environ, {"TESTING": "True"}),
            patch(
                "quack_core.integrations.google.mail.operations.attachments.clean_filename",
                side_effect=lambda x: x,
            ),
            patch(
                "quack_core.integrations.google.mail.operations.attachments.standalone"
            ) as mock_fs,
            patch(
                "quack_core.integrations.google.mail.operations.attachments.base64"
            ) as mock_base64,
            patch("pathlib.Path") as mock_path,
            patch(
                "quack_core.integrations.google.mail.operations.attachments.execute_api_request"
            ) as mock_execute,
        ):
            # Configure filesystem mocks with collision handling
            mock_fs.create_directory.return_value = mock_dir_result
            mock_fs.get_file_info.side_effect = [
                mock_file_info_collision,
                mock_file_info_no_collision,
            ]
            mock_fs.join_path.side_effect = [
                "/path/to/storage/test2.pdf",
                "/path/to/storage/test2-1.pdf",
            ]
            mock_fs.split_path.return_value = ["path", "to", "storage", "test2.pdf"]

            # Configure filesystem service
            mock_fs_service = MagicMock()
            mock_fs_service.write_binary.return_value = mock_write_result
            mock_fs.service.FileSystemService.return_value = mock_fs_service

            # Configure path mocks for the collision case
            path_instance = MagicMock()
            path_instance.parent = "/path/to"
            path_instance.__str__.return_value = "/path/to/storage/test2-1.pdf"
            mock_path.return_value = path_instance

            # Configure API request mock for attachment retrieval
            mock_execute.return_value = {
                "data": base64.urlsafe_b64encode(b"PDF content").decode()
            }

            # Configure base64 mock for decoding attachment data
            mock_base64.urlsafe_b64decode.return_value = b"PDF content"

            # Execute the function under test
            path = attachments.handle_attachment(
                gmail_service,
                "me",
                part,
                msg_id,
                storage_path,
                logger,
            )

            # Assert the result - should get the deduplicated filename
            assert path == "/path/to/storage/test2-1.pdf"

            # Verify mocks were called correctly
            assert mock_fs.create_directory.call_count == 1
            assert mock_fs.get_file_info.call_count == 2
            assert mock_fs.join_path.call_count == 2
            mock_execute.assert_called_once()

    def test_handle_attachment_with_error(self) -> None:
        """Test handling an attachment with error."""
        # Get mock Gmail service
        gmail_service = create_mock_gmail_service()

        logger = logging.getLogger("test_gmail")
        msg_id = "msg1"
        storage_path = "/path/to/storage"

        # Test with a part that will generate an error
        part = {
            "filename": "test.pdf",
            "mimeType": "application/pdf",
            "body": {"data": "invalid_base64", "size": 11},
        }

        # Mock the necessary functions
        with (
            patch(
                "quack_core.integrations.google.mail.operations.attachments.clean_filename",
                side_effect=lambda x: x,
            ),
            patch(
                "quack_core.integrations.google.mail.operations.attachments.base64.urlsafe_b64decode",
                side_effect=Exception("Decode error"),
            ),
        ):
            # Execute the function under test - should handle the error gracefully
            path = attachments.handle_attachment(
                gmail_service, "me", part, msg_id, storage_path, logger
            )

            # Assert the result - should return None on error
            assert path is None
