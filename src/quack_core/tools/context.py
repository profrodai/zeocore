# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/context.py
# module: quack_core.tools.context
# role: module
# neighbors: __init__.py, base.py, protocol.py
# exports: ToolContext
# git_branch: refactor/toolkitWorkflow
# git_commit: 82e6d2b
# === QV-LLM:END ===



"""
Tool execution context.

The ToolContext is the bridge between tools (Ring B) and runners (Ring C).
It provides tools with access to services and configuration WITHOUT
coupling them to specific runner implementations.

Design principles:
- ToolContext is constructed by runners, not tools
- Tools receive context explicitly (no dependency injection magic)
- Context is immutable from tool's perspective
- All I/O services are accessed through context
"""

from typing import Any, Optional
from logging import Logger
from pydantic import BaseModel, Field, ConfigDict

from quack_core.contracts import generate_run_id


class ToolContext(BaseModel):
    """
    Execution context provided to tools by runners.

    This context encapsulates everything a tool needs to execute:
    - Identity (run_id, tool name/version)
    - Services (filesystem, logger)
    - Directories (work_dir, output_dir)
    - Metadata (free-form configuration)

    The context is constructed by the runner and passed to the tool.
    Tools should NOT construct their own contexts.

    Example (runner constructs context):
        >>> from quack_core.tools import ToolContext
        >>> from quack_core.lib.fs.service import standalone as fs
        >>> import logging
        >>>
        >>> ctx = ToolContext(
        ...     tool_name="media.transcribe",
        ...     tool_version="1.0.0",
        ...     run_id="550e8400-e29b-41d4-a716-446655440000",
        ...     fs=fs,
        ...     logger=logging.getLogger("media.transcribe"),
        ...     work_dir="/tmp/quack_work",
        ...     output_dir="/tmp/quack_output"
        ... )
        >>>
        >>> # Tool receives and uses context
        >>> def run(request, ctx: ToolContext):
        ...     ctx.logger.info(f"Starting {ctx.tool_name}")
        ...     content = ctx.fs.read_text("/input.txt")
        ...     return CapabilityResult.ok(data=content)

    Immutability:
        While Pydantic models are technically mutable, tools should treat
        ToolContext as immutable. Modifying context creates unexpected
        behavior across tool boundaries.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # Allow Logger, fs service
        extra="allow"  # Allow runners to add custom fields
    )

    # Identity
    run_id: str = Field(
        default_factory=generate_run_id,
        description="Unique identifier for this execution run"
    )

    tool_name: str = Field(
        ...,
        description="Name of the tool being executed",
        examples=["media.transcribe", "text.summarize", "crm.sync_contacts"]
    )

    tool_version: str = Field(
        ...,
        description="Semantic version of the tool",
        examples=["1.0.0", "2.1.3"]
    )

    # Services (Any type to avoid import cycles)
    logger: Optional[Logger] = Field(
        None,
        description="Logger instance for the tool"
    )

    fs: Optional[Any] = Field(
        None,
        description="Filesystem service handle (quack_core.lib.fs.service)"
    )

    # Directories
    work_dir: Optional[str] = Field(
        None,
        description="Temporary working directory for intermediate files"
    )

    output_dir: Optional[str] = Field(
        None,
        description="Directory for final output files"
    )

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form metadata (runner config, environment vars, etc.)"
    )

    def get_logger(self) -> Logger:
        """
        Get the logger instance, creating a basic one if not provided.

        Returns:
            Logger instance for this tool
        """
        if self.logger is None:
            import logging
            self.logger = logging.getLogger(self.tool_name)
        return self.logger

    def get_fs(self) -> Any:
        """
        Get the filesystem service, importing standalone if not provided.

        Returns:
            Filesystem service handle

        Raises:
            RuntimeError: If filesystem service cannot be initialized
        """
        if self.fs is None:
            try:
                from quack_core.lib.fs.service import standalone
                self.fs = standalone
            except ImportError as e:
                raise RuntimeError(
                    f"Failed to initialize filesystem service: {e}"
                )
        return self.fs

    def with_metadata(self, **kwargs: Any) -> "ToolContext":
        """
        Create a new context with additional metadata.

        This is useful for passing context through nested tool calls
        with additional information.

        Args:
            **kwargs: Additional metadata to merge

        Returns:
            New ToolContext with merged metadata

        Example:
            >>> ctx2 = ctx.with_metadata(step="preprocessing", index=1)
            >>> ctx2.metadata
            {'step': 'preprocessing', 'index': 1, ...}
        """
        new_metadata = {**self.metadata, **kwargs}
        return self.model_copy(update={"metadata": new_metadata})