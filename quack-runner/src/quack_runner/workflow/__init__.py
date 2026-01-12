# === QV-LLM:BEGIN ===
# path: quack-runner/src/quack_runner/workflow/__init__.py
# module: quack_runner.workflow.__init__
# role: module
# neighbors: results.py, legacy.py, tool_runner.py
# exports: ToolRunner
# git_branch: feat/9-make-setup-work
# git_commit: 2f6d56ab
# === QV-LLM:END ===



"""
quack_runner.workflow – Tool execution with file I/O and manifest generation.

This module provides the ToolRunner for executing doctrine-compliant tools
(BaseQuackTool with run() method) with file-based workflows.

NEW API (v2.0+):
- ToolRunner: Execute tools, generate RunManifests

LEGACY API (deprecated, v1.x):
- Available under quack_runner.workflow.legacy
- FileWorkflowRunner, DefaultOutputWriter, etc.
- Maintained for backward compatibility during migration

Migration:
- v2.0-2.x: Both new and legacy work
- v3.0: Legacy deprecated (warnings)
- v4.0: Legacy removed
"""

# NEW API: Only export ToolRunner
from quack_runner.workflow.tool_runner import ToolRunner

__all__ = [
    'ToolRunner',
]

# Example: New Pattern (v2.0+)
"""
from quack_core.tools import BaseQuackTool, ToolContext
from quack_core.contracts import CapabilityResult, EchoRequest
from quack_runner.workflow import ToolRunner

class EchoTool(BaseQuackTool):
    def run(self, request: EchoRequest, ctx: ToolContext) -> CapabilityResult[str]:
        return CapabilityResult.ok(data=f"Hello {request.text}", msg="Success")

# Run with ToolRunner
tool = EchoTool()
runner = ToolRunner(tool)
manifest = runner.run_on_file(
    input_path="input.txt",
    request_builder=lambda c: EchoRequest(text=c),
    output_dir="output"
)
"""

# Legacy imports (for backward compatibility during migration)
# Import from quack_runner.workflow.legacy instead:
"""
LEGACY (deprecated):
from quack_runner.workflow.legacy import (
    FileWorkflowRunner,
    DefaultOutputWriter,
    RemoteFileHandler,
    InputResult,
    OutputResult,
    FinalResult,
)
"""