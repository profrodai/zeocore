# quack-core/tests/test_workflow/runners/test_file_runner.py
"""
Tests for FileWorkflowRunner.

This module ensures the file workflow runner correctly handles file processing.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from quack_core.workflow.results import FinalResult, InputResult, OutputResult
from quack_core.workflow.runners.file_runner import FileWorkflowRunner, WorkflowError


# Simple processor function for testing
def dummy_processor(content, options=None):
    """Dummy processor that simply returns the content."""
    if options and options.get("fail_proc"):
        raise ValueError("Simulated processor error")
    return True, {"processed": True, "content": content, "options": options}, None


class TestFileWorkflowRunner:
    """Tests for FileWorkflowRunner."""

    def test_remote_download(self, tmp_path):
        """Test handling of remote files."""
        # Write a dummy file
        f = tmp_path / "r.txt"
        f.write_text("x")

        class Remote:
            def __init__(self):
                self.dl = False

            def is_remote(self, s):
                return True

            def download(self, s):
                self.dl = True
                return InputResult(path=f, metadata={"foo": "bar"})

        remote = Remote()

        # Mock the load_content method to avoid real fs calls
        with patch.object(FileWorkflowRunner, 'load_content', return_value="mock content"):
            # Mock the write_output method to avoid filesystem operations
            with patch.object(FileWorkflowRunner, 'write_output') as mock_write:
                mock_write.return_value = FinalResult(
                    success=True,
                    result_path=f.with_suffix(".json"),
                    metadata={
                        "input_file": str(f),
                        "output_file": str(f.with_suffix(".json")),
                        "output_format": "json",
                        "processor_success": True
                    }
                )

                runner = FileWorkflowRunner(processor=dummy_processor, remote_handler=remote)
                res = runner.run(str(f), options={"output_dir": str(tmp_path)})

                assert res.success
                assert remote.dl
                assert res.metadata["input_type"] == "remote"

    def test_read_failure_returns_error(self, tmp_path):
        """Test that a failure to read a file results in an error."""
        # Create a runner with a mocked load_content that raises an error
        runner = FileWorkflowRunner(processor=dummy_processor)

        with patch.object(FileWorkflowRunner, 'load_content', side_effect=WorkflowError("Failed to read file content")):
            # Run the processor with a file path
            bad = tmp_path / "missing.txt"
            res = runner.run(str(bad))

            # Verify the error is properly propagated
            assert not res.success
            assert "error_type" in res.metadata
            assert "failed to read" in res.metadata.get("error_message", "").lower()

    def test_file_exists_but_unreadable(self, tmp_path):
        """Test behavior when a file exists but is unreadable."""
        # Create a runner with a mocked load_content that raises an error
        runner = FileWorkflowRunner(processor=dummy_processor)

        with patch.object(FileWorkflowRunner, 'load_content', side_effect=WorkflowError("Failed to read file content")):
            # Run the processor with a file path
            bad = tmp_path / "unreadable.txt"
            res = runner.run(str(bad))

            # Verify the error is properly propagated
            assert not res.success
            assert "error_type" in res.metadata
            assert "failed to read" in res.metadata.get("error_message", "").lower()

    def test_processor_error_handling(self, tmp_path):
        """Test handling of errors from the processor function."""
        # Create a file
        f = tmp_path / "test.txt"
        f.write_text("testing")

        # Create a runner with a mocked load_content
        runner = FileWorkflowRunner(processor=dummy_processor)

        with patch.object(FileWorkflowRunner, 'load_content', return_value="test content"):
            # Run with options that trigger failure in the processor
            res = runner.run(str(f), options={"fail_proc": True})

            # Verify the processor error is properly handled
            assert not res.success
            assert "processor_error" in res.metadata
            assert "simulated processor error" in res.metadata.get("processor_error", "").lower()

    def test_write_error_propagates(self, tmp_path):
        """Test that errors during output writing are properly handled."""
        # Create a file
        f = tmp_path / "e.txt"
        f.write_text("x")

        # Create a runner with mocked methods
        runner = FileWorkflowRunner(processor=dummy_processor)

        with patch.object(FileWorkflowRunner, 'load_content', return_value="test content"):
            # Mock write_output to simulate a failure
            with patch.object(FileWorkflowRunner, 'write_output', side_effect=WorkflowError("Simulated write error")):
                res = runner.run(str(f), options={})

                # Verify the error is properly propagated
                assert not res.success
                assert "error_type" in res.metadata
                assert "error_message" in res.metadata
                assert "simulated write error" in res.metadata.get("error_message", "").lower()

    def test_directory_creation_failure(self, tmp_path):
        """Test handling of directory creation failure."""
        # Create a file
        f = tmp_path / "test.txt"
        f.write_text("testing")

        # Create a runner with mocked methods
        runner = FileWorkflowRunner(processor=dummy_processor)

        with patch.object(FileWorkflowRunner, 'load_content', return_value="test content"):
            # Mock write_output to simulate a failure during directory creation
            with patch.object(FileWorkflowRunner, 'write_output', side_effect=WorkflowError("Directory creation failed")):
                res = runner.run(str(f), options={"output_dir": "/nonexistent"})

                # Verify the error is properly propagated
                assert not res.success
                assert "error_type" in res.metadata
                assert "directory creation failed" in res.metadata.get("error_message", "").lower()

    def test_use_temp_dir(self, tmp_path):
        """Test using a temporary directory for output."""
        # Create a file
        f = tmp_path / "u.txt"
        f.write_text("hi")

        # Create a runner with mocked methods
        runner = FileWorkflowRunner(processor=dummy_processor)

        with patch.object(FileWorkflowRunner, 'load_content', return_value="test content"):
            # Mock tempfile.mkdtemp to return a controlled path
            temp_dir = str(tmp_path / "temp_dir")
            with patch('tempfile.mkdtemp', return_value=temp_dir):
                # Mock lower-level fs functions to avoid actual filesystem operations
                with patch('quack-core.fs.service.standalone.write_json') as mock_write_json:
                    mock_write_json.return_value = SimpleNamespace(success=True, path=str(f.with_suffix(".json")))

                    with patch('os.makedirs'):
                        res = runner.run(str(f), options={"use_temp_dir": True})

                        # Verify temp directory is used
                        assert res.success
                        mock_write_json.assert_called_once()
                        # Check that the output path contains our temp directory
                        assert temp_dir in mock_write_json.call_args[0][0]

    def test_custom_writer(self, tmp_path):
        """Test using a custom output writer."""
        class CustomWriter:
            def write(self, result, input_path, options):
                return FinalResult(
                    success=True,
                    result_path=Path(input_path).with_suffix(".X"),
                    metadata={"ok": True}
                )

        # Create a file
        f = tmp_path / "c.txt"
        f.write_text("x")

        # Create a runner with mocked load_content and a custom writer
        runner = FileWorkflowRunner(processor=dummy_processor, output_writer=CustomWriter())

        with patch.object(FileWorkflowRunner, 'load_content', return_value="test content"):
            res = runner.run(str(f), options={})

            # Verify custom writer was used
            assert res.success
            assert res.result_path == f.with_suffix(".X")
            assert res.metadata["ok"] is True

    def test_binary_file_handling(self, tmp_path):
        """Test proper handling of binary files."""
        # Create a file with binary extension
        f = tmp_path / "test.bin"
        f.write_bytes(b"\x00\x01\x02\x03")

        # Create a mock for the fs.get_extension call
        extension_result = SimpleNamespace(success=True, data="bin")

        # Create a mock for the fs.get_file_info call
        file_info_result = SimpleNamespace(success=True, exists=True)

        # Create a mock for the fs.read_binary call
        binary_read_result = SimpleNamespace(success=True, content=b"\x00\x01\x02\x03")

        # Patch specific fs calls to avoid dependency on the whole fs service
        with patch('quack-core.fs.service.standalone.get_extension', return_value=extension_result):
            with patch('quack-core.fs.service.standalone.get_file_info', return_value=file_info_result):
                with patch('quack-core.fs.service.standalone.read_binary', return_value=binary_read_result):
                    # Also patch the write_output to avoid filesystem operations
                    with patch.object(FileWorkflowRunner, 'write_output') as mock_write:
                        mock_write.return_value = FinalResult(
                            success=True,
                            result_path=f.with_suffix(".json"),
                            metadata={"output_format": "json"}
                        )

                        runner = FileWorkflowRunner(processor=dummy_processor)
                        res = runner.run(str(f))

                        # Verify binary path is detected
                        assert res.success
                        # Verify binary content was passed to the processor
                        assert mock_write.called
                        # Get the OutputResult that was passed to write_output
                        output_result = mock_write.call_args[0][0]
                        # The processor should have received binary content
                        assert isinstance(output_result, OutputResult)
                        assert output_result.content["content"] == b"\x00\x01\x02\x03"
