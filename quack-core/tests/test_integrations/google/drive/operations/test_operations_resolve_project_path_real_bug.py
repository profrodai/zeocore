# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/operations/test_operations_resolve_project_path_real_bug.py  # noqa: E501
# === QV-LLM:END ===

"""
Pinning tests for a real production bug (RULING-236..243 pattern, ~ninth
instance): `download.resolve_download_path` and `upload.resolve_file_details`
call `paths_service.resolve_project_path(...)` directly on the imported
MODULE (`from quack_core.core.paths import service as paths_service`)
instead of on an instantiated `PathService()`.

`quack_core.core.paths.service` (the module) has no `resolve_project_path`
attribute -- only `PathService` (the class) does, as an instance method.
Every existing test for these two functions mocks
`...operations.download.paths_service` / `...operations.upload.paths_service`
wholesale with `unittest.mock.patch`, which happily lets the mock answer
`resolve_project_path(...)` even though the REAL module has no such
attribute -- masking the bug exactly the way RULING-238/240 documented for
the same shape in `google/config.py` and `google/mail/service.py` (both of
which carry the fix + an explanatory comment; `drive/operations/download.py`
and `drive/operations/upload.py` were missed).

These tests do NOT patch `paths_service` -- they call the real module so the
real `AttributeError` surfaces. Each test asserts the AttributeError IS
raised (`pytest.raises`), so they PASS today, pinning the bug's current
(broken) behavior and keeping `make test-fast` green while the fix awaits
a Master ruling. Once the authorized fix lands (instantiate
`paths_service.PathService()`, then call `.resolve_project_path(...)` on
the instance -- the exact pattern already used in
`drive/service.py:229/293`), these tests will start FAILING (no exception
raised) and must be rewritten to assert the correct, successful return
value instead.
"""

import pytest
from quack_core.integrations.google.drive.operations import download, upload


class TestResolveProjectPathModuleVsInstanceBug:
    """Pin the module-vs-instance `resolve_project_path` crash, live."""

    def test_paths_service_module_has_no_resolve_project_path(self) -> None:
        """Ground the bug: the imported module itself lacks the attribute.

        This is the direct, non-inferred evidence -- not a mock's opinion.
        """
        from quack_core.core.paths import service as paths_service

        assert not hasattr(paths_service, "resolve_project_path"), (
            "if this now passes, quack_core.core.paths.service gained a "
            "module-level resolve_project_path and the bug below may already "
            "be fixed by a different mechanism -- re-verify before trusting "
            "this test file's premise"
        )

    def test_resolve_download_path_crashes_with_real_local_path(self) -> None:
        """download.resolve_download_path(..., local_path=...) crashes.

        Passing a non-None local_path drives execution into the buggy
        `paths_service.resolve_project_path(local_path)` module-level call
        at download.py:53.
        """
        file_metadata = {"name": "report.pdf"}
        with pytest.raises(AttributeError, match="resolve_project_path"):
            download.resolve_download_path(
                file_metadata, local_path="some/local/dir"
            )

    def test_resolve_file_details_crashes_on_real_call(self) -> None:
        """upload.resolve_file_details(...) crashes on the same shape.

        upload.py:73 calls `paths_service.resolve_project_path(file_path)`
        directly on the module -- same AttributeError, first line of the
        function body, before any file-existence check even runs.
        """
        with pytest.raises(AttributeError, match="resolve_project_path"):
            upload.resolve_file_details(
                file_path="some/file/to/upload.txt",
                remote_path=None,
                parent_folder_id=None,
            )
