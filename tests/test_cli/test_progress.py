# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_cli/test_progress.py
# role: tests
# neighbors: __init__.py, mocks.py, test_bootstrap.py, test_config.py, test_context.py, test_error.py (+5 more)
# exports: TestProgressReporter, TestSimpleProgress, TestShowProgress, TestProgressCallback
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

"""
Tests for the CLI progress module.
"""

import itertools
import time
from io import StringIO, TextIOBase
from unittest.mock import MagicMock, patch

import pytest
from quack_core.interfaces.cli.utils.progress import (
    ProgressReporter,
    SimpleProgress,
    show_progress,
)


class TestProgressReporter:
    """Tests for the ProgressReporter class."""

    def test_initialization(self) -> None:
        """Test initialization of ProgressReporter."""
        # Test with default values
        reporter = ProgressReporter()
        assert reporter.total is None
        assert reporter.desc == "Progress"
        assert reporter.unit == "it"
        assert reporter.current == 0
        assert reporter.show_eta is True
        assert isinstance(reporter.file, TextIOBase)
        assert reporter.start_time is None
        assert reporter.last_update_time is None
        assert reporter.callbacks == []

        # Test with custom values
        file_obj = StringIO()
        reporter = ProgressReporter(
            total=100,
            desc="Custom Progress",
            unit="files",
            show_eta=False,
            file=file_obj,
        )
        assert reporter.total == 100
        assert reporter.desc == "Custom Progress"
        assert reporter.unit == "files"
        assert reporter.show_eta is False
        assert reporter.file is file_obj

    def test_start(self) -> None:
        """Test start method."""
        reporter = ProgressReporter()

        with patch.object(reporter, "_draw") as mock_draw:
            with patch("time.time", return_value=123456.0):
                reporter.start()

                assert reporter.start_time == 123456.0
                assert reporter.last_update_time == 123456.0
                assert reporter.current == 0
                mock_draw.assert_called_once()

    def test_update(self) -> None:
        """Test update method with various parameters."""
        reporter = ProgressReporter()
        reporter.start_time = 123456.0
        reporter.last_update_time = 123456.0

        # Test with incremental update
        with patch.object(reporter, "_draw") as mock_draw:
            with patch("time.time", return_value=123456.1):
                reporter.update()
                assert reporter.current == 1
                assert reporter.last_update_time == 123456.1
                mock_draw.assert_called_once_with(None)

        # Test with explicit current value
        with patch.object(reporter, "_draw") as mock_draw:
            with patch("time.time", return_value=123456.2):
                reporter.update(current=10, message="Custom message")
                assert reporter.current == 10
                assert reporter.last_update_time == 123456.2
                mock_draw.assert_called_once_with("Custom message")

        # Test with callback
        callback = MagicMock()
        reporter.add_callback(callback)

        with patch.object(reporter, "_draw"):
            with patch("time.time", return_value=123456.3):
                reporter.update(message="Test callback")
                callback.assert_called_once_with(11, None, "Test callback")

    def test_finish(self) -> None:
        """Test finish method."""
        file_obj = StringIO()
        reporter = ProgressReporter(file=file_obj)
        reporter.current = 50

        with patch.object(reporter, "update") as mock_update:
            reporter.finish(message="Finished")

            # If total was None, it should be set to current
            assert reporter.total == 50
            # update should be called with total
            mock_update.assert_called_once_with(50, "Finished")

        # Should write a newline to the file
        assert file_obj.getvalue().endswith("\n")

        # Test with preset total
        file_obj = StringIO()
        reporter = ProgressReporter(total=100, file=file_obj)
        reporter.current = 50

        with patch.object(reporter, "update") as mock_update:
            reporter.finish()

            # update should be called with the preset total
            mock_update.assert_called_once_with(100, None)

    def test_add_callback(self) -> None:
        """Test adding a callback."""
        reporter = ProgressReporter()
        callback = MagicMock()

        reporter.add_callback(callback)
        assert callback in reporter.callbacks

        # Test that added callback gets called
        with patch.object(reporter, "_draw"):
            with patch("time.time", return_value=123456.0):
                reporter.update(message="Test callback")
                callback.assert_called_once_with(1, None, "Test callback")

    def test_draw(self) -> None:
        """Test _draw method with various scenarios."""
        # Test with known total (percentage-based progress)
        file_obj = StringIO()
        reporter = ProgressReporter(total=100, file=file_obj)
        reporter.current = 50
        reporter.start_time = time.time() - 10  # Started 10 seconds ago

        # The test is expecting to find this exact message in the output
        message = "Half done"

        with patch("quack_core.interfaces.cli.utils.terminal.get_terminal_size") as mock_get_size:
            # Use a wider terminal width to ensure message fits
            mock_get_size.return_value = (200, 24)

            # Call _draw with the message
            reporter._draw(message)

            # Get the output and print it for debugging
            output = file_obj.getvalue()
            print(f"Debug - Actual output: {repr(output)}")

            # Check output contains expected elements
            assert "Progress: 50/100" in output
            assert "it" in output  # Default unit
            assert message in output, (
                f"Message '{message}' not found in output: {repr(output)}"
            )
            assert "[" in output  # Progress bar

        # Test with unknown total (spinner-based progress)
        file_obj = StringIO()
        reporter = ProgressReporter(file=file_obj)
        reporter.current = 10

        with patch("quack_core.interfaces.cli.utils.terminal.get_terminal_size") as mock_get_size:
            with patch.object(
                itertools, "cycle", return_value=iter(["-", "\\", "|", "/"])
            ):
                mock_get_size.return_value = (80, 24)

                # Call _draw
                reporter._draw("Working")
                output = file_obj.getvalue()

                # Check output contains expected elements
                assert "Progress: 10" in output
                assert "it" in output  # Default unit
                assert "Working" in output
                assert "-" in output  # First spinner character

        # Test without TTY
        file_obj = MagicMock()
        reporter = ProgressReporter(file=file_obj)

        # Ensure mocking is done correctly
        with patch("quack_core.interfaces.cli.utils.terminal.get_terminal_size", return_value=(80, 24)):
            reporter._draw()
            # Should still write something
            file_obj.write.assert_called_once()
            file_obj.flush.assert_called_once()


