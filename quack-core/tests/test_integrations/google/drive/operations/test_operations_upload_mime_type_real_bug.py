# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/operations/test_operations_upload_mime_type_real_bug.py  # noqa: E501
# === QV-LLM:END ===

"""
Pinning test for a real production bug (RULING-236..245 pattern family,
eleventh instance): `upload.py::resolve_file_details`'s

    mime_type = standalone.get_mime_type(resolved_path) or "application/octet-stream"

never actually reads the MIME type string. `standalone.get_mime_type`
returns `DataResult[str | None]` (see `quack_core/core/fs/service/
standalone.py`/`utility_operations.py`), not a raw `str | None`. A
`DataResult` object is always truthy regardless of its own `.data`/
`.success` fields, so the `or "application/octet-stream"` fallback NEVER
fires -- `mime_type` is unconditionally the whole `DataResult` object,
never a string, on every successful call. Found while investigating this
same file's already-fixed `resolve_project_path` module-vs-instance bug
(RULING-245) -- a distinct bug at a distinct call site in the same
function, not touched by that fix.

This is unconditional (not gated behind any error branch) and has a real
blast radius: `resolve_file_details`'s `mime_type` return value flows
directly into `upload_file`'s Google Drive API request body
(`file_metadata["mimeType"] = mime_type`) and into
`MediaInMemoryUpload(..., mimetype=mime_type, ...)` -- both would receive
a `DataResult` object where the Google API client expects a MIME type
string, on every real upload.

The existing test (`test_operations_upload.py::test_resolve_file_details`)
mocks `quack_core.core.fs.service.standalone.get_mime_type` directly and
sets `mock_mime.return_value = "text/plain"` -- a raw string, masking the
bug exactly the way every prior generation of this pattern has been
masked: the mock returns what the code WISHES the real function returned,
not what it actually returns.

This test drives the REAL `standalone.get_mime_type` (no mocking) against
a real file on disk, using an in-sandbox relative scratch dir (core/fs's
`allow_absolute=False` invariant), the same convention every prior pinning
test in this round has used. NOT fixed here -- same discipline as every
prior generation of this pattern (RULING-236 through RULING-245): pinned
live, ruling requested, not fixed unilaterally, since the fix changes a
return-value contract flowing directly into two external Google Drive API
calls.
"""

import shutil
from pathlib import Path

from quack_core.integrations.google.drive.operations import upload


class TestResolveFileDetailsMimeTypeTruthyOrBug:
    """Pin the get_mime_type-or-fallback-never-fires bug, live."""

    def test_get_mime_type_returns_dataresult_always_truthy(self) -> None:
        """Ground the bug: the real return type is a DataResult, and a
        DataResult instance is always truthy regardless of its own
        .success/.data fields -- so `x or fallback` can never reach the
        fallback branch.

        Direct, non-inferred evidence -- not a mock's opinion.
        """
        from quack_core.core.fs.service import standalone

        rel_dir = "test_scratch_mime_type_ground"
        scratch_dir = Path.cwd() / rel_dir
        scratch_dir.mkdir(parents=True, exist_ok=True)
        try:
            target = scratch_dir / "sample.txt"
            target.write_text("hello")

            result = standalone.get_mime_type(str(target.relative_to(Path.cwd())))
            assert not isinstance(result, str), (
                "if this now passes, standalone.get_mime_type started "
                "returning a raw str | None -- re-verify the bug's premise "
                "before trusting this test file"
            )
            assert bool(result) is True, (
                "if this now passes (the DataResult became falsy), the "
                "or-fallback bug's premise may no longer hold -- re-verify "
                "before trusting this test file"
            )
        finally:
            shutil.rmtree(scratch_dir, ignore_errors=True)

    def test_resolve_file_details_mime_type_is_not_a_string(self) -> None:
        """PINS THE BUG'S CURRENT (WRONG) BEHAVIOR -- this test passes
        against today's broken code and MUST be rewritten to assert
        `mime_type` is a real string (e.g. `mime_type == "text/plain"`)
        the moment a RULING-authorized fix lands; a green run of the
        assertion below is proof the bug is STILL PRESENT, not proof
        anything works.

        resolve_file_details's 4th return value (documented as "MIME type
        as strings") is actually the whole DataResult object on every real,
        non-mocked call -- confirmed against a real file, no mocking of
        standalone at all.
        """
        rel_dir = "test_scratch_mime_type_resolve_file_details"
        scratch_dir = Path.cwd() / rel_dir
        scratch_dir.mkdir(parents=True, exist_ok=True)
        try:
            target = scratch_dir / "upload_target.txt"
            target.write_text("upload content")

            _path_obj, filename, _folder_id, mime_type = upload.resolve_file_details(
                file_path=str(target.relative_to(Path.cwd())),
                remote_path=None,
                parent_folder_id=None,
            )

            assert filename == "upload_target.txt"
            # BUG, pinned as observed: mime_type is a DataResult object,
            # not the real MIME type string ("text/plain").
            assert not isinstance(mime_type, str), (
                "resolve_file_details now returns a real string mime_type "
                "-- the get_mime_type-or-fallback bug appears FIXED; "
                "replace this test with a positive assertion "
                "(mime_type == 'text/plain') instead of this negative pin"
            )
        finally:
            shutil.rmtree(scratch_dir, ignore_errors=True)
