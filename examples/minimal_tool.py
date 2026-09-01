"""
Minimal zeo_core.tools example: a tool with no integrations at all.

This is the simplest possible doctrine-compliant tool -- no mixins, no
external services, no optional behavior. It exists to show the smallest
onboarding surface: subclass BaseZeoTool, implement run(request, ctx),
return a CapabilityResult.

Contrast with examples/toolkit_usage.py, which layers on
IntegrationEnabledMixin (service lookup) and LifecycleMixin (pre/post hooks)
-- neither of which is required. A tool is a valid, complete tool with just
run().

Run this file directly:

    uv run examples/minimal_tool.py
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from zeo_core.contracts import CapabilityResult
from zeo_core.core.fs import get_service as get_fs_service
from zeo_core.tools import BaseZeoTool, ToolContext


class WordCountRequest(BaseModel):
    """Request model for WordCountTool.run()."""

    text: str


class WordCountResponse(BaseModel):
    """Response payload carried inside CapabilityResult.data."""

    word_count: int
    char_count: int


class WordCountTool(BaseZeoTool):
    """
    Counts words and characters in a string.

    No mixins, no services, no I/O beyond what run() itself needs. This is
    the floor of what a doctrine-compliant tool looks like: a class with a
    name/version identity and a run(request, ctx) -> CapabilityResult method.
    """

    name = "word_count"
    version = "1.0.0"

    def run(
        self, request: WordCountRequest, ctx: ToolContext
    ) -> CapabilityResult[WordCountResponse]:
        """
        Count words and characters in request.text.

        Args:
            request: Typed request carrying the text to analyze.
            ctx: Runner-provided, immutable tool context.

        Returns:
            CapabilityResult wrapping a WordCountResponse.
        """
        logger = ctx.require_logger()
        if logger is not None:
            logger.info(f"[{self.name}] counting words in {len(request.text)} chars")

        words = request.text.split()

        return CapabilityResult.ok(
            data=WordCountResponse(
                word_count=len(words),
                char_count=len(request.text),
            ),
            msg="Word count completed",
            metadata={"tool": f"{self.name} v{self.version}"},
        )


def main() -> None:
    """
    Run WordCountTool end to end.

    Plays the runner's role (Ring C): builds a minimal ToolContext, builds
    a request, calls tool.run(), and prints the result. No output file is
    written -- there's nothing to persist beyond the printed data for a
    tool this simple.
    """
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory(prefix="zeo_minimal_tool_") as tmp:
        tmp_dir = Path(tmp)

        ctx = ToolContext(
            run_id="minimal-run-001",
            tool_name="word_count",
            tool_version="1.0.0",
            logger=logging.getLogger("word_count"),
            fs=get_fs_service(),
            work_dir=str(tmp_dir),
            output_dir=str(tmp_dir),
        )

        tool = WordCountTool()

        init_result = tool.initialize(ctx)
        if init_result.status != "success":
            print(f"Failed to initialize tool: {init_result.human_message}")
            return
        print(f"Tool initialized: {init_result.human_message}")

        request = WordCountRequest(
            text="ZeoCore is a capability-authoring framework for doctrine-compliant "
            "tools."
        )
        result = tool.run(request, ctx)

        if result.status != "success":
            print(f"Tool run failed: {result.human_message}")
            return

        assert result.data is not None  # noqa: S101 -- narrows Optional for the print below; status==success guarantees data is populated per run()'s own contract
        print(f"Result: {result.human_message}")
        print(f"Words: {result.data.word_count}, Characters: {result.data.char_count}")


if __name__ == "__main__":
    main()
