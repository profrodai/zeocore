# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/mail/operations/test_handle_attachment_split_path_real_bug.py  # noqa: E501
# === QV-LLM:END ===

"""
Pinning tests for two real production bugs found while investigating a
mypy `[index]` finding in `handle_attachment` (RULING-236..243 pattern
family), one per module -- they are NOT the same bug, despite starting
from the same mypy error shape.

BUG A -- `google/mail/operations/email.py::handle_attachment` NEVER unwraps
`standalone.join_path(...)`'s `DataResult` before using it as a path
(line 396: `file_path = str(standalone.join_path(storage_path, clean_name))`).
`str()` of a `DataResult` produces the pydantic model's repr
(`"ok=True path=... message='Joined paths' ... data='/real/path' ..."`), NOT
the path string. This is UNCONDITIONAL -- it fires on every single call,
not just on a filename collision. Confirmed live: `handle_attachment` on a
brand-new (non-colliding) filename returns the repr string as its "success"
result and does not create the intended file at the intended location
(`write_binary` is instead called against the mangled repr-derived string).
Any caller that does `if attachment_path: attachments.append(attachment_path)`
(exactly what `process_message_parts` in the same file does) records a
garbage non-path string as a successfully-saved attachment path.

BUG B -- inside the (rarely reached, but real) filename-collision retry
loop, BOTH `email.py` and `attachments.py` do:

    path_parts = standalone.split_path(file_path)
    ... = path_parts[-1] ...

`standalone.split_path` returns `DataResult[list[str]]` (see
`quack_core/core/fs/service/standalone.py:131`), not a raw `list[str]`.
`DataResult` is NOT subscriptable -- `path_parts[-1]` raises `TypeError`,
caught by each function's own bare `except Exception`, so the attachment is
silently dropped (returns `None`) instead of saved under a de-duplicated
name. The correct unwrap (`.data` after checking `.success`) is already
used correctly for `split_path` elsewhere in the codebase
(`pandoc/converter.py:265`, `google/auth.py:246` -- `split_result.data[-1]`),
so the fix has a clean, well-precedented shape. Note `attachments.py`
(unlike `email.py`) DOES correctly unwrap its own `join_path` call a few
lines above Bug B's site -- Bug B is an isolated miss in an otherwise-correct
unwrap pass, not evidence of the same root cause as Bug A.

Every existing test for `handle_attachment` mocks the whole `standalone`
module (`mock_fs.split_path.return_value = [...]`, `mock_fs.join_path.
return_value = "/path/to/storage/test.pdf"` -- a raw list/string in both
cases), which masks BOTH bugs: the mocks return what the code WISHES the
real functions returned, not what they actually return.

These tests drive the REAL `standalone` module (no mocking) using an
in-sandbox relative scratch directory (core/fs's `allow_absolute=False`
invariant refuses paths outside the project base dir -- `tmp_path` is
outside it, so a relative in-repo scratch dir is used instead, the same
convention `test_mail_service.py`'s own RULING-238 pinning tests use).

**These tests currently PASS by pinning the BUG'S OBSERVED (WRONG)
behavior** -- they assert what the broken code actually does today (a
mismatched/garbage return value for Bug A, a `None` return for Bug B), not
what it should do. This keeps `make test-fast` green while the fix awaits
a Master ruling (the same posture RULING-242's own escalation used: a
`FINDING`, not a `SHIPPED`, ledger entry). Each test's docstring says
explicitly it must be REWRITTEN to a positive assertion once the
authorized fix lands -- a future green run of these exact assertions is
proof the bug is STILL PRESENT, not proof anything works.
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


class TestEmailHandleAttachmentJoinPathNotUnwrapped:
    """Bug A: email.py never unwraps join_path's DataResult -- unconditional."""

    def test_join_path_str_is_not_a_real_path(self) -> None:
        """Ground the bug: str(DataResult) is the model repr, not the path.

        Direct, non-inferred evidence -- not a mock's opinion.
        """
        from quack_core.core.fs.service import standalone

        result = standalone.join_path("some_dir", "file.txt")
        stringified = str(result)
        assert stringified != result.data, (
            "if this now passes, DataResult.__str__ started returning just "
            "the path -- re-verify the bug's premise before trusting this "
            "test file"
        )
        assert "success=" in stringified or "ok=" in stringified, (
            "expected the pydantic-model repr shape; if this changed, "
            "re-verify the bug's premise"
        )

    def test_handle_attachment_does_not_write_file_on_happy_path(self) -> None:
        """PINS THE BUG'S CURRENT (WRONG) BEHAVIOR -- this test passes
        against today's broken code and MUST be rewritten to assert the
        correct behavior (result == the real intended path, file exists)
        the moment RULING-authorized fix lands; a green run of the
        assertions below is proof the bug is STILL PRESENT, not proof
        anything works.

        email.handle_attachment on a NON-colliding filename still fails to
        create the file at the intended location and returns a garbage
        repr string instead of a real path -- this is not a collision-only
        edge case, it fires on ordinary, first-time attachment saves.
        """
        rel_storage = "test_scratch_email_joinpath_bug"
        storage_dir = Path.cwd() / rel_storage
        if storage_dir.exists():
            shutil.rmtree(storage_dir)
        storage_dir.mkdir(parents=True)
        try:
            filename = "newfile.pdf"
            part = _make_part(filename, b"new attachment content")
            logger = logging.getLogger("test_email_joinpath_bug")

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

            # BUG, pinned as observed: result is the DataResult repr, not
            # the real path, and no file lands at the intended location.
            assert result != str(expected_path), (
                "handle_attachment now returns the real intended path -- "
                "the join_path-unwrap bug appears FIXED; replace this "
                "test with a positive assertion (result == real path, "
                "file exists) instead of this negative pin"
            )
            assert not expected_path.exists(), (
                "the attachment now lands at the intended path -- the "
                "join_path-unwrap bug appears FIXED; replace this test "
                "with a positive assertion instead of this negative pin"
            )
        finally:
            shutil.rmtree(storage_dir, ignore_errors=True)


