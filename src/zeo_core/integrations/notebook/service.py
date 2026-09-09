"""Parent-enforced deadlines and separately promoted execution output."""

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any

from zeo_core.integrations.core.artifacts import artifact_fact, validate_output
from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.notebook.identity import resolved_identity
from zeo_core.integrations.notebook.models import (
    NotebookExecutionReceipt,
    NotebookExecutionRequest,
)
from zeo_core.integrations.notebook.processes import ProcessTracker


def _environment(home: Path, allowlist: tuple[str, ...]) -> dict[str, str]:
    env = {
        "PATH": os.defpath,
        "HOME": str(home),
        "JUPYTER_CONFIG_DIR": str(home / "config"),
        "JUPYTER_DATA_DIR": str(home / "data"),
        "JUPYTER_RUNTIME_DIR": str(home / "runtime"),
        "IPYTHONDIR": str(home / "ipython"),
        "XDG_CONFIG_HOME": str(home / "config"),
        "XDG_DATA_HOME": str(home / "data"),
        "XDG_CACHE_HOME": str(home / "cache"),
        "PYTHONNOUSERSITE": "1",
    }
    for key in allowlist:
        if not re.fullmatch(r"(LANG|LC_ALL|TZ|COURSE_[A-Z0-9_]+)", key) or re.search(
            r"SECRET|TOKEN|PASSWORD|KEY|CREDENTIAL|PROXY", key
        ):
            raise ValueError("UNSAFE_ENVIRONMENT_ALLOWLIST")
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def _kernel(home: Path) -> None:
    directory = home / "data" / "kernels" / "python3"
    directory.mkdir(parents=True)
    (directory / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [
                    sys.executable,
                    "-I",
                    "-m",
                    "ipykernel_launcher",
                    "-f",
                    "{connection_file}",
                ],
                "display_name": "ZeoCore Python",
                "language": "python",
                "env": {},
            }
        )
    )


def _paths(request: NotebookExecutionRequest) -> tuple[Path, Path, Path, Path]:
    root = Path(request.workspace_root).resolve(strict=True)
    values = [
        Path(p)
        for p in (
            request.source_path,
            request.output_path,
            request.working_directory,
        )
    ]
    source, output, cwd = [p if p.is_absolute() else root / p for p in values]
    validate_output(source, output, root)
    cwd.resolve(strict=True).relative_to(root)
    if not cwd.is_dir():
        raise ValueError("INVALID_WORKING_DIRECTORY")
    return source, output, cwd, root


