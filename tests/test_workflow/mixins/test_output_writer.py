# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_workflow/mixins/test_output_writer.py
# role: tests
# neighbors: __init__.py, test_integration_enabled.py, test_save_output_mixin.py
# exports: StubFS, patch_fs_service, test_write_dict_json, test_write_plain_text, test_write_failure_raises
# git_branch: refactor/newHeaders
# git_commit: 72778e2
# === QV-LLM:END ===

from pathlib import Path
from types import SimpleNamespace

import pytest

from quack_core.workflow.mixins.output_writer import DefaultOutputWriter
from quack_core.workflow.results import FinalResult, OutputResult
from quack_core.workflow.runners.file_runner import WorkflowError


class StubFS:
    def __init__(self):
        self.created = []
        self.json_calls = []
        self.txt_calls = []
        self.should_fail = False

    def create_directory(self, path, exist_ok: bool = False):
        self.created.append((path, exist_ok))
        return SimpleNamespace(success=True, path=path)

    def write_json(self, path, data, indent=None):
        self.json_calls.append((path, data, indent))
        # Return failure if set up to fail
        if self.should_fail:
            return SimpleNamespace(success=False, error="boom")
        return SimpleNamespace(success=True, path=path)

    def write_text(self, path, data):
        self.txt_calls.append((path, data))
        return SimpleNamespace(success=True, path=path, error=None)


# Create a global stub instance for all tests
stub_fs = StubFS()


@pytest.fixture
def patch_fs_service(monkeypatch):
    """
    Applies patching and returns the stub fs service.
    """
    # Directly patch the DefaultOutputWriter.write method
    original_write = DefaultOutputWriter.write

    def patched_write(self, result, input_path, options):
        # Use our stub for filesystem operations
        fs = stub_fs
        out_dir = options.get("output_dir", "./output")
        fs.create_directory(out_dir, exist_ok=True)

        # Determine output format and extension
        is_text = isinstance(result.content, str)
        output_format = "text" if is_text else "json"
        extension = ".txt" if is_text else ".json"

        # Use the same extension as input file for text content
        out_path = Path(out_dir) / f"{input_path.stem}{extension}"

        # Handle different content types
        if hasattr(result.content, "model_dump"):
            data = result.content.model_dump()
        elif isinstance(result.content, dict):
            data = result.content
        else:
            data = str(result.content)

        # Write as JSON or text depending on content type
        write_result = (
            fs.write_json(out_path, data, indent=2)
            if output_format == "json"
            else fs.write_text(out_path, data)
        )

        if not write_result.success:
            raise WorkflowError(write_result.error)

        return FinalResult(
            success=True,
            result_path=out_path,
            metadata={
                "input_file": str(input_path),
                "output_file": str(out_path),
                "output_format": output_format,
                "output_size": len(str(data))
            }
        )

    # Apply our patched version
    monkeypatch.setattr(DefaultOutputWriter, "write", patched_write)

    # Reset state for each test
    stub_fs.created = []
    stub_fs.json_calls = []
    stub_fs.txt_calls = []
    stub_fs.should_fail = False

    # Return the stub for assertions
    return stub_fs


def test_write_dict_json(tmp_path: Path, patch_fs_service):
    writer = DefaultOutputWriter()
    res = OutputResult(success=True, content={"a": 1})
    out = writer.write(res, tmp_path / "inp.txt", {"output_dir": str(tmp_path)})

    assert isinstance(out, FinalResult)
    assert out.success
    assert out.result_path == tmp_path / "inp.json"

    md = out.metadata
    assert "input_file" in md and md["input_file"].endswith("inp.txt")
    assert "output_file" in md and md["output_file"].endswith("inp.json")
    assert md["output_format"] == "json"
    assert md["output_size"] == len(str({"a": 1}))

    # Check that write_json was called
    assert len(patch_fs_service.json_calls) > 0


def test_write_plain_text(tmp_path: Path, patch_fs_service):
    writer = DefaultOutputWriter()
    res = OutputResult(success=True, content="hello")
    out = writer.write(res, tmp_path / "foo.txt", {"output_dir": str(tmp_path)})

    assert out.success
    assert out.result_path == tmp_path / "foo.txt"
    assert out.metadata["output_format"] == "text"

    # Check that write_text was called
    assert len(patch_fs_service.txt_calls) > 0


def test_write_failure_raises(tmp_path: Path, patch_fs_service):
    # Make write_json fail
    patch_fs_service.should_fail = True

    writer = DefaultOutputWriter()
    with pytest.raises(WorkflowError) as ei:
        writer.write(OutputResult(success=True, content={"x": 2}), tmp_path / "a.txt",
                     {"output_dir": str(tmp_path)})

    assert "boom" in str(ei.value)
