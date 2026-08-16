# === QV-LLM:BEGIN ===
# path: examples/tools/echo_tool.py
# === QV-LLM:END ===


"""
Example: Doctrine-compliant echo tool.

Demonstrates:
- Canonical imports (from quack_core.tools only)
- Pure capability (no I/O)
- Immutable context usage
- Proper CapabilityResult returns
"""

from pydantic import BaseModel

# ✅ CORRECT: Import contracts
from quack_core.contracts import CapabilityResult

# ✅ CORRECT: Import from quack_core.tools (canonical path)
from quack_core.tools import BaseQuackTool, ToolContext


# Request model (in contracts in production)
class EchoRequest(BaseModel):
    """Request for echo tool."""

    text: str
    override_greeting: str | None = None


class EchoTool(BaseQuackTool):
    """
    Simple echo tool demonstrating doctrine compliance.

    This tool:
    - Returns CapabilityResult (machine-readable)
    - Receives ToolContext (immutable)
    - Does NO file I/O (runner handles)
    - Uses canonical imports
    """

    def __init__(self) -> None:
        super().__init__(name="echo", version="1.0.0")

    def run(self, request: EchoRequest, ctx: ToolContext) -> CapabilityResult[str]:
        """
        Echo the input text with optional greeting.

        Args:
            request: Echo request
            ctx: Tool context (immutable, runner-provided)

        Returns:
            CapabilityResult with echoed text
        """
        # Access services from context (runner-provided)
        logger = ctx.require_logger()
        logger.info(f"[{ctx.run_id}] Echoing: {request.text}")

        # Process request
        greeting = request.override_greeting or "Hello"
        result_text = f"{greeting} {request.text}"

        # Return capability result
        return CapabilityResult.ok(data=result_text, msg="Echo completed successfully")


# ❌ ANTI-PATTERNS (what NOT to do):
"""
# DON'T: Import from submodules
from quack_core.tools.mixins import IntegrationEnabledMixin  # Wrong!
from quack_core.tools import IntegrationEnabledMixin  # Correct!

# DON'T: Import from runner
from quack_runner.workflow import ToolRunner  # Wrong! (Ring C)

# DON'T: Write files directly
def run(self, request, ctx):
    with open("output.txt", "w") as f:  # Wrong!
        f.write(result)
    # Runner handles file I/O

# DON'T: Create RunManifest
def run(self, request, ctx):
    return RunManifest(...)  # Wrong!
    # Return CapabilityResult instead

# DON'T: Mutate context
def run(self, request, ctx):
    ctx.metadata["foo"] = "bar"  # Wrong! (context is frozen)
"""
