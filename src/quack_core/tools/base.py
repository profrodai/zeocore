

"""
Base class for all QuackCore tools (doctrine-compliant).

This is the foundation for Ring B (capability authoring).
Tools inherit from this class and implement run().

Key principles:
- Tools are pure capabilities (request → CapabilityResult)
- No file I/O (runner handles)
- No manifest creation (runner translates)
- Receive explicit ToolContext (no DI magic)
"""

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from quack_core.contracts import CapabilityResult, CapabilityStatus

if TYPE_CHECKING:
    from quack_core.tools.context import ToolContext


class BaseQuackTool(ABC):
    """
    Base class for all doctrine-compliant tools.

    Tools must implement run() which:
    - Receives typed request (Pydantic model from contracts)
    - Receives ToolContext (immutable, runner-provided)
    - Returns CapabilityResult (machine-readable outcome)

    Tools must NOT:
    - Write files directly
    - Create RunManifest
    - Import from quack_runner.*
    - Mutate ToolContext

    Example:
        >>> from quack_core.tools import BaseQuackTool, ToolContext
        >>> from quack_core.contracts import CapabilityResult
        >>>
        >>> class MyTool(BaseQuackTool):
        ...     def __init__(self):
        ...         super().__init__(name="my_tool", version="1.0.0")
        ...
        ...     def run(self, request, ctx: ToolContext) -> CapabilityResult:
        ...         result = self._process(request, ctx)
        ...         return CapabilityResult.ok(data=result, msg="Success")
    """

    def __init__(self, name: str, version: str):
        """
        Initialize the tool.

        Args:
            name: Tool name (e.g. "echo", "markdown_converter")
            version: Tool version (e.g. "1.0.0")
        """
        self.name = name
        self.version = version

    def initialize(self, ctx: "ToolContext") -> CapabilityResult[None]:
        """
        Initialize tool with context (optional hook).

        Override this to perform setup that requires context.
        Default: success.

        Args:
            ctx: Tool context

        Returns:
            CapabilityResult indicating success or failure
        """
        return CapabilityResult.ok(msg=f"{self.name} initialized")

    def is_available(self, ctx: "ToolContext") -> bool:
        """
        Check if tool is available (optional hook).

        Override this to check dependencies, permissions, etc.
        Default: true.

        Args:
            ctx: Tool context

        Returns:
            True if tool can run, False otherwise
        """
        return True

    @abstractmethod
    def run(self, request: Any, ctx: "ToolContext") -> CapabilityResult[Any]:
        """
        Execute the tool capability.

        This is the core method every tool must implement.

        Args:
            request: Typed request (Pydantic model from contracts)
            ctx: Tool context (immutable, runner-provided)

        Returns:
            CapabilityResult with:
            - status: success/skip/error
            - data: Typed response (if success)
            - error: Error details (if error)
            - logs: Execution logs
            - metadata: Additional metadata

        Example:
            >>> def run(self, request: MyRequest, ctx: ToolContext) -> CapabilityResult[MyResponse]:
            ...     logger = ctx.require_logger()
            ...     logger.info(f"Processing: {request.input}")
            ...
            ...     result = self._do_work(request, ctx)
            ...
            ...     return CapabilityResult.ok(
            ...         data=MyResponse(output=result),
            ...         msg="Processing complete"
            ...     )
        """
        pass

# Note: Backward compatibility alias removed from this file (fix #5)
# Alias is defined in __init__.py only to avoid duplication