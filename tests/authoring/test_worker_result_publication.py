"""A parent must never observe a partially written worker result."""

import io
import json
from pathlib import Path
from unittest.mock import MagicMock

import nbformat
import pytest

from zeo_core.integrations.notebook import worker


@pytest.mark.parametrize("fails", [False, True])
def test_result_is_published_only_after_complete_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fails: bool
) -> None:
    source = tmp_path / "source.ipynb"
    nbformat.write(
        nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("1")]), source
    )
    result_path = tmp_path / "result.json"
    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "source_path": str(source),
                "result_path": str(result_path),
                "executed_path": str(tmp_path / "executed.ipynb"),
                "working_directory": str(tmp_path),
                "kernel_name": "python3",
                "max_output_bytes": 1000,
                "startup_timeout_seconds": 10,
                "cell_timeout_seconds": 10,
            }
        )
    )
    monkeypatch.setattr(worker.sys, "argv", ["worker", str(request_path)])
    monkeypatch.setattr(worker.sys, "stdin", io.StringIO(""))

    def client(*, nb: nbformat.NotebookNode, **_kwargs: object) -> MagicMock:
        instance = MagicMock(observations={"code_cells_attempted": 1})

        def execute(**_kwargs: object) -> None:
            if fails:
                raise RuntimeError("synthetic cell failure")
            nb.cells[0].execution_count = 1

        instance.execute.side_effect = execute
        return instance

    monkeypatch.setattr(worker, "BoundedNotebookClient", client)
    original_write = Path.write_text
    observations = []

    def interrupted_write(
        path: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        if path.name not in {"result.json", "result.pending"}:
            return original_write(path, data, encoding, errors, newline=newline)
        with path.open("w") as handle:
            handle.write(data[:1])
            handle.flush()
            observations.append(True)
            assert not result_path.exists(), "Parent can observe partial result JSON"
            handle.write(data[1:])
        return len(data)

    monkeypatch.setattr(Path, "write_text", interrupted_write)
    worker.main()
    assert observations == [True]
    result = json.loads(result_path.read_text())
    assert result["status"] == ("FAILED" if fails else "SUCCEEDED")
    assert result["failure_kind"] == ("CELL_EXCEPTION" if fails else None)
    assert not result_path.with_suffix(".pending").exists()
