# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/base.py
# module: quack_core.tools.base
# role: module
# neighbors: __init__.py, context.py, protocol.py
# exports: BaseQuackTool
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===



"""
Base class for all QuackCore tools (doctrine-compliant).

IDENTITY IMMUTABILITY (Recommendation #2): name/version frozen after __init__.
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

    IDENTITY CONTRACT (ENFORCED - Recommendation #2):
    - name and version are set once during __init__
    - Tools CANNOT mutate these after initialization (enforced via __setattr__)
    - Runner may cache tool identity for routing
    - Attempting to mutate raises AttributeError with clear message
    """

    # Class attributes (optional - can be overridden in __init__)
    name: str | None = None
    version: str = "1.0.0"  # Default version

    # Internal flag to track frozen state (Recommendation #2)
    _identity_frozen: bool

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
        # Allow setting identity before freezing (Recommendation #2)
        object.__setattr__(self, '_identity_frozen', False)

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

        # After validation, name is guaranteed non-None
        assert self.name is not None, "name must be set by this point"

        if version is not None:
            self.version = version
        # else: use class attribute (default "1.0.0" or overridden)

        # Freeze identity (Recommendation #2)
        object.__setattr__(self, '_identity_frozen', True)

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Prevent mutation of identity fields after initialization.

        Recommendation #2: Enforce identity immutability.
        """
        # Allow setting _identity_frozen itself
        if name == '_identity_frozen':
            object.__setattr__(self, name, value)
            return

        # Check if identity is frozen
        frozen = getattr(self, '_identity_frozen', False)

        # Block identity changes if frozen (Recommendation #2)
        if frozen and name in ('name', 'version'):
            raise AttributeError(
                f"Cannot modify tool identity after initialization. "
                f"Attempted to set '{name}' = {value!r} on {self.__class__.__name__}. "
                f"Tool identity (name/version) is immutable after __init__. "
                f"Runner may cache identity for routing."
            )

        # Allow other attributes
        object.__setattr__(self, name, value)

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