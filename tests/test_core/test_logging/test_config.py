"""
Tests for zeo_core.core.logging.config.configure_logger's log_file branch.

RULING-242: configure_logger crashed 100% of the time whenever log_file was
set, because standalone.split_path(log_file) returns a DataResult[list[str]]
object, not a bare list, and the old code subscripted the DataResult
directly (`parts[:-1]`) -- `TypeError: 'DataResult' object is not
subscriptable`. The one pre-existing test that exercises this branch
(test_config/test_models.py) mocks configure_logger ENTIRELY, so the real
standalone.split_path/join_path/create_directory return shapes were never
exercised. These tests use the REAL filesystem service (no mocking of
configure_logger or the fs standalone module) and assert a FileHandler is
actually attached and actually writes -- not just that no exception fires.
"""

import logging
from pathlib import Path

import pytest
from zeo_core.core.logging.config import configure_logger


class TestConfigureLoggerFileHandler:
    """Real, non-mocked coverage of configure_logger's log_file branch."""

    def test_configure_logger_attaches_real_file_handler(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A FileHandler is actually attached and actually writes to disk.

        Regression test for RULING-242. Before the fix, this call raised
        TypeError: 'DataResult' object is not subscriptable on the
        `parts = standalone.split_path(log_file); parent_parts = parts[:-1]`
        line, for every caller that set log_file (which is every real
        caller -- ModelConfig.setup_logging and setup_tool_logging both
        always pass one).
        """
        # The fs service's singleton base_dir defaults to Path.cwd(); chdir
        # into tmp_path so a relative log_file resolves (and sandboxes)
        # inside a real, disposable directory -- no mocking of the fs layer.
        monkeypatch.chdir(tmp_path)

        logger = configure_logger(
            "ruling242_test_logger",
            log_file="nested/logdir/app.log",
            force=True,
        )

        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1, (
            f"expected exactly one FileHandler, got handlers={logger.handlers!r}"
        )

        # The parent directory must have actually been created by the
        # split_path/join_path/create_directory chain, not just have
        # avoided crashing.
        expected_path = tmp_path / "nested" / "logdir" / "app.log"
        assert Path(file_handlers[0].baseFilename) == expected_path.resolve()
        assert expected_path.parent.is_dir()

        # Behavioral proof, not just presence: a real log line must reach
        # the real file.
        logger.info("ruling242 real write check")
        for h in logger.handlers:
            h.flush()
        content = expected_path.read_text()
        assert "ruling242 real write check" in content

        # Cleanup: close handlers so the FileHandler doesn't hold the fd
        # open past the test (tmp_path is auto-cleaned by pytest, but a
        # held-open handle on a removed dir is its own footgun).
        for h in list(logger.handlers):
            logger.removeHandler(h)
            h.close()

    def test_configure_logger_no_log_file_has_no_file_handler(self) -> None:
        """Sanity check: the console-only path (log_file=None) is unaffected.

        Confirms the fix didn't widen behavior for the branch that was
        never broken -- configure_logger(log_file=None) must still attach
        zero FileHandlers.
        """
        logger = configure_logger("ruling242_console_only_logger", force=True)
        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert file_handlers == []

        for h in list(logger.handlers):
            logger.removeHandler(h)
            h.close()

    def test_configure_logger_log_file_outside_sandbox_degrades_not_crashes(
        self, tmp_path: Path
    ) -> None:
        """A split_path failure (e.g. path outside the fs sandbox) must not
        raise TypeError -- it must degrade to "no parent dir pre-created"
        and let FileHandler raise its own clear error (if the target dir
        genuinely doesn't exist), per the fix's documented fallback
        (config.py's inline comment on the fix).

        This exercises the split_result.ok is False branch live: an
        absolute path outside the fs service's base_dir is rejected by the
        real sandbox (core/fs's allowed-roots invariant), confirmed via a
        direct standalone.split_path call returning ok=False for exactly
        this shape. The target directory here is a NESTED, never-created
        subdirectory of tmp_path (not tmp_path itself, which pytest already
        creates) so a real FileNotFoundError is forced from FileHandler,
        proving the fix's fallback genuinely skips parent-dir creation
        rather than silently succeeding for an unrelated reason.
        """
        outside_path = str(
            tmp_path / "never_created_subdir" / "definitely_outside_cwd_sandbox.log"
        )

        # Must NOT raise TypeError (the RULING-242 bug). It's allowed to
        # raise FileNotFoundError/OSError from the real FileHandler once
        # split_path's failure correctly short-circuits parent-dir
        # creation -- that is honest behavior, not a crash on a DataResult.
        with pytest.raises(Exception) as exc_info:
            configure_logger(
                "ruling242_outside_sandbox_logger",
                log_file=outside_path,
                force=True,
            )
        assert not isinstance(exc_info.value, TypeError), (
            "configure_logger must not raise TypeError on a DataResult "
            "subscript -- that is exactly the RULING-242 regression"
        )
        assert isinstance(exc_info.value, OSError), (
            f"expected the real FileHandler to fail with an OSError "
            f"(FileNotFoundError) once parent-dir creation was correctly "
            f"skipped -- got {type(exc_info.value)}: {exc_info.value}"
        )
