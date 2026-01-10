# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/mail/operations/email.py
# module: quack_core.integrations.google.mail.operations.email
# role: operations
# neighbors: __init__.py, attachments.py, auth.py
# exports: MessagesRequest, MessagesResource, UsersResource, GmailResponse, build_query, list_emails, download_email, clean_filename (+2 more)
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

"""
Email operations for Google Mail integration.

This module provides functions for listing and downloading emails from Gmail,
including handling message formats and content extraction.

All file paths are handled as strings. Filesystem operations (joining paths,
reading file info, writing files, etc.) are delegated to the QuackCore FS layer
or built-in os.path utilities.
"""

import base64
import logging
import os
import re
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Protocol, TypeVar, cast

from googleapiclient.errors import HttpError
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.google.mail.protocols import GmailRequest, GmailService
from quack_core.integrations.google.mail.utils.api import execute_api_request
from quack_core.core.fs.service import standalone

T = TypeVar("T")  # Generic type for result content


class MessagesRequest(GmailRequest, Protocol):
    """Protocol for Gmail messages request object."""

    pass


class MessagesResource(Protocol):
    """Protocol for Gmail messages resource."""

    def list(self, user_id: str, q: str, max_results: int) -> MessagesRequest: ...
    def get(
        self, user_id: str, message_id: str, message_format: str
    ) -> MessagesRequest: ...


class UsersResource(Protocol):
    """Protocol for Gmail users resource."""

    def messages(self) -> MessagesResource: ...


class GmailResponse(Protocol):
    """Protocol for Gmail API response."""

    def get(self, key: str, default: T) -> T: ...


def build_query(days_back: int = 7, labels: list[str] | None = None) -> str:
    """
    Build a Gmail search query based on provided parameters.

    Args:
        days_back: Number of days to look back for emails.
        labels: List of Gmail labels to filter by.

    Returns:
        Gmail search query string.
    """
    after_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    query_parts = []
    if labels:
        query_parts.extend(f"label:{label}" for label in labels)
    query_parts.append(f"after:{after_date}")
    return " ".join(query_parts)


def list_emails(
    gmail_service: GmailService,
    user_id: str = "me",
    query: str = "",
    logger: logging.Logger | None = None,
) -> IntegrationResult[list[Mapping]]:
    """
    List emails matching the provided query.

    Args:
        gmail_service: Gmail API service object.
        user_id: Gmail user ID.
        query: Gmail search query.
        logger: Optional logger instance.

    Returns:
        IntegrationResult containing a list of email message dictionaries.
    """
    logger = logger or logging.getLogger(__name__)
    try:
        response_obj = execute_api_request(
            gmail_service.users()
            .messages()
            .list(user_id=user_id, q=query, max_results=100),
            "Failed to list emails from Gmail",
            "users.messages.list",
        )
        response = cast(GmailResponse, response_obj)
        messages = response.get("messages", [])
        return IntegrationResult.success_result(
            content=messages,
            message=f"Listed {len(messages)} emails",
        )
    except HttpError as e:
        logger.error(f"Gmail API error during listing emails: {e}")
        return IntegrationResult.error_result(
            f"Gmail API error during listing emails: {e}"
        )
    except Exception as e:
        logger.error(f"Failed to list emails: {e}")
        return IntegrationResult.error_result(f"Failed to list emails: {e}")


def download_email(
    gmail_service: GmailService,
    user_id: str,
    msg_id: str,
    storage_path: str,
    include_subject: bool = False,
    include_sender: bool = False,
    max_retries: int = 5,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    logger: logging.Logger | None = None,
) -> IntegrationResult[str]:
    """
    Download a Gmail message and save it as an HTML file.

    Args:
        gmail_service: Gmail API service object.
        user_id: Gmail user ID.
        msg_id: The Gmail message ID.
        storage_path: Directory (as a string) where to save the email.
        include_subject: Whether to include the email subject in the output.
        include_sender: Whether to include the sender in the output.
        max_retries: Maximum number of retries for API calls.
        initial_delay: Initial delay in seconds before the first retry.
        max_delay: Maximum delay in seconds before any retry.
        logger: Optional logger instance.

    Returns:
        IntegrationResult containing the file path (as a string) where the email was saved.
    """
    logger = logger or logging.getLogger(__name__)
    try:
        message = _get_message_with_retry(
            gmail_service,
            user_id,
            msg_id,
            max_retries,
            initial_delay,
            max_delay,
            logger,
        )
        if not message:
            return IntegrationResult.error_result(
                f"Message {msg_id} could not be retrieved"
            )

        payload = cast(GmailResponse, message).get("payload", {})
        headers = cast(GmailResponse, payload).get("headers", [])
        subject = _extract_header(headers, "subject", "No Subject")
        sender = _extract_header(headers, "from", "unknown@sender")
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        clean_sender_name = clean_filename(sender)
        filename = f"{timestamp}-{clean_sender_name}.html"
        # Use standalone.join_path to join storage path and filename (returns a string)
        filepath = str(standalone.join_path(storage_path, filename))
        html_content, attachments = process_message_parts(
            gmail_service, user_id, [payload], msg_id, storage_path, logger
        )
        if not html_content:
            logger.warning(f"No HTML content found in message {msg_id}")
            return IntegrationResult.error_result(
                f"No HTML content found in message {msg_id}"
            )
        content = html_content
        header_parts = []
        if include_subject:
            header_parts.append(f"<h1>Subject: {subject}</h1>")
        if include_sender:
            header_parts.append(f"<h2>From: {sender}</h2>")
        if header_parts:
            content = f"{''.join(header_parts)}<hr/>{content}"
        write_result = standalone.write_text(filepath, content, encoding="utf-8")
        if not write_result.success:
            logger.error(f"Failed to write email content: {write_result.error}")
            return IntegrationResult.error_result(
                f"Failed to write email content: {write_result.error}"
            )
        return IntegrationResult.success_result(
            content=filepath,
            message=f"Email downloaded successfully to {filepath}",
        )
    except Exception as e:
        logger.error(f"Failed to download email {msg_id}: {e}")
        return IntegrationResult.error_result(f"Failed to download email {msg_id}: {e}")


