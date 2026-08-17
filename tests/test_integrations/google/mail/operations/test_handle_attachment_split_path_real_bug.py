"""
Regression tests for two real production bugs found while investigating a
mypy `[index]` finding in `handle_attachment` (RULING-236..243 pattern
family; fixed per RULING-245), one per module -- they were NOT the same
bug, despite starting from the same mypy error shape.

BUG A -- `google/mail/operations/email.py::handle_attachment` used to NEVER
unwrap `standalone.join_path(...)`'s `DataResult` before using it as a path
(`file_path = str(standalone.join_path(storage_path, clean_name))`).
`str()` of a `DataResult` produces the pydantic model's repr, NOT the path
string. This was UNCONDITIONAL -- it fired on every single call, not just
on a filename collision. FIXED: now checks `.success` and unwraps `.data`,
matching `attachments.py`'s own established pattern.

BUG B -- inside the filename-collision retry loop, BOTH `email.py` and
`attachments.py` used to do `path_parts = standalone.split_path(file_path);
... = path_parts[-1] ...` -- `standalone.split_path` returns
`DataResult[list[str]]`, not a raw `list[str]`, so subscripting it directly
raised `TypeError`, caught by each function's own bare `except Exception`,
silently dropping the attachment. FIXED: both now check `.success` and
unwrap `.data` before subscripting, matching the precedent at
`pandoc/converter.py:265` / `google/auth.py:246`.

Every existing (pre-fix) test for `handle_attachment` mocks the whole
`standalone` module (`mock_fs.split_path.return_value = [...]`, `mock_fs.
join_path.return_value = "/path/to/storage/test.pdf"` -- a raw list/string
in both cases), which masked both bugs. These tests drive the REAL
`standalone` module (no mocking) using an in-sandbox relative scratch
directory (core/fs's `allow_absolute=False` invariant refuses paths outside
the project base dir -- `tmp_path` is outside it, so a relative in-repo
scratch dir is used instead, the same convention `test_mail_service.py`'s
own RULING-238 pinning tests use).

**These tests now assert the CORRECT, FIXED behavior** -- a green run means
the fix is present and working. A future regression back to the old bug
shape would make these fail, not silently pass.
"""

import base64
import logging
import shutil
from pathlib import Path

from quack_core.integrations.google.mail.operations import attachments, email
from quack_core.integrations.google.mail.operations.email import clean_filename
from tests.test_integrations.google.mail.mocks import create_mock_gmail_service


def _make_part(filename: str, content: bytes) -> dict:
    return {
        "filename": filename,
        "body": {"data": base64.urlsafe_b64encode(content).decode()},
    }


class TestEmailHandleAttachmentJoinPathFixed:
    """Bug A fixed: email.py now correctly unwraps join_path's DataResult."""

    def test_join_path_str_is_still_not_a_real_path(self) -> None:
        """Ground truth, unchanged by the fix: str(DataResult) is still the
        model repr, not the path -- the fix unwraps via .data explicitly
        rather than relying on str() ever becoming path-shaped.

        Direct, non-inferred evidence -- not a mock's opinion.
        """
        from quack_core.core.fs.service import standalone

        result = standalone.join_path("some_dir", "file.txt")
        stringified = str(result)
        assert stringified != result.data, (
            "DataResult.__str__ started returning just the path -- "
            "re-verify the fix's premise before trusting this test file"
        )
        assert "success=" in stringified or "ok=" in stringified, (
            "expected the pydantic-model repr shape; if this changed, "
            "re-verify the fix's premise"
        )

    def test_handle_attachment_writes_real_file_on_happy_path(self) -> None:
        """email.handle_attachment on a NON-colliding filename now creates
        the file at the intended location and returns the real path, not a
        DataResult repr string -- this was not a collision-only edge case,
        it fired on every ordinary, first-time attachment save.
        """
        rel_storage = "test_scratch_email_joinpath_fixed"
        storage_dir = Path.cwd() / rel_storage
        if storage_dir.exists():
            shutil.rmtree(storage_dir)
        storage_dir.mkdir(parents=True)
        try:
            filename = "newfile.pdf"
            part = _make_part(filename, b"new attachment content")
            logger = logging.getLogger("test_email_joinpath_fixed")

            result = email.handle_attachment(
                gmail_service=create_mock_gmail_service(),  # unused: data in part body
                user_id="me",
                part=part,
                msg_id="msg123",
                storage_path=str(storage_dir),
                logger=logger,
            )

            expected_name = clean_filename(filename)
            expected_path = storage_dir / expected_name

            assert result == str(expected_path), (
                f"handle_attachment returned {result!r} instead of the "
                f"real intended path {str(expected_path)!r} -- the "
                "join_path-unwrap fix appears broken or reverted"
            )
            assert expected_path.exists(), (
                "the attachment was not actually written to the intended "
                f"path ({expected_path}) -- the join_path-unwrap fix "
                "appears broken or reverted"
            )
            assert expected_path.read_bytes() == b"new attachment content"
        finally:
            shutil.rmtree(storage_dir, ignore_errors=True)


