
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
from pathlib import Path
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

    # Convenience properties for Path usage (fix #4)

    @property
    def work_path(self) -> Path:
        """
        Get work directory as Path for convenient manipulation.

        Returns:
            Path object for work_dir

        Example:
            >>> temp_file = ctx.work_path / "temp.txt"
            >>> with open(temp_file, 'w') as f:
            ...     f.write("data")
        """
        return Path(self.work_dir)

    @property
    def output_path(self) -> Path:
        """
        Get output directory as Path for convenient manipulation.

        Returns:
            Path object for output_dir

        Example:
            >>> report_file = ctx.output_path / "report.json"
            >>> # Note: tools should not write directly to output_path
            >>> # This is for reference only - runner writes outputs
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