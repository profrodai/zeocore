# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/workflow/output/__init__.py
# module: quack_core.workflow.output.__init__
# role: module
# neighbors: base.py, writers.py
# exports: OutputWriter, DefaultOutputWriter, YAMLOutputWriter
# git_branch: refactor/toolkitWorkflow
# git_commit: 66ff061
# === QV-LLM:END ===

"""
Output writing functionality for QuackCore workflows.

This module provides a flexible system for writing workflow outputs in various formats.
It defines a common interface (OutputWriter) and provides concrete implementations
for common formats like JSON and YAML.

The OutputWriter interface is designed to be extensible, allowing for additional
output formats to be added in the future. The current implementations focus on
text-based output formats.

Future extensions:
- TextWriter family: JSON, YAML, CSV, Markdown, HTML
- BinaryWriter family: PDF, Excel, PNG, JPEG
"""

from quack_core.workflow.output.base import OutputWriter
from quack_core.workflow.output.writers import DefaultOutputWriter, YAMLOutputWriter

__all__ = [
    "OutputWriter",
    "DefaultOutputWriter",
    "YAMLOutputWriter",
]
