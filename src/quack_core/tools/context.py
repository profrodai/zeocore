# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/context.py
# module: quack_core.tools.context
# role: module
# neighbors: __init__.py, base.py, protocol.py
# exports: ToolContext
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===


"""
ToolContext: Immutable dependency container for tool execution.

TOP-LEVEL IMMUTABILITY (fix #1): Uses MappingProxyType for services/metadata.
Nested mutable values (dicts, lists) inside are not recursively frozen.
"""

from typing import Any, Mapping
from pathlib import Path
from types import MappingProxyType
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToolContext(BaseModel):
    """
    Immutable context for tool execution.

    The runner constructs this with all required services.
    Tools receive it as read-only and must not modify it.

    FIXED: Accepts str | Path for work_dir/output_dir (fix #4).
    Normalizes to str for serialization, provides Path properties for convenience.
    """

    # Identity (required)
    run_id: str
    tool_name: str
    tool_version: str

    # Core services (required - runner must provide)
    logger: Any
    fs: Any

    # Directories (required - accepts str | Path, stores as str)
    work_dir: str
    output_dir: str

    # Integration services (optional - deep immutable via MappingProxyType)
    services: Mapping[str, Any] = Field(default_factory=dict)

    # Metadata (optional - deep immutable via MappingProxyType)
    metadata: Mapping[str, Any] = Field(default_factory=dict)

    # Validators to accept str | Path
    @field_validator('work_dir', 'output_dir', mode='before')
    @classmethod
    def normalize_path(cls, v: str | Path) -> str:
        """Normalize Path to str for storage."""
        return str(v) if isinstance(v, Path) else v

    # Validators for deep immutability (fix #1 - always normalize)
    @field_validator('services', 'metadata', mode='before')
    @classmethod
    def make_immutable_mapping(cls, v: dict[str, Any] | Mapping[str, Any]) -> Mapping[
        str, Any]:
        """
        Convert to MappingProxyType for top-level immutability.

        NOTE: This provides top-level immutability only.
        Nested mutable values (dicts, lists) inside are not recursively frozen.
        For services, this is intentional (service objects may be stateful).
        For metadata, tool authors should avoid nested mutables.
        """
        if isinstance(v, MappingProxyType):
            return v
        # Always normalize to dict first (fix #1)
        return MappingProxyType(dict(v))

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

        Example (path computation only):
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
        """Get logger (guaranteed non-None by runner)."""
        return self.logger

    def require_fs(self) -> Any:
        """Get filesystem service (guaranteed non-None by runner)."""
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