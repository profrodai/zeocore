"""
Structural protocol for ZeoTools.

This protocol defines the interface that tools must satisfy.
It matches BaseZeoTool exactly for structural typing.

FIXED: Types match BaseZeoTool reality (name can be None before init).
"""

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from zeo_core.contracts import CapabilityResult
    from zeo_core.tools.context import ToolContext


class ZeoToolProtocol(Protocol):
    """
    Protocol for ZeoTools (structural typing).

    This defines the interface any tool must satisfy, whether or not
    it inherits from BaseZeoTool.

    IMPORTANT: Types match BaseZeoTool exactly (fix #1):
    - name can be None until __init__ enforces it
    - version has default "1.0.0"

    For duck-typed tools, ensure name is set before use.
    """

    # Attributes - match BaseZeoTool exactly (fix #1)
    name: str | None  # Can be None before __init__
    version: str  # Has default "1.0.0"

    # Core method
    def run(
        self,
        request: Any,  # noqa: ANN401 -- request type is per-tool; mirrors BaseZeoTool.run (structural protocol, must match exactly)
        ctx: "ToolContext",
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
    def initialize(self, ctx: "ToolContext") -> "CapabilityResult[None]":
        """
        Initialize tool with context (optional).

        Args:
            ctx: Tool context

        Returns:
            CapabilityResult indicating success or failure
        """
        ...
