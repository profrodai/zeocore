# === QV-LLM:BEGIN ===
# path: quack-runner/src/quack_runner/workflow/output/__init__.py
# module: quack_runner.workflow.output.__init__
# role: module
# neighbors: base.py, writers.py
# exports: OutputWriter, JsonOutputWriter, YamlOutputWriter
# git_branch: feat/9-make-setup-work
# git_commit: 10c11a25
# === QV-LLM:END ===


"""
Output writing functionality for QuackRunner workflows (LEGACY).

This module provides output writers for legacy FileWorkflowRunner.
ToolRunner (v2.0+) handles output writing internally.

New names in v2.0:
- JsonOutputWriter (was DefaultOutputWriter)
- YamlOutputWriter (was YAMLOutputWriter)
"""

from quack_runner.workflow.output.base import OutputWriter
from quack_runner.workflow.output.writers import JsonOutputWriter, YamlOutputWriter

__all__ = [
    "OutputWriter",
    "JsonOutputWriter",
    "YamlOutputWriter",
]