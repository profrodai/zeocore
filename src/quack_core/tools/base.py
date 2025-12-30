# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/base.py
# module: quack_core.tools.base
# role: module
# neighbors: __init__.py, context.py, protocol.py
# exports: BaseQuackTool
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===


"""
Base class for all QuackCore tools (doctrine-compliant).

FIXED: Constructor accepts class attributes as defaults (blocker #1).
"""

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from quack_core.contracts import CapabilityResult

if TYPE_CHECKING:
    from quack_core.tools.context import ToolContext


class BaseQuackTool(ABC):
    """
    Base class for all doctrine-compliant tools.

    Tools can define name/version as class attributes (recommended):
        class EchoTool(BaseQuackTool):
            name = "echo"
            version = "1.0.0"

            def run(self, request, ctx):
                return CapabilityResult.ok(data=response)

    Or pass them to __init__ (if dynamic):
        tool = EchoTool(name="echo", version="2.0.0")

    Tools must NOT:
    - Write files directly
    - Create RunManifest
    - Import from quack_runner.*
    - Mutate ToolContext
    """

    # Class attributes (optional - can be overridden in __init__)
    # Use str | None to avoid type: ignore (fix #2)
    name: str | None = None
    version: str = "1.0.0"  # Default version

    def __init__(self, name: str | None = None, version: str | None = None):
        """
        Initialize the tool.

        Args:
            name: Tool name (uses class attribute if not provided)
            version: Tool version (uses class attribute if not provided)

        Raises:
            TypeError: If name not provided and no class attribute

        Example:
            >>> # Option A: Class attributes (recommended)
            >>> class MyTool(BaseQuackTool):
            ...     name = "my_tool"
            ...     version = "1.0.0"
            >>> tool = MyTool()  # Uses class attributes

            >>> # Option B: Constructor args (dynamic)
            >>> tool = MyTool(name="custom_name", version="2.0.0")
        """
        # Use provided args, fall back to class attributes
        if name is not None:
            self.name = name
        elif self.name is None:
            raise TypeError(
                f"{self.__class__.__name__} must either:\n"
                f"  1. Define 'name' as a class attribute, or\n"
                f"  2. Pass 'name' to __init__()\n"
                f"Example: class {self.__class__.__name__}(BaseQuackTool):\n"
                f"    name = 'my_tool'"
            )

        # After validation, name is guaranteed non-None (fix #4 - cleaner)
        assert self.name is not None, "name must be set by this point"

        if version is not None:
            self.version = version
        # else: use class attribute (default "1.0.0" or overridden)

    def initialize(self, ctx: "ToolContext") -> CapabilityResult[None]:
        """
        Initialize tool with context (optional hook).

        Override this to perform setup that requires context.
        Default: success.
        """
        return CapabilityResult.ok(data=None, msg=f"{self.name} initialized")

    def is_available(self, ctx: "ToolContext") -> bool:
        """
        Check if tool is available (optional hook).

        Override this to check dependencies, permissions, etc.
        Default: true.
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
            CapabilityResult with status, data, error, logs, metadata

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