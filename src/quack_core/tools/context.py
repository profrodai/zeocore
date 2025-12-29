# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/context.py
# module: quack_core.tools.context
# role: module
# neighbors: __init__.py, base.py, protocol.py
# exports: ToolContext
# git_branch: refactor/toolkitWorkflow
# git_commit: 21647d6
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

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolContext(BaseModel):
    """
    Immutable context for tool execution.

    The runner constructs this with all required services.
    Tools receive it as read-only and must not modify it.

    Core fields (run_id, tool_name, tool_version, logger, fs, work_dir, output_dir)
    are required - runner must provide them.

    Optional fields (services, metadata) may be empty dicts if not needed.
    """

    # Identity (required)
    run_id: str  # No default - runner must provide
    tool_name: str
    tool_version: str

    # Core services (required - runner must provide)
    logger: Any  # Logger instance
    fs: Any  # Filesystem service instance

    # Directories (required - runner ensures they exist)
    # Stored as str for serialization, but Path properties provided
    work_dir: str  # Working directory for temp files
    output_dir: str  # Output directory for artifacts

    # Integration services (optional - may be empty dict)
    services: dict[str, Any] = Field(default_factory=dict)

    # Metadata (optional - may be empty dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Configuration: frozen (immutable)
    model_config = ConfigDict(
        frozen=True,
        arbitrary_types_allowed=True
    )

    # Convenience properties for Path usage

    @property
    def work_path(self) -> Path:
        """
        Get work directory as Path for path computation.

        Returns:
            Path object for work_dir

        Note:
            This is for PATH COMPUTATION only (e.g., building file paths).
            Tools should NOT perform I/O directly. Use fs service for I/O.

        Example (path computation only - fix #3):
            >>> # ✅ Compute paths (no I/O)
            >>> temp_file_path = ctx.work_path / "temp.txt"
            >>> log_file_path = ctx.work_path / "processing.log"
            >>>
            >>> # ❌ DON'T do I/O directly
            >>> # temp_file_path.write_text("data")  # Wrong! Use fs service
        """
        return Path(self.work_dir)

    @property
    def output_path(self) -> Path:
        """
        Get output directory as Path.

        Returns:
            Path object for output_dir

        Note:
            This is for REFERENCE/DEBUG only.
            Tools should NOT write to output_path directly.
            Return data via CapabilityResult; runner writes outputs.

        Example (what NOT to do):
            >>> # ❌ DON'T write to output_path
            >>> # output_file = ctx.output_path / "result.json"
            >>> # output_file.write_text(json.dumps(data))  # Wrong!
            >>>
            >>> # ✅ DO return via CapabilityResult
            >>> return CapabilityResult.ok(data=result)
            >>> # Runner handles writing to output_path
        """
        return Path(self.output_dir)

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

    def get_service(self, name: str) -> Any | None:
        """
        Get a service by name (if runner provided it).

        Args:
            name: Service name (e.g. "slack", "github")

        Returns:
            Service instance or None if not available
        """
        return self.services.get(name)

    def require_service(self, name: str) -> Any:
        """
        Get a service by name (raises if missing).

        Args:
            name: Service name (e.g. "slack", "github")

        Returns:
            Service instance

        Raises:
            ValueError: If service not available in context
        """
        service = self.get_service(name)
        if service is None:
            raise ValueError(
                f"Service '{name}' not available in context. "
                f"Runner must provide it in ctx.services. "
                f"Available services: {list(self.services.keys())}"
            )
        return service
