"""Execution requests and secret-free operational receipts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from zeo_core.integrations.core.artifacts import ArtifactFact


class NotebookExecutionRequest(BaseModel):
    """Explicit paths and deadlines. This is trusted execution, not an OS sandbox."""

    model_config = ConfigDict(extra="forbid")
    source_path: str
    output_path: str
    workspace_root: str
    working_directory: str
    kernel_name: str = "python3"
    timeout_seconds: float = Field(default=120, gt=0)
    cell_timeout_seconds: int = Field(default=30, gt=0)
    require_code_cells: bool = True
    allow_errors: Literal[False] = False
    environment_allowlist: tuple[str, ...] = ()


class NotebookExecutionReceipt(BaseModel):
    """No notebook source, outputs, credentials or raw exception text."""

    source: ArtifactFact
    executed_output: ArtifactFact | None = None
    kernel_name: str
    python_version: str | None = None
    executor_version: str
    code_cells_total: int
    code_cells_executed: int = 0
    code_cells_skipped: int = 0
    failed_cell_id: str | None = None
    failure_kind: str | None = None
    sanitized_error: str | None = None
    status: Literal["SUCCEEDED", "FAILED", "TIMED_OUT", "KERNEL_UNAVAILABLE"] = "FAILED"
    cleanup: Literal["SUCCEEDED", "FAILED", "NOT_STARTED"] = "NOT_STARTED"
    process_isolation: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    network_isolation: Literal["UNAVAILABLE"] = "UNAVAILABLE"
