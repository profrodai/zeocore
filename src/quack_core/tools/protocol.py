# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/protocol.py
# module: quack_core.tools.protocol
# role: module
# neighbors: __init__.py, base.py, context.py
# exports: QuackToolProtocol
# git_branch: refactor/toolkitWorkflow
# git_commit: de0fa70
# === QV-LLM:END ===



"""
Protocol for QuackCore tools (Ring B only).

This protocol defines the structural interface for doctrine-compliant tools.
It matches BaseQuackTool exactly (fix #1 - no extra methods).

Note: This is for Ring B tools only. Plugin-layer concerns (metadata, discovery)
are handled separately in the plugin system.
"""

from typing import Any, Protocol, runtime_checkable, TYPE_CHECKING

from quack_core.contracts import CapabilityResult

if TYPE_CHECKING:
    from quack_core.tools.context import ToolContext


@runtime_checkable
class QuackToolProtocol(Protocol):
    """
    Protocol for doctrine-compliant tools (Ring B).

    This protocol defines the minimal interface that all tools must implement.
    It matches BaseQuackTool exactly.

    Use this for:
    - Type hints when you want structural typing
    - Duck-typing checks (isinstance with @runtime_checkable)
    - Tool discovery (check if object satisfies protocol)

    Note: This does NOT include plugin-layer methods like get_metadata().
    Those belong in a separate plugin protocol if needed.
    """

    # Identity
    name: str
    version: str

    # Core methods (match BaseQuackTool exactly)

    def initialize(self, ctx: "ToolContext") -> CapabilityResult[None]:
        """
        Initialize tool with context (optional hook).

        Args:
            ctx: Tool context

        Returns:
            CapabilityResult indicating success or failure
        """
        ...

    def is_available(self, ctx: "ToolContext") -> bool:
        """
        Check if tool is available (optional hook).

        Args:
            ctx: Tool context

        Returns:
            True if tool can run, False otherwise
        """
        ...

    def run(self, request: Any, ctx: "ToolContext") -> CapabilityResult[Any]:
        """
        Execute the tool capability.

        This is the core method every tool must implement.

        Args:
            request: Typed request (Pydantic model from contracts)
            ctx: Tool context (immutable, runner-provided)

        Returns:
            CapabilityResult with status, data, error, logs, metadata
        """
        ...

# Note on removed methods (fix #1):
#
# REMOVED: logger property
# Reason: Tools don't have logger property. They get logger from ctx.
#
# REMOVED: get_metadata() -> QuackPluginMetadata
# Reason: That's plugin-layer concern, not Ring B tool interface.
#
# This protocol now matches BaseQuackTool exactly, so any BaseQuackTool
# instance will satisfy QuackToolProtocol structurally.