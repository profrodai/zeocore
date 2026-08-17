"""
Regression tests for a real production bug (RULING-236..243 pattern family,
ninth instance; fixed per RULING-245): `download.resolve_download_path` and
`upload.resolve_file_details` used to call `paths_service.
resolve_project_path(...)` directly on the imported MODULE (`from
zeo_core.core.paths import service as paths_service`) instead of on an
instantiated `PathService()`.

`zeo_core.core.paths.service` (the module) has no `resolve_project_path`
attribute -- only `PathService` (the class) does, as an instance method.
Every existing test for these two functions mocks
`...operations.download.paths_service` / `...operations.upload.paths_service`
wholesale with `unittest.mock.patch`, which happily let the mock answer
`resolve_project_path(...)` even though the REAL module has no such
attribute -- masking the bug exactly the way RULING-238/240 documented for
the same shape in `google/config.py` and `google/mail/service.py` (both of
which already carried the fix + an explanatory comment; `drive/operations/
download.py` and `drive/operations/upload.py` were missed by that earlier
fix, which is exactly what this pair of files pins).

FIXED per RULING-245: both call sites now instantiate `paths_service.
PathService()` before calling `.resolve_project_path(...)` on the instance
-- the exact pattern already used in `drive/service.py:229/293`. These
tests were rewritten from asserting the bug's crash (AttributeError) to
asserting the correct, successful behavior -- a green run now means the fix
is present and working, not that the bug reproduces.
"""

from pathlib import Path

from zeo_core.integrations.google.drive.operations import download, upload


class TestResolveProjectPathModuleVsInstanceFixed:
    """Confirm the module-vs-instance `resolve_project_path` fix, live."""

    def test_paths_service_module_has_no_resolve_project_path(self) -> None:
        """Ground truth, unchanged by the fix: the imported MODULE itself
        never gained the attribute -- the fix instantiates PathService
        instead of relying on the module gaining a free function.

        This is the direct, non-inferred evidence -- not a mock's opinion.
        """
        from zeo_core.core.paths import service as paths_service

        assert not hasattr(paths_service, "resolve_project_path"), (
            "zeo_core.core.paths.service gained a module-level "
            "resolve_project_path -- re-verify the fix's premise (it "
            "should still be instantiating PathService explicitly, not "
            "relying on this)"
        )
        assert hasattr(paths_service, "PathService"), (
            "PathService class itself went missing -- re-verify the fix's "
            "premise before trusting this test file"
        )

    def test_resolve_download_path_succeeds_with_real_local_path(self) -> None:
        """download.resolve_download_path(..., local_path=...) now
        succeeds instead of raising AttributeError.

        Passing a non-None local_path drives execution into the
        previously-buggy `paths_service.resolve_project_path(local_path)`
        call at download.py -- now correctly instantiates PathService
        first.
        """
        file_metadata = {"name": "report.pdf"}
        result = download.resolve_download_path(
            file_metadata, local_path="some/local/dir"
        )
        assert result.endswith("some/local/dir") or result.endswith(
            "some/local/dir/report.pdf"
        ), (
            f"expected a real resolved path derived from 'some/local/dir', "
            f"got {result!r}"
        )
        assert "AttributeError" not in result

    def test_resolve_file_details_succeeds_or_fails_on_missing_file_not_attribute_error(
        self,
    ) -> None:
        """upload.resolve_file_details(...) now correctly reaches the
        file-existence check (raising ZeoIntegrationError for a genuinely
        missing file) instead of crashing on the module-vs-instance
        AttributeError before ever getting there.
        """
        from zeo_core.core.errors import ZeoIntegrationError

        try:
            path_obj, filename, folder_id, mime_type = upload.resolve_file_details(
                file_path="some/file/to/upload/that/does/not/exist.txt",
                remote_path=None,
                parent_folder_id=None,
            )
            raise AssertionError(
                "expected ZeoIntegrationError for a nonexistent file, got "
                f"a successful result instead: {path_obj!r}"
            )
        except ZeoIntegrationError as e:
            # The correct failure mode now: resolve_project_path succeeded
            # (no AttributeError), and the function reached its own
            # explicit file-not-found check.
            assert "File not found" in str(e), (
                f"expected the file-not-found ZeoIntegrationError, got a "
                f"differently-shaped ZeoIntegrationError instead: {e}"
            )

    def test_resolve_file_details_succeeds_for_a_real_existing_file(
        self, tmp_path: Path
    ) -> None:
        """Full happy-path proof: a real, existing file resolves correctly
        end-to-end through the fixed resolve_project_path call.
        """
        # Use an in-sandbox relative path (core/fs allow_absolute=False
        # invariant), same convention as this round's other pinning tests.
        rel_dir = "test_scratch_upload_resolve_fixed"
        scratch_dir = Path.cwd() / rel_dir
        scratch_dir.mkdir(parents=True, exist_ok=True)
        try:
            target = scratch_dir / "real_upload_target.txt"
            target.write_text("content")

            path_obj, filename, folder_id, mime_type = upload.resolve_file_details(
                file_path=str(target.relative_to(Path.cwd())),
                remote_path=None,
                parent_folder_id="some-folder-id",
            )
            assert filename == "real_upload_target.txt"
            assert folder_id == "some-folder-id"
        finally:
            import shutil

            shutil.rmtree(scratch_dir, ignore_errors=True)
