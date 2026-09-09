"""Elder positive controls for output, startup, identity and accounting limits."""

import hashlib
import importlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from tests.authoring.test_notebook_execution import notebook, request
from zeo_core.integrations.notebook import execute_notebook


@pytest.mark.parametrize(
    "code",
    [
        "print('x' * 20000)",
        "import sys; print('x' * 20000, file=sys.stderr)",
        "from IPython.display import HTML, display; display(HTML('x' * 20000))",
    ],
)
def test_output_flood_is_bounded(tmp_path: Path, code: str) -> None:
    notebook(tmp_path / "source.ipynb", code)
    result = execute_notebook(request(tmp_path, max_output_bytes=512))
    assert not result.success and result.content is not None, result
    assert result.content.failure_kind == "OUTPUT_LIMIT"
    assert result.content.captured_output_bytes <= 512
    assert result.content.cleanup == "SUCCEEDED"
    assert result.content.code_cells_attempted == 1
    assert result.content.code_cells_failed == 1
    assert result.content.code_cells_completed == 0
    assert not (tmp_path / "executed.ipynb").exists()


def test_startup_deadline_and_memory_fuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = importlib.import_module("zeo_core.integrations.notebook.service")
    real_popen = subprocess.Popen
    notebook(tmp_path / "source.ipynb", "raise AssertionError('must never start')")

    def stalled(*args: object, **kwargs: Any) -> subprocess.Popen:  # noqa: ANN401 -- pass Popen configuration through unchanged
        return real_popen(  # noqa: S603 -- fixed injected stalled-startup process
            [sys.executable, "-c", "import time; time.sleep(60)"], **kwargs
        )

    monkeypatch.setattr(service.subprocess, "Popen", stalled)
    start = time.monotonic()
    result = execute_notebook(
        request(tmp_path, timeout_seconds=0.2, cleanup_timeout_seconds=1)
    )
    assert time.monotonic() - start < 3
    assert result.content is not None, result
    assert result.content.failure_kind == "WHOLE_RUN_TIMEOUT"
    assert result.content.code_cells_attempted == 0
    assert result.content.cleanup == "SUCCEEDED"
    result = execute_notebook(request(tmp_path, max_worker_memory_bytes=1))
    assert result.content is not None, result
    assert result.content.failure_kind == "WORKER_MEMORY_LIMIT"
    assert result.content.cleanup == "SUCCEEDED"


def test_detached_observed_child_after_kernel_exit(tmp_path: Path) -> None:
    notebook(
        tmp_path / "source.ipynb",
        """
import os, subprocess, sys, time
from pathlib import Path
from typing import Any
child = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True
)
Path("detached.pid").write_text(str(child.pid))
time.sleep(0.25)
os._exit(17)
""",
    )
    result = execute_notebook(request(tmp_path))
    assert not result.success and result.content is not None, result
    assert result.content.cleanup == "SUCCEEDED"
    assert result.content.complete_descendant_cleanup == "UNAVAILABLE"
    psutil = importlib.import_module("psutil")
    pid = int((tmp_path / "detached.pid").read_text())
    try:
        process = psutil.Process(pid)
        assert not process.is_running() or process.status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        pass


