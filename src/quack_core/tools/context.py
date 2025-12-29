# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/context.py
# module: quack_core.tools.context
# role: module
# neighbors: __init__.py, base.py, protocol.py
# exports: ToolContext
# git_branch: refactor/toolkitWorkflow
# git_commit: 07a259e
# === QV-LLM:END ===


"""
ToolContext: Immutable dependency container for tool execution.

This context is constructed by the runner and passed to tools.
Tools treat it as read-only. No auto-creation of services.

Key principles:
- IMMUTABLE: frozen=True, no mutations
- EXPLICIT: runner provides all services
- NO MAGIC: no service discovery or lazy loading
"""

from typing import Any
from pydantic import BaseModel, ConfigDict


class ToolContext(BaseModel):
    """
    Immutable context for tool execution.

    The runner constructs this with all required services.
    Tools receive it as read-only and must not modify it.

    All fields are required - runner must provide them.
    """

    # Identity
    run_id: str  # No default - runner must provide
    tool_name: str
    tool_version: str

    # Services (all required - runner provides)
    logger: Any  # Logger instance
    fs: Any  # Filesystem service instance

    # Directories (all required - runner ensures they exist)
    work_dir: str  # Working directory for temp files
    output_dir: str  # Output directory for artifacts

    # Metadata
    metadata: dict[str, Any]

    # Configuration: frozen (immutable)
    model_config = ConfigDict(
        frozen=True,
        arbitrary_types_allowed=True
    )

    # Accessor methods (pure - no side effects)

    def require_logger(self) -> Any:
        """
        Get logger (guaranteed non-None by runner).

        Returns:
            Logger instance
        """
        return self.logger

    def require_fs(self) -> Any:
        """
        Get filesystem service (guaranteed non-None by runner).

        Returns:
            Filesystem service instance
        """
        return self.fs