def _run_worker(
    request: NotebookExecutionRequest,
    source: Path,
    cwd: Path,
    temp: Path,
) -> tuple[dict[str, Any], bool]:
    env = _environment(temp, request.environment_allowlist)
    _kernel(temp)
    identity = resolved_identity(
        temp / "data/kernels/python3/kernel.json",
        absolute_paths=request.absolute_provenance_paths,
    )
    if request.expected_environment_sha256 is not None and (
        identity["environment_sha256"] != request.expected_environment_sha256
    ):
        return {
            "status": "FAILED",
            "failure_kind": "ENVIRONMENT_MISMATCH",
            "kernel_identity": identity,
        }, True
    result_path, executed = temp / "result.json", temp / "executed.ipynb"
    payload = request.model_dump()
    payload.update(
        source_path=str(source),
        working_directory=str(cwd),
        result_path=str(result_path),
        executed_path=str(executed),
    )
    request_path = temp / "request.json"
    request_path.write_text(json.dumps(payload))
    process = subprocess.Popen(  # noqa: S603 -- fixed installed worker, no shell
        [
            sys.executable,
            "-I",
            "-m",
            "zeo_core.integrations.notebook.worker",
            str(request_path),
        ],
        env=env,
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    tracker = ProcessTracker(process)
    result: dict[str, Any] = {"status": "FAILED", "failure_kind": "WORKER_FAILED"}
    deadline = time.monotonic() + request.timeout_seconds
    try:
        while process.poll() is None:
            tracker.observe()
            if tracker.worker_memory() > request.max_worker_memory_bytes:
                result = {"status": "FAILED", "failure_kind": "WORKER_MEMORY_LIMIT"}
                break
            if result_path.exists():
                result = json.loads(result_path.read_text())
                break
            if time.monotonic() >= deadline:
                result = {"status": "TIMED_OUT", "failure_kind": "WHOLE_RUN_TIMEOUT"}
                break
            time.sleep(0.01)
    finally:
        cleaned = tracker.cleanup(request.cleanup_timeout_seconds)
        if process.stdin:
            process.stdin.close()
    progress = temp / "progress.json"
    if progress.exists():
        observations = json.loads(progress.read_text())
        for name in (
            "code_cells_attempted",
            "code_cells_completed",
            "code_cells_failed",
            "captured_output_bytes",
        ):
            result.setdefault(name, observations.get(name, 0))
        result.setdefault("failed_cell_id", observations.get("active_cell_id"))
    result["kernel_identity"] = identity
    return result, cleaned


def _inventory(source: Path) -> tuple[int, int]:
    text = source.read_text()
    if not text.strip():
        raise ValueError("EMPTY_INPUT")
    notebook = json.loads(text)
    cells = notebook.get("cells", [])
    if not cells:
        raise ValueError("ZERO_CELLS")
    if any(c.get("cell_type") not in ("code", "markdown", "raw") for c in cells):
        raise ValueError("UNSUPPORTED_CELL_TYPE")
    code = [c for c in cells if c["cell_type"] == "code"]
    if not code:
        raise ValueError("NO_CODE_CELLS")
    skipped = sum("no-execute" in c.get("metadata", {}).get("tags", []) for c in code)
    if len(code) == skipped:
        raise ValueError("NO_EXECUTABLE_CODE")
    return len(code), skipped


def _accounting(receipt: NotebookExecutionReceipt, result: dict[str, Any]) -> None:
    """Timeout and crash leave attempted cells failed, never completed."""
    for name in (
        "code_cells_attempted",
        "code_cells_completed",
        "code_cells_failed",
        "captured_output_bytes",
    ):
        setattr(receipt, name, result.get(name, 0))
    if result["status"] != "SUCCEEDED":
        receipt.code_cells_failed = max(
            receipt.code_cells_failed,
            receipt.code_cells_attempted - receipt.code_cells_completed,
        )


def execute_notebook(
    request: NotebookExecutionRequest,
) -> IntegrationResult[NotebookExecutionReceipt]:
    """Execute trusted course code with a fresh Python kernel and bounded cleanup."""
    if os.name != "posix":
        return IntegrationResult.error_result("PROCESS_CLEANUP_UNAVAILABLE")
    if any(
        importlib.util.find_spec(name) is None
        for name in ("nbclient", "ipykernel", "psutil")
    ):
        return IntegrationResult.error_result("NOTEBOOK_EXTRA_UNAVAILABLE")
    try:
        source, output, cwd, root = _paths(request)
        _environment(root, request.environment_allowlist)  # validate before writes
        total, skipped = _inventory(source)
        if total > request.max_code_cells:
            raise ValueError("CODE_CELL_LIMIT")
        lock = None
        if request.environment_lock_path is not None:
            lock_path = Path(request.environment_lock_path)
            lock = artifact_fact(
                lock_path if lock_path.is_absolute() else root / lock_path, "lock", root
            )
        receipt = NotebookExecutionReceipt(
            source=artifact_fact(source, "ipynb", root),
            kernel_name=request.kernel_name,
            executor_version=version("nbclient"),
            code_cells_total=total,
            code_cells_skipped=skipped,
            environment_lock=lock,
            output_limit_bytes=request.max_output_bytes,
            cleanup_timeout_seconds=request.cleanup_timeout_seconds,
        )
        with tempfile.TemporaryDirectory(prefix=".execution-", dir=root) as temporary:
            temp = Path(temporary)
            result, cleaned = _run_worker(request, source, cwd, temp)
            _accounting(receipt, result)
            receipt.kernel_identity = result.get("kernel_identity", {})
            receipt.cleanup = "SUCCEEDED" if cleaned else "FAILED"
            receipt.status = result["status"]
            receipt.failure_kind = result.get("failure_kind")
            receipt.sanitized_error = receipt.failure_kind
            receipt.code_cells_executed = result.get("code_cells_executed", 0)
            receipt.failed_cell_id = result.get("failed_cell_id")
            receipt.python_version = result.get("python_version")
            if not cleaned:
                receipt.status, receipt.failure_kind = "FAILED", "CLEANUP_FAILED"
            if receipt.status == "SUCCEEDED":
                if artifact_fact(source, "ipynb", root).sha256 != receipt.source.sha256:
                    receipt.status, receipt.failure_kind = "FAILED", "SOURCE_CHANGED"
                else:
                    staged = temp / "executed.ipynb"
                    fact = artifact_fact(staged, "ipynb", root)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    os.link(staged, output)
                    receipt.executed_output = fact.model_copy(
                        update={"path": str(output.relative_to(root))}
                    )
            receipt.sanitized_error = receipt.failure_kind
            return IntegrationResult(
                success=receipt.status == "SUCCEEDED",
                content=receipt,
                error=receipt.failure_kind,
            )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        code = (
            str(exc)
            if str(exc)
            in {
                "CODE_CELL_LIMIT",
                "EMPTY_INPUT",
                "ZERO_CELLS",
                "NO_CODE_CELLS",
                "NO_EXECUTABLE_CODE",
                "UNSUPPORTED_CELL_TYPE",
                "UNSAFE_ENVIRONMENT_ALLOWLIST",
            }
            else "EXECUTION_REQUEST_OR_WORKER_FAILED"
        )
        return IntegrationResult.error_result(code)
