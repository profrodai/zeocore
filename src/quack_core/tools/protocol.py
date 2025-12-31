# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/protocol.py
# module: quack_core.tools.protocol
# role: module
# neighbors: __init__.py, base.py, context.py
# exports: QuackToolProtocol
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===



"""
Structural protocol for QuackTools.

This protocol defines the interface that tools must satisfy.
It matches BaseQuackTool exactly for structural typing.

FIXED: Types match BaseQuackTool reality (name can be None before init).
"""

from typing import Protocol, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from quack_core.contracts import CapabilityResult
    from quack_core.tools.context import ToolContext


class QuackToolProtocol(Protocol):
    """
    Protocol for QuackTools (structural typing).

    This defines the interface any tool must satisfy, whether or not
    it inherits from BaseQuackTool.

    IMPORTANT: Types match BaseQuackTool exactly (fix #1):
    - name can be None until __init__ enforces it
    - version has default "1.0.0"

    For duck-typed tools, ensure name is set before use.
    """

    # Attributes - match BaseQuackTool exactly (fix #1)
    name: str | None  # Can be None before __init__
    version: str  # Has default "1.0.0"

    # Core method
    def run(
            self,
            request: Any,
            ctx: "ToolContext"
    ) -> "CapabilityResult[Any]":
        """
        Execute the tool capability.

        Args:
            request: Typed request (Pydantic model)
            ctx: Tool context (immutable, runner-provided)

        Returns:
            CapabilityResult with status, data, error, logs
        """
        ...

    # Optional lifecycle method
    def initialize(
            self,
            ctx: "ToolContext"
    ) -> "CapabilityResult[None]":
        """
        Initialize tool with context (optional).

        Args:
            ctx: Tool context

        Returns:
            CapabilityResult indicating success or failure
        """
        ...