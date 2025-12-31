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

TOP-LEVEL IMMUTABILITY: Uses MappingProxyType for services/metadata.
Nested mutable values (dicts, lists) inside are not recursively frozen.
"""

from typing import Any, Mapping
from pathlib import Path
from types import MappingProxyType
from pydantic import BaseModel, ConfigDict, Field, field_validator, field_serializer

# Fix #2: Import shared serialization logic
from quack_core.lib.serialization import normalize_for_json


class ToolContext(BaseModel):
    """
    Immutable context for tool execution.

    The runner constructs this with all required services.
    Tools receive it as read-only and must not modify it.

    METADATA CONTRACT (ENFORCED):
    - Must be JSON-serializable (validated on construction)
    - Uses shared normalize_for_json() - same logic as ToolRunner (Fix #2)
    - Primitives: str, int, float, bool, None
    - Collections: list, dict (string keys only)
    - Safe types auto-converted: Path→str, datetime→isoformat, Enum→value
    - Pydantic models: converted via model_dump() (Fix #3 - strict isinstance)
    - Top-level immutable (cannot reassign ctx.metadata)
    - Nested values not frozen (tools should treat as read-only)
    - Violations fail immediately with clear error
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

    # Integration services (optional - top-level immutable via MappingProxyType)
    services: Mapping[str, Any] = Field(default_factory=dict)

    # Metadata (optional - top-level immutable + JSON-safe enforced)
    metadata: Mapping[str, Any] = Field(default_factory=dict)

    # Validators to accept str | Path
    @field_validator('work_dir', 'output_dir', mode='before')
    @classmethod
    def normalize_path(cls, v: str | Path) -> str:
        """
        Normalize Path to str for storage.

        Raises:
            TypeError: If value is neither str nor Path
        """
        if isinstance(v, Path):
            return str(v)
        if isinstance(v, str):
            return v
        raise TypeError(
            f"work_dir/output_dir must be str or Path, got {type(v).__name__}"
        )

    # Validators for top-level immutability
    @field_validator('services', mode='before')
    @classmethod
    def make_immutable_services(cls, v: dict[str, Any] | Mapping[str, Any]) -> Mapping[
        str, Any]:
        """Convert to MappingProxyType for top-level immutability."""
        if isinstance(v, MappingProxyType):
            return v
        return MappingProxyType(dict(v))

    # Metadata validator: enforce JSON-serializability using shared logic (Fix #2)
    @field_validator('metadata', mode='before')
    @classmethod
    def validate_and_normalize_metadata(cls, v: dict[str, Any] | Mapping[str, Any]) -> \
    Mapping[str, Any]:
        """
        Validate metadata is JSON-serializable and normalize safe types.

        Fix #2: Uses shared normalize_for_json() to prevent drift with ToolRunner.
        Fix #3: Strict isinstance check for Pydantic models (via shared implementation).
        """
        if isinstance(v, MappingProxyType):
            return v

        # Normalize to dict first
        metadata_dict = dict(v) if isinstance(v, Mapping) else v

        # Use shared normalization logic (Fix #2)
        try:
            normalized = normalize_for_json(
                metadata_dict,
                path="metadata",
                allow_pydantic=True,  # Allow Pydantic models in metadata
                allow_string_fallback=False,  # Strict - no fallback
                logger=None  # No logger during validation
            )
        except TypeError as e:
            # Re-raise with context about metadata validation
            raise TypeError(
                f"ToolContext metadata validation failed: {e}. "
                f"Metadata must be JSON-serializable. "
                f"See quack_core.lib.serialization.normalize_for_json for details."
            ) from e

        # Return as immutable
        return MappingProxyType(normalized)

    # Serializers for MappingProxyType
    @field_serializer('services', 'metadata')
    def serialize_mapping(self, v: Mapping[str, Any]) -> dict[str, Any]:
        """Convert MappingProxyType to dict for serialization."""
        return dict(v)

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