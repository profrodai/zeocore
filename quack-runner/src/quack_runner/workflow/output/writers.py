# === QV-LLM:BEGIN ===
# path: quack-runner/src/quack_runner/workflow/output/writers.py
# === QV-LLM:END ===


"""
⚠️ LEGACY - DEPRECATED - DO NOT USE ⚠️

LEGACY: Output writers for FileWorkflowRunner.

These are for legacy FileWorkflowRunner only.
ToolRunner (v2.0+) handles output writing internally.

Deprecated: Will be removed in v4.0

For new code, use:
    from quack_runner.workflow import ToolRunner

DO NOT import from here - use quack_runner.workflow.legacy if needed.
"""

import warnings

# Issue loud deprecation warning (fix blocker #1)
warnings.warn(
    "quack_runner.workflow.output.writers is LEGACY and deprecated. "
    "Use ToolRunner for new code. Import from quack_runner.workflow.legacy if you must use legacy. "
    "This module will be removed in v4.0.",
    DeprecationWarning,
    stacklevel=2
)

from pathlib import Path
from typing import Any
import json
import yaml

from quack_runner.workflow.output.base import OutputWriter


class JsonOutputWriter(OutputWriter):
    """
    LEGACY: JSON output writer.

    ⚠️ DEPRECATED - DO NOT USE IN NEW CODE ⚠️

    Performs I/O directly (doctrine violation - acceptable only because legacy).
    """

    def __init__(self, indent: int = 2):
        self.indent = indent

    def write_output(self, data: Any, output_path: str | Path) -> str:
        """Write data as JSON."""
        from quack_core.core.fs.service import standalone
        output_path = Path(output_path)

        # Ensure directory exists
        fs = standalone
        fs.create_directory(str(output_path.parent), exist_ok=True)

        # Write JSON
        result = fs.write_json(str(output_path), data, indent=self.indent)
        if not result.success:
            raise IOError(f"Failed to write JSON: {result.error}")

        return str(output_path)


class YamlOutputWriter(OutputWriter):
    """
    LEGACY: YAML output writer.

    ⚠️ DEPRECATED - DO NOT USE IN NEW CODE ⚠️

    Performs I/O directly (doctrine violation - acceptable only because legacy).
    """

    def write_output(self, data: Any, output_path: str | Path) -> str:
        """Write data as YAML."""
        from quack_core.core.fs.service import standalone
        output_path = Path(output_path)

        # Ensure directory exists
        fs = standalone
        fs.create_directory(str(output_path.parent), exist_ok=True)

        # Convert to YAML
        yaml_content = yaml.dump(data, default_flow_style=False, sort_keys=False)

        # Write file
        result = fs.write_text(str(output_path), yaml_content)
        if not result.success:
            raise IOError(f"Failed to write YAML: {result.error}")

        return str(output_path)


# Backward compatibility alias (will be removed in v4.0)
DefaultOutputWriter = JsonOutputWriter