# quack-core/src/quack-core/workflow/results.py
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
