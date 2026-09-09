"""Worker-only nbclient specialization: bounded capture and explicit accounting."""

import json
from pathlib import Path
from typing import Any

from nbclient import NotebookClient
from nbformat import NotebookNode


class OutputLimitError(RuntimeError):
    """Captured output exceeded the declared limit."""


class BoundedNotebookClient(NotebookClient):
    """Bound retained output and persist progress for parent deadlines."""

    def __init__(
        self,
        nb: NotebookNode,
        *,
        output_limit: int,
        progress: Path,
        **kwargs: Any,  # noqa: ANN401 -- nbclient forwards trait configuration
    ) -> None:
        super().__init__(nb, **kwargs)
        self.output_limit = output_limit
        self.progress = progress
        self.observations: dict[str, Any] = {
            "code_cells_attempted": 0,
            "code_cells_completed": 0,
            "code_cells_failed": 0,
            "captured_output_bytes": 0,
        }

    def save_progress(self) -> None:
        """Atomic diagnostics; the parent never reads half-written progress."""
        pending = self.progress.with_suffix(".pending")
        pending.write_text(json.dumps(self.observations))
        pending.replace(self.progress)

    async def async_execute_cell(
        self,
        cell: NotebookNode,
        cell_index: int,
        execution_count: int | None = None,
        store_history: bool = True,
    ) -> NotebookNode:
        tracked = (
            cell.cell_type == "code"
            and bool(cell.source.strip())
            and "no-execute" not in cell.metadata.get("tags", [])
        )
        if tracked:
            self.observations["code_cells_attempted"] += 1
            self.observations["active_cell_id"] = cell.get("id")
            self.save_progress()
        try:
            result = await super().async_execute_cell(
                cell, cell_index, execution_count, store_history
            )
        except Exception:
            if tracked:
                self.observations["code_cells_failed"] += 1
                self.save_progress()
            raise
        if tracked:
            self.observations["code_cells_completed"] += 1
            self.observations.pop("active_cell_id", None)
            self.save_progress()
        return result

    def process_message(
        self, msg: dict[str, Any], cell: NotebookNode, cell_index: int
    ) -> NotebookNode | None:
        if msg["msg_type"] in {
            "stream",
            "display_data",
            "execute_result",
            "update_display_data",
            "error",
            "comm_open",
            "comm_msg",
            "comm_close",
        }:
            size = len(json.dumps(msg["content"], ensure_ascii=False).encode())
            size += sum(len(buffer) for buffer in msg.get("buffers", []))
            if self.observations["captured_output_bytes"] + size > self.output_limit:
                self.save_progress()
                raise OutputLimitError("OUTPUT_LIMIT")
            self.observations["captured_output_bytes"] += size
        return super().process_message(msg, cell, cell_index)
