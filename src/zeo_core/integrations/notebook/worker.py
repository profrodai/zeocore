"""Private worker; imported only by the optional execution subprocess."""

import importlib
import json
import sys
from pathlib import Path
from typing import Any

from zeo_core.integrations.notebook.bounded_client import BoundedNotebookClient


def _failure(exc: Exception) -> dict[str, str]:
    kind = {
        "OutputLimitError": ("FAILED", "OUTPUT_LIMIT"),
        "NoSuchKernel": ("KERNEL_UNAVAILABLE", "MISSING_KERNEL"),
        "CellTimeoutError": ("TIMED_OUT", "CELL_TIMEOUT"),
        "DeadKernelError": ("FAILED", "KERNEL_CRASH"),
    }.get(type(exc).__name__, ("FAILED", "CELL_EXCEPTION"))
    if type(exc).__name__ == "CellExecutionError":
        kind = (
            "FAILED",
            {
                "SyntaxError": "SYNTAX_ERROR",
                "_IncompleteInputError": "SYNTAX_ERROR",
                "IndentationError": "SYNTAX_ERROR",
                "AssertionError": "ASSERTION_FAILURE",
            }.get(getattr(exc, "ename", ""), "CELL_EXCEPTION"),
        )
    return {"status": kind[0], "failure_kind": kind[1]}


def main() -> None:
    """Execute once, report fixed error codes, then wait for parent cleanup."""
    request = json.loads(Path(sys.argv[1]).read_text())
    nbformat = importlib.import_module("nbformat")
    notebook = nbformat.read(request["source_path"], as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.execution_count = None
            cell.outputs = []
    managers = importlib.import_module("jupyter_client")
    specs = importlib.import_module("jupyter_client.kernelspec")
    manager = managers.AsyncKernelManager(
        kernel_name=request["kernel_name"],
        transport="ipc",
        kernel_spec_manager=specs.KernelSpecManager(
            kernel_dirs=[str(Path(request["result_path"]).parent / "data" / "kernels")],
            ensure_native_kernel=False,
        ),
    )
    client = BoundedNotebookClient(
        output_limit=request["max_output_bytes"],
        progress=Path(request["result_path"]).with_name("progress.json"),
        startup_timeout=request["startup_timeout_seconds"],
        nb=notebook,
        km=manager,
        timeout=request["cell_timeout_seconds"],
        kernel_name=request["kernel_name"],
        allow_errors=False,
        force_raise_errors=True,
        skip_cells_with_tag="no-execute",
        record_timing=False,
    )
    result: dict[str, Any] = {
        "status": "FAILED",
        "failure_kind": "EXECUTION_FAILED",
        "code_cells_executed": 0,
        "failed_cell_id": None,
    }
    try:
        client.execute(cwd=request["working_directory"], cleanup_kc=True)
        runnable = [
            cell
            for cell in notebook.cells
            if cell.cell_type == "code"
            and "no-execute" not in cell.metadata.get("tags", [])
        ]
        executed = sum(cell.execution_count is not None for cell in runnable)
        result["code_cells_executed"] = executed
        if executed != len(runnable):
            result["failure_kind"] = "UNEVALUATED_CODE"
        else:
            nbformat.write(notebook, request["executed_path"])
            result.update(status="SUCCEEDED", failure_kind=None)
    except Exception as exc:
        result.update(_failure(exc))
        for cell in notebook.cells:
            if cell.cell_type == "code" and cell.execution_count is not None:
                result["code_cells_executed"] += 1
                result["failed_cell_id"] = cell.get("id")
    result.update(client.observations)
    result["failed_cell_id"] = client.observations.get("active_cell_id")
    result["python_version"] = notebook.metadata.get("language_info", {}).get("version")
    Path(request["result_path"]).write_text(json.dumps(result))
    # Parent retains a live ancestry root until all observed descendants are gone.
    sys.stdin.read(1)


if __name__ == "__main__":
    main()
