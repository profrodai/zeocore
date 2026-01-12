# === QV-LLM:BEGIN ===
# path: quack-runner/src/quack_runner/workflow/legacy.py
# module: quack_runner.workflow.legacy
# role: module
# neighbors: __init__.py, results.py, tool_runner.py
# exports: FileWorkflowRunner, LegacyWorkflowOutputWriter, DefaultOutputWriter, RemoteFileHandler, InputResult, OutputResult, FinalResult
# git_branch: feat/9-make-setup-work
# git_commit: 2f6d56ab
# === QV-LLM:END ===

"""
LEGACY API for backward compatibility.

⚠️ DEPRECATED - DO NOT USE IN NEW CODE ⚠️

This module exports the v1.x workflow API for tools that haven't
migrated to the new doctrine-compliant pattern yet.

All classes here are LEGACY and maintained only for backward compatibility.
They are NOT doctrine-compliant and should not be used for new tools.

Deprecated: Will be removed in v4.0

For new tools, use:
    from quack_runner.workflow import ToolRunner
    from quack_core.tools import BaseQuackTool

DOCTRINE FENCE (fix #4, #5):
Legacy code in this module may:
- Use global service registries
- Perform I/O from Ring B
- Auto-initialize services
This is acceptable ONLY because it's explicitly quarantined as LEGACY.
The new ToolRunner path never touches this code.
"""

import warnings

# Issue loud deprecation warning on import (fix #4)
warnings.warn(
    "quack_runner.workflow.legacy is deprecated. "
    "Migrate to ToolRunner and doctrine-compliant tools. "
    "This module will be removed in v4.0.",
    DeprecationWarning,
    stacklevel=2
)

# Legacy runner
from quack_runner.workflow.runners.file_runner import FileWorkflowRunner

# Legacy output writer (renamed to avoid collision)
from quack_runner.workflow.mixins.output_writer import (
    LegacyWorkflowOutputWriter,
    DefaultOutputWriter,  # Deprecated alias
)

# Legacy protocols
from quack_runner.workflow.protocols.remote_handler import RemoteFileHandler

# Legacy result types
from quack_runner.workflow.results import FinalResult, InputResult, OutputResult

__all__ = [
    'FileWorkflowRunner',
    'LegacyWorkflowOutputWriter',
    'DefaultOutputWriter',  # Deprecated alias
    'RemoteFileHandler',
    'InputResult',
    'OutputResult',
    'FinalResult',
]

# CRITICAL: NO LEGACY INTEGRATION MIXIN (blocker #2 resolution)
#
# quack_runner/workflow/mixins/integration_enabled.py DOES NOT EXIST.
# It was removed entirely - no warning version, no legacy version.
#
# Why removed completely:
# - Used global service registry (get_integration_service)
# - Did lazy initialization and auto-init
# - Violated doctrine even as "legacy"
# - Too easy to import accidentally
#
# The ONLY integration mixin is quack_core.tools.IntegrationEnabledMixin:
# - Services from ctx.services (runner-provided)
# - No global registry
# - No auto-initialization
# - Type-safe with optional validation
#
# DO NOT re-create a runner version. It will not be accepted.
# Tools must use the doctrine-compliant version in quack_core.tools.