class TestHandleAttachmentSplitPathCollisionFixed:
    """Bug B fixed: split_path's DataResult is now correctly unwrapped in
    the filename-collision retry loop, in both email.py and attachments.py.
    """

    def test_split_path_still_returns_dataresult_not_list(self) -> None:
        """Ground truth, unchanged by the fix: the real return type is
        still not a plain list -- the fix unwraps via .data explicitly.
        """
        from quack_core.core.fs.service import standalone

        result = standalone.split_path("test_scratch_split_path_fixed/file.txt")
        assert not isinstance(result, list), (
            "standalone.split_path started returning a raw list -- "
            "re-verify the fix's premise before trusting this test file"
        )
        assert result.success is True
        assert isinstance(result.data, list)

    def test_email_handle_attachment_deduplicates_on_filename_collision(
        self,
    ) -> None:
        """email.handle_attachment now correctly saves a colliding
        attachment under a de-duplicated name instead of crashing
        internally and silently dropping it (returning None).
        """
        rel_storage = "test_scratch_email_collision_fixed"
        storage_dir = Path.cwd() / rel_storage
        if storage_dir.exists():
            shutil.rmtree(storage_dir)
        storage_dir.mkdir(parents=True)
        try:
            filename = "report.pdf"
            colliding_name = clean_filename(filename)  # "report-pdf"
            (storage_dir / colliding_name).write_bytes(b"pre-existing file")

            part = _make_part(filename, b"new attachment content")
            logger = logging.getLogger("test_email_collision_fixed")

            result = email.handle_attachment(
                gmail_service=create_mock_gmail_service(),  # unused: data in part body
                user_id="me",
                part=part,
                msg_id="msg123",
                storage_path=str(storage_dir),
                logger=logger,
            )

            assert result is not None, (
                "handle_attachment returned None on a real filename "
                "collision -- the split_path DataResult-unwrap fix "
                "appears broken or reverted"
            )
            expected_deduplicated = storage_dir / "report-pdf-1"
            assert result == str(expected_deduplicated), (
                f"expected the de-duplicated path {expected_deduplicated!r}, "
                f"got {result!r}"
            )
            assert Path(result).exists()
            assert Path(result).read_bytes() == b"new attachment content"
            # The pre-existing file must be untouched.
            assert (storage_dir / colliding_name).read_bytes() == b"pre-existing file"
        finally:
            shutil.rmtree(storage_dir, ignore_errors=True)

    def test_attachments_handle_attachment_deduplicates_on_filename_collision(
        self,
    ) -> None:
        """attachments.handle_attachment: same fix, same module family.

        attachments.py already correctly unwrapped its own join_path call
        before this fix -- this isolates Bug B's fix cleanly: the
        pre-existing filename on disk must match clean_filename's OUTPUT
        (it replaces non-alphanumerics with "-", so "report.pdf" ->
        "report-pdf"), or no collision occurs at all and the loop this fix
        lives in never runs.
        """
        rel_storage = "test_scratch_attachments_collision_fixed"
        storage_dir = Path.cwd() / rel_storage
        if storage_dir.exists():
            shutil.rmtree(storage_dir)
        storage_dir.mkdir(parents=True)
        try:
            filename = "report.pdf"
            colliding_name = clean_filename(filename)  # "report-pdf"
            (storage_dir / colliding_name).write_bytes(b"pre-existing file")

            part = _make_part(filename, b"new attachment content")
            logger = logging.getLogger("test_attachments_collision_fixed")

            result = attachments.handle_attachment(
                gmail_service=create_mock_gmail_service(),  # unused: data in part body
                user_id="me",
                part=part,
                msg_id="msg123",
                storage_path=str(storage_dir),
                logger=logger,
            )

            assert result is not None, (
                "handle_attachment returned None on a real filename "
                "collision -- the split_path DataResult-unwrap fix "
                "appears broken or reverted"
            )
            expected_deduplicated = storage_dir / "report-pdf-1"
            assert result == str(expected_deduplicated), (
                f"expected the de-duplicated path {expected_deduplicated!r}, "
                f"got {result!r}"
            )
            assert Path(result).exists()
            assert Path(result).read_bytes() == b"new attachment content"
            assert (storage_dir / colliding_name).read_bytes() == b"pre-existing file"
        finally:
            shutil.rmtree(storage_dir, ignore_errors=True)
