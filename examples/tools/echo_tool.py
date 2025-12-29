
"""
Echo tool example - demonstrates doctrine-compliant tool implementation.

This example shows:
- How to import from contracts (Ring A)
- How to inherit from BaseQuackTool (Ring B)
- How to use ToolContext
- How to return CapabilityResult
- What NOT to do (no file I/O, no runners, no output writers)
"""

from quack_core.contracts import (
    CapabilityResult,
    EchoRequest,
)
from quack_core.tools import BaseQuackTool, ToolContext


class EchoTool(BaseQuackTool):
    """
    Simple echo tool that demonstrates the contract pattern.

    This tool:
    - Receives an EchoRequest (from contracts)
    - Returns a CapabilityResult[str]
    - Uses ToolContext for logging
    - Does NOT handle file I/O (that's the runner's job)

    Example:
        >>> from quack_core.contracts import EchoRequest
        >>> from examples.tools.echo_tool import EchoTool
        >>>
        >>> tool = EchoTool()
        >>> request = EchoRequest(text="World", preset="friendly")
        >>>
        >>> # In real usage, runner would build context
        >>> # For demo, we build minimal context:
        >>> from quack_core.tools import ToolContext
        >>> ctx = ToolContext(
        ...     tool_name=tool.name,
        ...     tool_version=tool.version
        ... )
        >>>
        >>> result = tool.run(request, ctx)
        >>> print(result.data)  # "Hello World"
        >>> print(result.status)  # CapabilityStatus.success
    """

    def __init__(self):
        """Initialize the echo tool."""
        super().__init__(
            name="demo.echo",
            version="1.0.0"
        )

    def run(
            self,
            request: EchoRequest,
            ctx: ToolContext
    ) -> CapabilityResult[str]:
        """
        Execute the echo capability.

        Args:
            request: Echo request with text and optional greeting
            ctx: Execution context (for logging, etc.)

        Returns:
            CapabilityResult containing the echoed text
        """
        # Use context for logging
        ctx.get_logger().info(f"Processing echo request with preset: {request.preset}")

        # Build result
        greeting = request.override_greeting or "Hello"
        result_text = f"{greeting} {request.text}"

        # Return CapabilityResult
        return CapabilityResult.ok(
            data=result_text,
            msg="Echo completed successfully",
            metadata={
                "preset": request.preset,
                "greeting_used": greeting,
                "output_length": len(result_text)
            }
        )

# Anti-patterns to AVOID:
#
# ❌ DON'T import from quack_runner:
# from quack_runner.workflow import FileWorkflowRunner  # WRONG
#
# ❌ DON'T handle file I/O in the tool:
# def run(self, request, ctx):
#     with open("/output/result.txt", "w") as f:  # WRONG
#         f.write(result)
#
# ❌ DON'T create manifests in the tool:
# def run(self, request, ctx):
#     manifest = RunManifest(...)  # WRONG
#     write_manifest(manifest)
#
# ❌ DON'T use FastAPI-style dependency injection:
# def run(self, request, fs: FileSystem = Depends(...)):  # WRONG
#
# ✅ DO return CapabilityResult with typed data:
# def run(self, request, ctx):
#     return CapabilityResult.ok(data=result, msg="Done")
#
# ✅ DO use ToolContext for services:
# def run(self, request, ctx):
#     ctx.logger.info("Processing...")
#     fs = ctx.get_fs()