class TestHandleAttachmentSplitPathCollisionBug:
    """Bug B: split_path's DataResult is subscripted directly in the
    filename-collision retry loop, in both email.py and attachments.py."""

    def test_split_path_returns_dataresult_not_list(self) -> None:
        """Ground the bug: the real return type is not a plain list."""
        from quack_core.core.fs.service import standalone

        result = standalone.split_path("test_scratch_split_path_bug/file.txt")
        assert not isinstance(result, list), (
            "if this now passes, standalone.split_path started returning a "
            "raw list -- re-verify the bug's premise before trusting this "
            "test file"
        )
        try:
            result[-1]  # type: ignore[index]  # deliberately reproduces the bug
            raise AssertionError(
                "DataResult became subscriptable -- re-verify the bug's "
                "premise before trusting this test file"
            )
        except TypeError as e:
            assert "not subscriptable" in str(e)

    def test_attachments_handle_attachment_drops_attachment_on_filename_collision(
        self,
    ) -> None:
        """attachments.handle_attachment silently drops the attachment
        (returns None) when the target filename already exists, instead of
        saving it under a de-duplicated name.

        PINS THE BUG'S CURRENT (WRONG) BEHAVIOR -- this test passes against
        today's broken code and MUST be rewritten to assert the correct
        behavior (result is a real de-duplicated path) the moment a
        RULING-authorized fix lands; a green run of the assertion below is
        proof the bug is STILL PRESENT, not proof anything works.

        attachments.py correctly unwraps join_path (unlike email.py), so
        this isolates Bug B cleanly: the pre-existing filename on disk must
        match clean_filename's OUTPUT (it replaces non-alphanumerics with
        "-", so "report.pdf" -> "report-pdf"), or no collision occurs at
        all and the loop this bug lives in never runs.
        """
        rel_storage = "test_scratch_attachments_collision_bug"
        storage_dir = Path.cwd() / rel_storage
        if storage_dir.exists():
            shutil.rmtree(storage_dir)
        storage_dir.mkdir(parents=True)
        try:
            filename = "report.pdf"
            colliding_name = clean_filename(filename)  # "report-pdf"
            (storage_dir / colliding_name).write_bytes(b"pre-existing file")

            part = _make_part(filename, b"new attachment content")
            logger = logging.getLogger("test_attachments_collision_bug")

            result = attachments.handle_attachment(
                gmail_service=create_mock_gmail_service(),  # unused: data in part body
                user_id="me",
                part=part,
                msg_id="msg123",
                storage_path=str(storage_dir),
                logger=logger,
            )

            # BUG, pinned as observed: the TypeError from path_parts[-1] is
            # caught by the function's own bare `except Exception`, so it
            # returns None (attachment silently dropped) instead of a
            # de-duplicated saved path.
            assert result is None, (
                "handle_attachment no longer returns None on a real "
                "filename collision -- the split_path DataResult-unwrap "
                "bug appears FIXED; replace this test with a positive "
                "assertion (result is a real de-duplicated path) instead "
                "of this negative pin"
            )
        finally:
            shutil.rmtree(storage_dir, ignore_errors=True)
