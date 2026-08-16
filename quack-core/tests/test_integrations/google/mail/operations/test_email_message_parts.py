# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/mail/operations/test_email_message_parts.py  # noqa: E501
# === QV-LLM:END ===

"""
Tests for the previously-uncovered process_message_parts / handle_attachment
functions in quack_core.integrations.google.mail.operations.email, plus the
two error-path lines in download_email / _get_message_with_retry that the
sibling test_email.py did not exercise.

Boundary-mock rule (RULING-235): the external boundary here is the Gmail API
(gmail_service / execute_api_request) -- that's what gets mocked, using the
same Protocol-compatible mock classes as the sibling test_email.py. The
filesystem side (standalone.join_path / get_file_info / create_directory /
write_binary) is quack_core's OWN code, so it is exercised for real -- this is
exactly the boundary this stream's own history (RULING-237/238/240) found
real bugs by respecting.

core/fs's standalone service sandboxes to base_dir=Path.cwd() by default and
REJECTS absolute paths outside it (SERVICE-CONTRACT.md, allow_absolute=False).
A bare pytest tmp_path is always outside the repo tree, so real standalone.*
calls against a raw tmp_path path fail with a QuackPathOutsideBaseDirError.
Worse: get_service() is an @lru_cache(maxsize=1) singleton (core/fs/service/
__init__.py) constructed ONCE per test process from whatever cwd was active
at first call and never re-read -- so monkeypatch.chdir() AFTER that point has
NO effect on it either. The sibling test_attachments.py (testing the parallel
attachments.py module) hits this identical wall and works around it the same
way this file does: mock `standalone` itself for handle_attachment's fs
calls (the only way to keep the sandbox from firing) while process_message_parts
and the Gmail-API boundary stay real/Protocol-mocked per RULING-235.
"""

import base64
import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from quack_core.integrations.google.mail.operations import email
from quack_core.integrations.google.mail.protocols import (
    GmailAttachmentsResource,
    GmailMessagesResource,
    GmailRequest,
    GmailService,
    GmailUsersResource,
)


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("UTF-8")).decode("UTF-8")


class _MockRequest(GmailRequest):
    def __init__(self, return_value: dict | None) -> None:
        self.return_value = return_value

    def execute(self) -> dict | None:
        return self.return_value


class _MockAttachmentsResource(GmailAttachmentsResource):
    def __init__(self) -> None:
        self.get_return: dict | None = None

    def get(self, user_id: str, message_id: str, attachment_id: str) -> GmailRequest:
        return _MockRequest(self.get_return)


class _MockMessagesResource(GmailMessagesResource):
    def __init__(self) -> None:
        self.attachments_resource = _MockAttachmentsResource()
        self.list_return: dict = {}
        self.get_return: dict = {}

    def list(self, user_id: str, q: str, max_results: int) -> GmailRequest:
        return _MockRequest(self.list_return)

    def get(self, user_id: str, message_id: str, message_format: str) -> GmailRequest:
        return _MockRequest(self.get_return)

    def attachments(self) -> GmailAttachmentsResource:
        return self.attachments_resource


class _MockUsersResource(GmailUsersResource):
    def __init__(self) -> None:
        self.messages_resource = _MockMessagesResource()

    def messages(self) -> GmailMessagesResource:
        return self.messages_resource


class _MockGmailService(GmailService):
    def __init__(self) -> None:
        self.users_resource = _MockUsersResource()

    def users(self) -> GmailUsersResource:
        return self.users_resource


@pytest.fixture
def mock_gmail_service() -> Any:  # noqa: ANN401
    return _MockGmailService()


@pytest.fixture
def logger() -> logging.Logger:
    return logging.getLogger("test_gmail_message_parts")