class TestSimpleProgress:
    """Tests for the SimpleProgress class."""

    def test_initialization(self) -> None:
        """Test initialization of SimpleProgress."""
        iterable = range(10)

        with patch.object(ProgressReporter, "start") as mock_start:
            progress = SimpleProgress(iterable)

            assert progress.iterable is not iterable  # Should create a new iterator
            assert progress.total == 10  # Should get length from iterable
            assert isinstance(progress.reporter, ProgressReporter)
            mock_start.assert_called_once()

        # Test with custom parameters
        with patch.object(ProgressReporter, "start") as mock_start:
            progress = SimpleProgress(
                iterable, total=20, desc="Custom Progress", unit="steps"
            )

            assert progress.total == 20  # Should use provided total
            assert progress.reporter.desc == "Custom Progress"
            assert progress.reporter.unit == "steps"
            mock_start.assert_called_once()

        # Test with iterable without __len__
        class CustomIterable:
            def __iter__(self):
                return iter(range(5))

        with patch.object(ProgressReporter, "start") as mock_start:
            progress = SimpleProgress(CustomIterable())

            assert progress.total is None  # Total should be None
            mock_start.assert_called_once()

    def test_iteration(self) -> None:
        """Test iteration behavior."""
        iterable = [1, 2, 3, 4, 5]

        # Use StringIO to capture the output
        file_obj = StringIO()

        with patch("sys.stdout", file_obj):
            progress = SimpleProgress(iterable)

            # Replace the reporter with a mock to verify calls
            mock_reporter = MagicMock()
            progress.reporter = mock_reporter

            # Iterate over the progress wrapper
            collected = list(progress)

            # Verify the wrapped iterable was correctly returned
            assert collected == iterable

            # Verify update was called for each item
            assert mock_reporter.update.call_count == len(iterable)

            # Verify finish was called at the end
            mock_reporter.finish.assert_called_once()

    def test_exception_during_iteration(self) -> None:
        """Test handling exceptions during iteration."""

        # Create an iterable that raises an exception
        def error_generator():
            yield 1
            yield 2
            raise ValueError("Test error")
            yield 3  # This will never be reached

        progress = SimpleProgress(error_generator())

        # Replace the reporter with a mock
        mock_reporter = MagicMock()
        progress.reporter = mock_reporter

        # Iterate until exception
        with pytest.raises(ValueError):
            list(progress)

        # Verify update was called twice (for the first two yields)
        assert mock_reporter.update.call_count == 2

        # finish should NOT be called on exception
        mock_reporter.finish.assert_not_called()


class TestShowProgress:
    """Tests for the show_progress function."""

    def test_simple_progress(self) -> None:
        """Test that show_progress returns a SimpleProgress instance."""
        iterable = range(10)

        result = show_progress(iterable, desc="Test")

        # Verify it's the right type
        assert isinstance(result, SimpleProgress)

        # Verify the parameters were passed correctly
        assert result.reporter.desc == "Test"
        assert result.total == 10
        assert result.reporter.unit == "it"

        # Verify it can be iterated
        assert list(result) == list(range(10))


class TestProgressCallback:
    """Tests for the ProgressCallback protocol."""

    def test_protocol_compliance(self) -> None:
        """Test that functions follow the ProgressCallback protocol."""

        # Create a function that matches the protocol
        def callback(
            current: int, total: int | None, message: str | None = None
        ) -> None:
            pass

        # There's no direct way to check protocol compliance at runtime,
        # but we can verify it has the expected signature
        assert callable(callback)

        # Test using it as a callback
        reporter = ProgressReporter()
        reporter.add_callback(callback)

        # Should not raise any TypeError about incompatible signatures
        with patch.object(reporter, "_draw"):  # Prevent actual drawing
            with patch("time.time", return_value=123456.0):  # Fix the time
                reporter.update(message="Test callback")
