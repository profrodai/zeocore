# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/mail/operations/attachments.py
# module: quack_core.integrations.google.mail.operations.attachments
# role: module
# neighbors: __init__.py, auth.py, email.py
# exports: process_message_parts, handle_attachment
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
# === QV-LLM:END ===

"""
Upload _ops for Google Mail attachments.

This module provides functions for processing email message parts to extract
HTML content and download attachments, saving them to a given storage path.
All file path values are handled as strings. Filesystem _ops
(like joining paths, checking file existence, creating directories, writing files, etc.)
are delegated to the QuackCore FS layer or Python’s os.path utilities.
"""

import base64
import logging
import os

from quack_core.integrations.google.mail.operations.email import clean_filename
from quack_core.integrations.google.mail.protocols import GmailService
from quack_core.integrations.google.mail.utils.api import execute_api_request
from quack_core.core.fs.service import standalone


def process_message_parts(
    gmail_service: GmailService,
    user_id: str,
    parts: list[dict],
    msg_id: str,
    storage_path: str,
    logger: logging.Logger,
) -> tuple[str | None, list[str]]:
    """
    Process message parts to extract HTML content and attachments.

    Args:
        gmail_service: Gmail API service object.
        user_id: Gmail user ID.
        parts: List of message part dictionaries.
        msg_id: The Gmail message ID.
        storage_path: Path (as a string) where attachments should be saved.
        logger: Logger instance.

    Returns:
        A tuple of HTML content (or None) and a list of attachment file paths.
    """
    html_content: str | None = None
    attachments: list[str] = []
    parts_stack = parts.copy()

    while parts_stack:
        part = parts_stack.pop()

        # Process nested parts
        if "parts" in part:
            parts_stack.extend(part["parts"])
            continue

        mime_type = part.get("mimeType", "")

        # Extract HTML content if not already found
        if mime_type == "text/html" and html_content is None:
            data = part.get("body", {}).get("data")
            if data is not None:
                data_str = str(data)
                html_content = base64.urlsafe_b64decode(
                    data_str.encode("utf-8")
                ).decode("utf-8")

        # Process attachments if a filename is present
        elif part.get("filename"):
            attachment_path = handle_attachment(
                gmail_service, user_id, part, msg_id, storage_path, logger
            )
            if attachment_path:
                attachments.append(attachment_path)

    return html_content, attachments


def handle_attachment(
    gmail_service: GmailService,
    user_id: str,
    part: dict,
    msg_id: str,
    storage_path: str,
    logger: logging.Logger,
) -> str | None:
    """
    Download and save an attachment from a message part.

    Args:
        gmail_service: Gmail API service object.
        user_id: Gmail user ID.
        part: Message part dictionary containing attachment data.
        msg_id: The Gmail message ID.
        storage_path: Directory path (as a string) to save the attachment.
        logger: Logger instance.

    Returns:
        The file path to the saved attachment, or None if failed.
    """
    try:
        filename = part.get("filename")
        if not filename:
            return None

        # Get attachment data from body or via a separate API call if needed
        body = part.get("body", {})
        data = body.get("data")
        if data is None and "attachmentId" in body:
            attachment_id = body["attachmentId"]
            attachment = execute_api_request(
                gmail_service.users()
                .messages()
                .attachments()
                .get(user_id=user_id, message_id=msg_id, attachment_id=attachment_id),
                "Failed to get attachment from Gmail",
                "users.messages.attachments.get",
            )
            data = attachment.get("data")

        if data is None:
            return None

        data_str = str(data)
        try:
            content = base64.urlsafe_b64decode(data_str)
        except Exception as e:
            logger.error(f"Failed to decode attachment data: {e}")
            return None

        # Clean the filename
        clean_name = clean_filename(filename)

        # Build initial file path (unwrap DataResult if needed)
        join_res = standalone.join_path(storage_path, clean_name)
        file_path = join_res.data if hasattr(join_res, "data") else join_res


        # Handle filename collisions
        counter = 1
        file_info = standalone.get_file_info(file_path)
        while file_info.success and file_info.exists:
            path_parts = standalone.split_path(file_path)
            name_part = path_parts[-1]
            base, ext = (name_part.rsplit(".", 1) + [""])[:2]
            ext = f".{ext}" if ext else ""
            new_name = f"{base}-{counter}{ext}"
            join_res = standalone.join_path(storage_path, new_name)
            file_path = join_res.data if hasattr(join_res, "data") else join_res
            file_info = standalone.get_file_info(file_path)
            counter += 1

        # Ensure directory exists
        dir_path = os.path.dirname(file_path)
        dir_result = standalone.create_directory(dir_path, exist_ok=True)
        if not (hasattr(dir_result, "success") and dir_result.success):
            logger.error(f"Failed to create directory: {getattr(dir_result, 'error', '')}")
            return None

        # Write the file
        write_result = standalone.write_binary(file_path, content)
        if not (hasattr(write_result, "success") and write_result.success):
            logger.error(f"Failed to write attachment: {getattr(write_result, 'error', '')}")
            return None

        return file_path

    except Exception as e:
        logger.error(f"Error handling attachment: {e}")
        return None
