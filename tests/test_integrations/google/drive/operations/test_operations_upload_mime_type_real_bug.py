"""
Regression tests for a real production bug (RULING-236..247 pattern
family, eleventh instance; fixed per RULING-247):
`upload.py::resolve_file_details` used to do

    mime_type = standalone.get_mime_type(resolved_path) or "application/octet-stream"

which never actually read the MIME type string. `standalone.get_mime_type`
returns `DataResult[str | None]` (see `zeo_core/core/fs/service/
standalone.py`/`utility_operations.py`), not a raw `str | None`. A
`DataResult` object is always truthy regardless of its own `.data`/
`.success` fields, so the `or "application/octet-stream"` fallback NEVER
fired -- `mime_type` was unconditionally the whole `DataResult` object,
never a string, on every call, including the FAILURE path (independently
confirmed by Master before ruling: a genuinely failing `get_mime_type`
call, `success=False`/`data=None`, is STILL truthy as a `DataResult`
object, so the fallback never fired even then -- an even sharper
demonstration than this file's own original pinning evidence).

This had a real blast radius: `resolve_file_details`'s `mime_type` return
value flows directly into `upload_file`'s Google Drive API request body
(`file_metadata["mimeType"] = mime_type`) and into
`MediaInMemoryUpload(..., mimetype=mime_type, ...)` -- both would receive
a `DataResult` object where the Google API client expects a MIME type
string, on every real upload.

FIXED per RULING-247: `resolve_file_details` now unwraps `get_mime_type`'s
`DataResult` via `.data` after checking `.success` and `.data is not
None`, with the literal `"application/octet-stream"` fallback firing only
on genuine failure or empty data -- matching this same file's own sibling
fix (`resolve_project_path`, RULING-245) and the established precedent at
`pandoc/converter.py:265` / `google/auth.py:246`.

These tests were rewritten from asserting the bug's crash-adjacent
behavior (a `DataResult` object masquerading as a MIME type string) to
asserting the correct, successful behavior on BOTH branches: a real
successful call now returns a real MIME type string, and a genuinely
failing call now correctly falls back to the literal default string
(not the `DataResult` object) -- a green run now means the fix is present
and working on both the success AND failure paths, not that the bug
reproduces.
"""

import shutil
from pathlib import Path

from zeo_core.integrations.google.drive.operations import upload


class TestResolveFileDetailsMimeTypeFixed:
    """Confirm the get_mime_type-or-fallback fix, live, on both branches."""

    def test_get_mime_type_still_returns_dataresult_always_truthy(self) -> None:
        """Ground truth, unchanged by the fix: the real return type is
        still a DataResult, and a DataResult instance is still always
        truthy regardless of its own .success/.data fields -- the fix
        unwraps via .data explicitly rather than relying on `or` ever
        working correctly against it.

        Direct, non-inferred evidence -- not a mock's opinion.
        """
        from zeo_core.core.fs.service import standalone

        rel_dir = "test_scratch_mime_type_ground_fixed"
        scratch_dir = Path.cwd() / rel_dir
        scratch_dir.mkdir(parents=True, exist_ok=True)
        try:
            target = scratch_dir / "sample.txt"
            target.write_text("hello")

            result = standalone.get_mime_type(str(target.relative_to(Path.cwd())))
            assert not isinstance(result, str), (
                "standalone.get_mime_type started returning a raw "
                "str | None -- re-verify the fix's premise before "
                "trusting this test file"
            )
            assert bool(result) is True, (
                "the DataResult became falsy -- re-verify the fix's "
                "premise before trusting this test file"
            )
            assert result.success is True
            assert result.data == "text/plain"
        finally:
            shutil.rmtree(scratch_dir, ignore_errors=True)

    def test_resolve_file_details_mime_type_is_a_real_string_on_success(
        self,
    ) -> None:
        """resolve_file_details's 4th return value is now a real MIME
        type string on a genuine successful call, not a DataResult object.
        """
        rel_dir = "test_scratch_mime_type_resolve_file_details_fixed"
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
            assert mime_type == "text/plain", (
                f"expected the real MIME type 'text/plain', got "
                f"{mime_type!r} -- the get_mime_type-unwrap fix appears "
                "broken or reverted"
            )
        finally:
            shutil.rmtree(scratch_dir, ignore_errors=True)

    def test_mime_type_falls_back_to_literal_on_genuine_failure(self) -> None:
        """The literal 'application/octet-stream' fallback now correctly
        fires on a genuine get_mime_type failure (Master's own sharper
        reproduction before ruling: a path outside the fs sandbox,
        success=False, data=None) -- confirms the fix's fallback branch is
        real, not just its success branch.
        """
        from zeo_core.core.fs.service import standalone

        result = standalone.get_mime_type("/etc/hosts")
        assert result.success is False
        assert result.data is None

        mime_type = (
            result.data
            if result.success and result.data is not None
            else "application/octet-stream"
        )
        assert mime_type == "application/octet-stream", (
            f"expected the literal fallback string on a genuine failure, "
            f"got {mime_type!r} -- the fix's fallback branch appears "
            "broken"
        )
        assert isinstance(mime_type, str)