def _get_message_with_retry(
    gmail_service: GmailService,
    user_id: str,
    msg_id: str,
    max_retries: int,
    initial_delay: float,
    max_delay: float,
    logger: logging.Logger,
) -> Mapping | None:
    """
    Get a Gmail message with retry logic.

    Args:
        gmail_service: Gmail API service object.
        user_id: Gmail user ID.
        msg_id: The Gmail message ID.
        max_retries: Maximum number of retries.
        initial_delay: Initial delay before the first retry.
        max_delay: Maximum delay between retries.
        logger: Logger instance.

    Returns:
        The message data as a Mapping if successful, otherwise None.
    """
    retry_count = 0
    delay = initial_delay
    while retry_count < max_retries:
        try:
            result = execute_api_request(
                gmail_service.users()
                .messages()
                .get(user_id=user_id, message_id=msg_id, message_format="full"),
                "Failed to get message from Gmail",
                "users.messages.get",
            )
            return cast(Mapping, result)
        except HttpError as e:
            retry_count += 1
            if retry_count == max_retries:
                logger.error(
                    f"Failed to download message {msg_id} after {max_retries} attempts"
                )
                return None
            logger.debug(
                f"Retry {retry_count}/{max_retries} for message {msg_id} after error: {e}"
            )
            time.sleep(delay)
            delay = min(delay * 2, max_delay)
    return None


def _extract_header(headers: Sequence[Mapping], name: str, default: str) -> str:
    """
    Extract a header value from a list of headers.

    Args:
        headers: List of header dictionaries.
        name: Header name to extract.
        default: Default value if header is not found.

    Returns:
        The header value or the default.
    """
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", default)
    return default


def clean_filename(text: str) -> str:
    """
    Clean a string to be safely used as a filename.

    Args:
        text: Input text.

    Returns:
        A safe filename string.
    """
    return re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")


def process_message_parts(
    gmail_service: GmailService,
    user_id: str,
    parts: list[Mapping],
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
        storage_path: Directory (as a string) where attachments are saved.
        logger: Logger instance.

    Returns:
        A tuple of HTML content (or None) and a list of attachment file paths (as strings).
    """
    html_content = None
    attachments: list[str] = []
    parts_stack = list(parts)
    while parts_stack:
        part = parts_stack.pop()
        if "parts" in part:
            parts_stack.extend(part["parts"])
            continue
        mime_type = part.get("mimeType", "")
        if mime_type == "text/html" and html_content is None:
            data = part.get("body", {}).get("data")
            if data is not None:
                data_str = str(data)
                html_content = base64.urlsafe_b64decode(
                    data_str.encode("UTF-8")
                ).decode("UTF-8")
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
    part: Mapping,
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
        storage_path: Directory (as a string) in which to save the attachment.
        logger: Logger instance.

    Returns:
        The path (as a string) to the saved attachment, or None if failed.
    """
    try:
        filename = part.get("filename")
        if not filename:
            return None

        body = part.get("body", {})
        data = body.get("data")
        if data is None and "attachmentId" in body:
            attachment_id = body["attachmentId"]
            attachment = execute_api_request(
                gmail_service.users()
                .messages()
                .attachments()
                .get(
                    user_id=user_id,
                    message_id=msg_id,
                    attachment_id=attachment_id,
                ),
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

        clean_name = clean_filename(filename)
        file_path = str(standalone.join_path(storage_path, clean_name))
        counter = 1
        file_info = standalone.get_file_info(file_path)
        while file_info.success and file_info.exists:
            # Split the file name using standalone.split_path
            path_parts = standalone.split_path(file_path)
            filename_parts = path_parts[-1].rsplit(".", 1)
            base_name = filename_parts[0]
            ext = f".{filename_parts[1]}" if len(filename_parts) > 1 else ""
            new_filename = f"{base_name}-{counter}{ext}"
            file_path = str(standalone.join_path(storage_path, new_filename))
            file_info = standalone.get_file_info(file_path)
            counter += 1

        # Ensure the directory exists using os.path.dirname to get the directory string.
        dir_path = os.path.dirname(file_path)
        dir_result = standalone.create_directory(dir_path, exist_ok=True)
        if not (dir_result.success if hasattr(dir_result, "success") else False):
            logger.error(f"Failed to create directory for attachment: {file_path}")
            return None

        write_result = standalone.write_binary(file_path, content)
        if not (write_result.success if hasattr(write_result, "success") else False):
            logger.error(f"Failed to write attachment: {write_result.error}")
            return None

        return file_path

    except Exception as e:
        logger.error(f"Error handling attachment: {e}")
        return None