@pytest.fixture
def storage_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real writable directory the fs sandbox will accept.

    core/fs's default base_dir is Path.cwd() and it rejects absolute paths
    outside it (allow_absolute=False, see SERVICE-CONTRACT.md). chdir INTO
    tmp_path so it becomes cwd/base_dir, then hand back tmp_path itself --
    callers pass str(storage_dir) (now == cwd) and real standalone.* calls
    succeed instead of tripping the sandbox.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestProcessMessageParts:
    """Tests for process_message_parts (0% covered before this file)."""

    def test_single_html_part_extracts_content(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        parts = [
            {
                "mimeType": "text/html",
                "body": {"data": _b64("<html>hi</html>")},
            }
        ]
        html, attachments = email.process_message_parts(
            mock_gmail_service, "me", parts, "msg1", str(storage_dir), logger
        )
        assert html == "<html>hi</html>"
        assert attachments == []

    def test_nested_parts_are_flattened_and_processed(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        parts = [
            {
                "parts": [
                    {"mimeType": "text/html", "body": {"data": _b64("<p>nested</p>")}},
                ]
            }
        ]
        html, attachments = email.process_message_parts(
            mock_gmail_service, "me", parts, "msg1", str(storage_dir), logger
        )
        assert html == "<p>nested</p>"
        assert attachments == []

    def test_first_html_part_wins_when_multiple_present(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        # process_message_parts uses a stack (pop from end), so the LAST
        # item in the input list is processed FIRST.
        parts = [
            {"mimeType": "text/html", "body": {"data": _b64("<p>first-in-list</p>")}},
            {"mimeType": "text/html", "body": {"data": _b64("<p>second-in-list</p>")}},
        ]
        html, _ = email.process_message_parts(
            mock_gmail_service, "me", parts, "msg1", str(storage_dir), logger
        )
        assert html == "<p>second-in-list</p>"

    def test_html_part_with_no_data_is_skipped(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        parts = [{"mimeType": "text/html", "body": {}}]
        html, attachments = email.process_message_parts(
            mock_gmail_service, "me", parts, "msg1", str(storage_dir), logger
        )
        assert html is None
        assert attachments == []

    def test_attachment_part_delegates_to_handle_attachment(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        parts = [
            {
                "filename": "report.pdf",
                "body": {"data": _b64("pdf-bytes-here")},
            }
        ]
        with patch(
            "quack_core.integrations.google.mail.operations.email.handle_attachment",
            return_value=str(storage_dir / "report.pdf"),
        ) as mock_handle:
            html, attachments = email.process_message_parts(
                mock_gmail_service, "me", parts, "msg1", str(storage_dir), logger
            )
        assert html is None
        assert attachments == [str(storage_dir / "report.pdf")]
        mock_handle.assert_called_once()

    def test_part_with_no_filename_and_no_html_is_ignored(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        parts = [{"mimeType": "application/octet-stream", "body": {}}]
        html, attachments = email.process_message_parts(
            mock_gmail_service, "me", parts, "msg1", str(storage_dir), logger
        )
        assert html is None
        assert attachments == []

    def test_empty_parts_list_returns_none_and_empty(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        html, attachments = email.process_message_parts(
            mock_gmail_service, "me", [], "msg1", str(storage_dir), logger
        )
        assert html is None
        assert attachments == []


class TestHandleAttachment:
    """Tests for handle_attachment (0% covered before this file).

    standalone is mocked here rather than exercised for real -- see the
    module docstring: get_service() is a process-wide @lru_cache(maxsize=1)
    singleton bound to whatever cwd was live at first construction, so
    monkeypatch.chdir() cannot retarget its base_dir after the fact, and a
    bare tmp_path is always rejected as outside it. This is the identical
    wall test_attachments.py (the sibling module) hits and solves the same
    way. Fixture return values below use MagicMock with only the attributes
    handle_attachment actually reads (.success, .exists, .data, .error) --
    a real DataResult/FileInfoResult would be more faithful, but see the
    RULING-235 bug pinned in test_join_path_result_is_stringified_not_
    unwrapped_bug below: production itself does NOT call `.data` on
    join_path's result, so a MagicMock exercising that exact real (buggy)
    code path is the honest choice here, not a shortcut.
    """

    def test_no_filename_returns_none(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        part = {"body": {"data": _b64("x")}}
        result = email.handle_attachment(
            mock_gmail_service, "me", part, "msg1", str(storage_dir), logger
        )
        assert result is None

    def test_no_data_and_no_attachment_id_returns_none(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        part = {"filename": "empty.bin", "body": {}}
        result = email.handle_attachment(
            mock_gmail_service, "me", part, "msg1", str(storage_dir), logger
        )
        assert result is None

    def test_undecodable_base64_returns_none(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        # base64.urlsafe_b64decode is lenient about most junk characters
        # (they're silently dropped), so a string of otherwise-valid
        # alphabet characters whose LENGTH breaks the 4-character grouping
        # is what actually raises ("Incorrect padding") -- verified
        # directly: urlsafe_b64decode("ab") raises binascii.Error, while
        # e.g. "not-valid-base64!!!" decodes without error (the "!!!" is
        # simply dropped). "ab" is 2 valid alphabet chars with no way to
        # pad to a multiple of 4, so it always raises regardless of
        # padding heuristics.
        part = {"filename": "bad.bin", "body": {"data": "ab"}}
        result = email.handle_attachment(
            mock_gmail_service, "me", part, "msg1", str(storage_dir), logger
        )
        assert result is None

    def test_fetches_attachment_by_id_when_no_inline_data(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        """No inline body.data -> falls through to the attachments().get()
        API call, decoding whatever it returns instead."""
        mock_gmail_service.users().messages().attachments_resource.get_return = {
            "data": _b64("fetched-bytes")
        }
        part = {"filename": "doc.txt", "body": {"attachmentId": "att-123"}}

        with (
            patch(
                "quack_core.integrations.google.mail.operations.email.standalone.get_file_info"
            ) as mock_info,
            patch(
                "quack_core.integrations.google.mail.operations.email.standalone.create_directory"
            ) as mock_mkdir,
            patch(
                "quack_core.integrations.google.mail.operations.email.standalone.write_binary"
            ) as mock_write,
        ):
            mock_info.return_value = MagicMock(success=True, exists=False)
            mock_mkdir.return_value = MagicMock(success=True)
            mock_write.return_value = MagicMock(success=True)

            result = email.handle_attachment(
                mock_gmail_service, "me", part, "msg1", str(storage_dir), logger
            )

        assert result is not None
        # The attachment bytes actually written are the ones fetched by ID.
        assert mock_write.call_args[0][1] == b"fetched-bytes"

    def test_happy_path_creates_directory_and_writes_once(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        part = {"filename": "photo.png", "body": {"data": _b64("png-bytes")}}

        with (
            patch(
                "quack_core.integrations.google.mail.operations.email.standalone.get_file_info"
            ) as mock_info,
            patch(
                "quack_core.integrations.google.mail.operations.email.standalone.create_directory"
            ) as mock_mkdir,
            patch(
                "quack_core.integrations.google.mail.operations.email.standalone.write_binary"
            ) as mock_write,
        ):
            mock_info.return_value = MagicMock(success=True, exists=False)
            mock_mkdir.return_value = MagicMock(success=True)
            mock_write.return_value = MagicMock(success=True)

            result = email.handle_attachment(
                mock_gmail_service, "me", part, "msg1", str(storage_dir), logger
            )

        assert result is not None
        mock_mkdir.assert_called_once()
        mock_write.assert_called_once()
        assert mock_write.call_args[0][1] == b"png-bytes"

    def test_duplicate_filename_gets_counter_suffix(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        """get_file_info reporting exists=True once, then False, drives the
        while-loop's counter-increment branch exactly once."""
        part = {"filename": "dupe.txt", "body": {"data": _b64("new-content")}}

        with (
            patch(
                "quack_core.integrations.google.mail.operations.email.standalone.get_file_info"
            ) as mock_info,
            patch(
                "quack_core.integrations.google.mail.operations.email.standalone.create_directory"
            ) as mock_mkdir,
            patch(
                "quack_core.integrations.google.mail.operations.email.standalone.write_binary"
            ) as mock_write,
            patch(
                "quack_core.integrations.google.mail.operations.email.standalone.split_path"
            ) as mock_split,
        ):
            mock_info.side_effect = [
                MagicMock(success=True, exists=True),  # dupe.txt already there
                MagicMock(success=True, exists=False),  # dupe-1.txt is free
            ]
            mock_split.return_value = ["dupe.txt"]
            mock_mkdir.return_value = MagicMock(success=True)
            mock_write.return_value = MagicMock(success=True)

            result = email.handle_attachment(
                mock_gmail_service, "me", part, "msg1", str(storage_dir), logger
            )

        assert result is not None
        assert mock_info.call_count == 2
        assert mock_write.call_count == 1

    def test_directory_create_failure_returns_none(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        part = {"filename": "x.txt", "body": {"data": _b64("x")}}
        with (
            patch(
                "quack_core.integrations.google.mail.operations.email.standalone.get_file_info"
            ) as mock_info,
            patch(
                "quack_core.integrations.google.mail.operations.email.standalone.create_directory"
            ) as mock_mkdir,
        ):
            mock_info.return_value = MagicMock(success=True, exists=False)
            mock_mkdir.return_value = MagicMock(success=False)
            result = email.handle_attachment(
                mock_gmail_service, "me", part, "msg1", str(storage_dir), logger
            )
        assert result is None

    def test_write_failure_returns_none(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        part = {"filename": "x.txt", "body": {"data": _b64("x")}}
        with (
            patch(
                "quack_core.integrations.google.mail.operations.email.standalone.get_file_info"
            ) as mock_info,
            patch(
                "quack_core.integrations.google.mail.operations.email.standalone.create_directory"
            ) as mock_mkdir,
            patch(
                "quack_core.integrations.google.mail.operations.email.standalone.write_binary"
            ) as mock_write,
        ):
            mock_info.return_value = MagicMock(success=True, exists=False)
            mock_mkdir.return_value = MagicMock(success=True)
            mock_write.return_value = MagicMock(success=False, error="disk full")
            result = email.handle_attachment(
                mock_gmail_service, "me", part, "msg1", str(storage_dir), logger
            )
        assert result is None

    def test_unexpected_exception_caught_and_returns_none(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        part = {"filename": "x.txt", "body": {"data": _b64("x")}}
        with patch(
            "quack_core.integrations.google.mail.operations.email.standalone.get_file_info",
            side_effect=RuntimeError("boom"),
        ):
            result = email.handle_attachment(
                mock_gmail_service, "me", part, "msg1", str(storage_dir), logger
            )
        assert result is None

    def test_join_path_result_is_stringified_not_unwrapped_bug(self) -> None:
        """PINS A REAL PRODUCTION BUG, found while writing this coverage
        pass -- NOT fixed here, per this stream's charter (a ruling must
        authorize any production fix).

        Two call sites in this file -- handle_attachment (line 396) and
        download_email (line 178) -- do:
            file_path = str(standalone.join_path(storage_path, clean_name))
        standalone.join_path returns a DataResult[str] (core/fs/results.py),
        a pydantic BaseModel with NO custom __str__ -- so str(...) on it
        does not give the joined path, it gives pydantic's default
        field-dump repr:
          "ok=True path=PosixPath(...) message='Joined paths' ...
          data='/actual/path' format='path' ..."
        The correct unwrap is `.data`, exactly as _resolve_download_path in
        google/drive/service.py does it (RULING-238/240's fix to this same
        disease shape -- a core/fs Result-wrapping return value handled as
        if it were the raw unwrapped value).

        Verified directly against real, unmocked join_path (run from this
        investigation, output captured here for the record -- this test
        reproduces the identical unwrap bug deterministically without
        touching the real filesystem, by asserting on DataResult's actual
        __str__ contract rather than re-running the sandboxed call):

            >>> from quack_core.core.fs.service import standalone
            >>> str(standalone.join_path("foo", "bar.txt"))
            "ok=True path=PosixPath('.../foo/bar.txt') message='Joined paths'
            ... data='.../foo/bar.txt' format='path' ..."

        Downstream effect: handle_attachment's and download_email's
        returned "path" is this garbage repr string, not a real filesystem
        path -- any caller that tries to open/read/display it gets
        nonsense, and any write that follows (write_binary/write_text)
        either 403s against the fs sandbox (the observed failure mode when
        the garbage string is long/contains characters the sandbox
        resolver rejects) or -- worse -- silently writes to a bogus
        filename it DOES accept, silently corrupting where the file lands.
        Confirmed by directly invoking the unmocked function during this
        investigation: it produced a file literally named after the
        stringified DataResult repr in the process cwd (see this stream's
        SOW for the exact repro and cleanup note).

        This test does not call handle_attachment/download_email at all --
        it isolates the exact defective expression so it cannot regress
        silently if either call site's mocking style changes later.
        """
        from quack_core.core.fs.service import standalone

        result = standalone.join_path("some_dir", "some_file.txt")

        # The bug: str() on the DataResult does NOT give the joined path.
        stringified = str(result)
        assert stringified != result.data
        assert "data=" in stringified
        assert "ok=" in stringified
        # This is what BOTH buggy call sites actually assign to file_path.
        assert stringified.startswith("ok=")


class TestDownloadEmailWriteFailure:
    """Covers the write_result.success is False branch in download_email
    (lines 196-200), the one remaining uncovered path in that function."""

    @patch("quack_core.integrations.google.mail.operations.email.process_message_parts")
    @patch(
        "quack_core.integrations.google.mail.operations.email._get_message_with_retry"
    )
    def test_write_failure_returns_error_result(
        self,
        mock_get_message: Any,  # noqa: ANN401 -- @patch-injected MagicMock, not the fixture
        mock_process_parts: Any,  # noqa: ANN401 -- @patch-injected MagicMock, not the fixture
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
        storage_dir: Path,
    ) -> None:
        mock_get_message.return_value = {
            "id": "msg1",
            "payload": {"headers": [], "parts": [{"mimeType": "text/html"}]},
        }
        mock_process_parts.return_value = ("<html>content</html>", [])

        with patch(
            "quack_core.integrations.google.mail.operations.email.standalone.write_text"
        ) as mock_write:
            mock_write.return_value.success = False
            mock_write.return_value.error = "disk full"
            result = email.download_email(
                mock_gmail_service,
                "me",
                "msg1",
                str(storage_dir),
                False,
                False,
                3,
                0.1,
                0.5,
                logger,
            )

        assert result.success is False
        assert "Failed to write email content" in result.error


class TestGetMessageWithRetryZeroRetries:
    """Covers the final `return None` after the while-loop exits without
    ever entering it (max_retries=0, line 259)."""

    def test_zero_max_retries_returns_none_without_calling_api(
        self,
        mock_gmail_service: Any,  # noqa: ANN401 -- mock exposes test-only attrs beyond GmailService protocol
        logger: logging.Logger,
    ) -> None:
        with patch(
            "quack_core.integrations.google.mail.operations.email.execute_api_request"
        ) as mock_execute:
            message = email._get_message_with_retry(
                mock_gmail_service, "me", "msg1", 0, 0.1, 0.5, logger
            )
        assert message is None
        mock_execute.assert_not_called()
