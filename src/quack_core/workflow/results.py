# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/workflow/results.py
# module: quack_core.workflow.results
# role: module
# neighbors: __init__.py
# exports: InputResult, OutputResult, FinalResult
# git_branch: refactor/newHeaders
# git_commit: 7d82586
# === QV-LLM:END ===

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict


class InputResult(BaseModel):
    """
    Result of resolving and retrieving input.

    This model represents an input file that has been resolved
    and is ready for processing.
    """
    path: Path
    metadata: dict[str, Any] = {}

    # Use model_config instead of Config class
    model_config = ConfigDict(arbitrary_types_allowed=True)


class OutputResult(BaseModel):
    """
    Result of processing content.

    This model represents the results of processing the content
    of an input file.
    """
    success: bool
    content: Any | None = None
    raw_text: str | None = None

    # Use model_config instead of Config class
    model_config = ConfigDict(arbitrary_types_allowed=True)


class FinalResult(BaseModel):
    """
    Final result of a workflow.

    This model represents the final result of a workflow,
    including the output path and metadata.
    """
    success: bool
    result_path: Path | None = None
    metadata: dict[str, Any] = {}

    # Use model_config instead of Config class
    model_config = ConfigDict(arbitrary_types_allowed=True)
