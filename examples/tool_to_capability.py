"""Adapt a BaseZeoTool class into a BoundCapability and invoke it."""

from __future__ import annotations

import logging
from tempfile import TemporaryDirectory

from pydantic import BaseModel

from zeo_core.contracts import CapabilityExample, CapabilityResult
from zeo_core.core.fs import get_service as get_fs_service
from zeo_core.tools import (
    BaseZeoTool,
    CapabilityRegistry,
    ToolContext,
    invoke_sync,
    tool_to_capability,
)


class WordCountRequest(BaseModel):
    text: str


class WordCountResponse(BaseModel):
    word_count: int


class WordCountTool(BaseZeoTool):
    """Count words in a string."""

    name = "word_count"
    namespace = "demo"
    version = "1.0.0"
    capability_description = "Count words in a string."
    capability_examples = (
        CapabilityExample(
            request={"text": "hello world"},
            response={"word_count": 2},
        ),
    )

    def run(
        self, request: WordCountRequest, ctx: ToolContext
    ) -> CapabilityResult[WordCountResponse]:
        ctx.require_logger().info("counting words")
        return CapabilityResult.ok(
            data=WordCountResponse(word_count=len(request.text.split()))
        )


def main() -> None:
    tool = WordCountTool()
    cap = tool_to_capability(tool)
    registry = CapabilityRegistry()
    registry.register(cap)

    with TemporaryDirectory(prefix="zeo_adapt_") as tmp:
        ctx = ToolContext(
            run_id="adapt-001",
            tool_name=tool.name,
            tool_version=tool.version,
            logger=logging.getLogger("word_count"),
            fs=get_fs_service(),
            work_dir=tmp,
            output_dir=tmp,
        )
        # Direct class path still works:
        direct = tool.run(WordCountRequest(text="hello world"), ctx)
        # Canonical capability path:
        via_cap = invoke_sync(cap, WordCountRequest(text="hello world"), ctx)
        print("class run:", direct.data.word_count if direct.data else None)
        print("invoke_sync:", via_cap.data.word_count if via_cap.data else None)
        print("canonical id:", cap.definition.id.canonical())
        resolved = registry.get("demo.word_count@1.0.0")
        print("registry hit:", resolved is not None)


if __name__ == "__main__":
    main()
