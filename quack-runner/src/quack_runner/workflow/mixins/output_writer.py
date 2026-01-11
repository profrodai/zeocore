# === QV-LLM:BEGIN ===
# path: quack-runner/src/quack_runner/workflow/mixins/output_writer.py
# module: quack_runner.workflow.mixins.output_writer
# role: module
# neighbors: __init__.py, save_output_mixin.py
# exports: WorkflowError, LegacyWorkflowOutputWriter
# git_branch: feat/9-make-setup-work
# git_commit: d448237f
# === QV-LLM:END ===



"""
⚠️ LEGACY - DEPRECATED - DO NOT USE ⚠️

LEGACY: Output writer for FileWorkflowRunner.

This is for legacy FileWorkflowRunner only.
ToolRunner (v2.0+) handles output writing internally.

Deprecated: Will be removed in v4.0

For new code, use:
    from quack_runner.workflow import ToolRunner

DO NOT import from here - use quack_runner.workflow.legacy if needed.
"""

import warnings

# Issue loud deprecation warning (fix blocker #1)
warnings.warn(
    "quack_runner.workflow.mixins.output_writer is LEGACY and deprecated. "
    "Use ToolRunner for new code. Import from quack_runner.workflow.legacy if you must use legacy. "
    "This module will be removed in v4.0.",
    DeprecationWarning,
    stacklevel=2
)

from pathlib import Path
from typing import Any

from quack_runner.workflow.results import FinalResult, OutputResult


class WorkflowError(Exception):
    """Custom exception for workflow-related errors."""


class LegacyWorkflowOutputWriter:
    """
    LEGACY: Output writer for FileWorkflowRunner.

    ⚠️ DEPRECATED - DO NOT USE IN NEW CODE ⚠️

    This class writes OutputResult → FinalResult for legacy workflows.
    ToolRunner doesn't use this.

    Performs I/O directly (doctrine violation - acceptable only because legacy).
    """

    def write(self, result: OutputResult, input_path: Path,
              options: dict[str, Any]) -> FinalResult:
        """Write the output result to a file."""
        from quack_core.core.fs.service import standalone
        fs = standalone
        out_dir = options.get("output_dir", "./output")
        fs.create_directory(out_dir, exist_ok=True)

        is_text = isinstance(result.content, str)
        output_format = "text" if is_text else "json"
        extension = ".txt" if is_text else ".json"

        out_path = Path(out_dir) / f"{input_path.stem}{extension}"

        if hasattr(result.content, "model_dump"):
            data = result.content.model_dump()
        elif isinstance(result.content, dict):
            data = result.content
        else:
            data = str(result.content)

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


# Backward compatibility alias (will be removed in v4.0)
DefaultOutputWriter = LegacyWorkflowOutputWriter