def test_managed_kernel_identity_ignores_poisoned_ambient_specs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "SYNTHETIC_KERNELSPEC_VALUE"  # noqa: S105 -- test sentinel
    for name in ("first", "second"):
        directory = tmp_path / name / "kernels/python3"
        directory.mkdir(parents=True)
        (directory / "kernel.json").write_text(
            json.dumps(
                {
                    "argv": [sys.executable, "-c", "raise SystemExit(99)"],
                    "display_name": "Conflicting Python",
                    "language": "python",
                    "env": {"INJECTED_SECRET": secret},
                }
            )
        )
    monkeypatch.setenv(
        "JUPYTER_PATH", str(tmp_path / "first") + ":" + str(tmp_path / "second")
    )
    notebook(
        tmp_path / "source.ipynb",
        "import os; assert 'INJECTED_SECRET' not in os.environ; print(42)",
    )
    lock = tmp_path / "environment.lock"
    lock.write_bytes((Path(__file__).resolve().parents[2] / "uv.lock").read_bytes())
    result = execute_notebook(
        request(tmp_path, environment_lock_path="environment.lock")
    )
    assert result.success and result.content is not None, result
    identity = result.content.kernel_identity
    assert len(identity["kernelspec_sha256"]) == 64
    assert "executable_path" not in identity and "kernelspec_path" not in identity
    assert (
        identity["executable_sha256"]
        == hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
    )
    assert result.content.environment_lock is not None
    assert (
        result.content.environment_lock.sha256
        == hashlib.sha256(lock.read_bytes()).hexdigest()
    )
    assert secret not in result.model_dump_json()
    assert secret not in (tmp_path / "executed.ipynb").read_text()
    result = execute_notebook(
        request(
            tmp_path, output_path="refused.ipynb", expected_environment_sha256="0" * 64
        )
    )
    assert not result.success and result.content is not None, result
    assert result.content.failure_kind == "ENVIRONMENT_MISMATCH"
    assert result.content.code_cells_attempted == 0
    assert not (tmp_path / "refused.ipynb").exists()
    accepted = execute_notebook(
        request(
            tmp_path,
            output_path="accepted.ipynb",
            expected_environment_sha256=identity["environment_sha256"],
            absolute_provenance_paths=True,
        )
    )
    assert accepted.success and accepted.content is not None
    assert accepted.content.kernel_identity["executable_path"] == str(
        Path(sys.executable).resolve()
    )


def test_accounting_and_cell_limit(tmp_path: Path) -> None:
    source = tmp_path / "source.ipynb"
    notebook(source, "print(42)")
    nb = json.loads(source.read_text())
    skipped = dict(
        nb["cells"][0],
        id="intentionally-skipped",
        source="raise AssertionError()",
        metadata={"tags": ["no-execute"]},
    )
    nb["cells"].append(skipped)
    source.write_text(json.dumps(nb))
    refused = execute_notebook(request(tmp_path, max_code_cells=1))
    assert refused.error == "CODE_CELL_LIMIT"
    result = execute_notebook(request(tmp_path))
    assert result.success and result.content is not None, result
    assert (
        result.content.code_cells_attempted == result.content.code_cells_completed == 1
    )
    assert result.content.code_cells_failed == 0
    assert result.content.code_cells_skipped == 1
    nb["cells"] = [skipped]
    source.write_text(json.dumps(nb))
    assert (
        execute_notebook(request(tmp_path, output_path="allskipped.ipynb")).error
        == "NO_EXECUTABLE_CODE"
    )


def test_clear_output_cannot_reset_capture_budget(tmp_path: Path) -> None:
    from jupyter_client.session import Session
    from nbformat.v4 import new_code_cell, new_notebook

    from zeo_core.integrations.notebook.bounded_client import (
        BoundedNotebookClient,
        OutputLimitError,
    )

    cell = new_code_cell("print('an output')")
    client = BoundedNotebookClient(
        new_notebook(cells=[cell]),
        output_limit=200,
        progress=tmp_path / "progress.json",
    )
    client.clear_before_next_output = False  # nbclient initializes this at cell start
    message = Session().msg("stream", content={"name": "stdout", "text": "x" * 100})
    client.process_message(message, cell, 0)
    assert len(cell.outputs) == 1
    client.process_message(
        {"msg_type": "clear_output", "parent_header": {}, "content": {"wait": False}},
        cell,
        0,
    )
    assert not cell.outputs
    with pytest.raises(OutputLimitError):
        client.process_message(message, cell, 0)
    assert not cell.outputs
    assert (
        100
        <= json.loads((tmp_path / "progress.json").read_text())["captured_output_bytes"]
        <= 200
    )
    # Widget buffers also consume the same cumulative budget before processing.
    with pytest.raises(OutputLimitError):
        client.process_message(
            {"msg_type": "comm_msg", "content": {}, "buffers": [b"x" * 500]}, cell, 0
        )
