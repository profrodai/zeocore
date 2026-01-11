# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/context.py
# module: quack_core.tools.context
# role: module
# neighbors: __init__.py, base.py, protocol.py
# exports: ToolContext
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===



"""
ToolContext: Immutable dependency container for tool execution.

TOP-LEVEL IMMUTABILITY: Uses MappingProxyType for services/metadata.
"""

from typing import Any, Mapping
from pathlib import Path
from types import MappingProxyType
from pydantic import BaseModel, ConfigDict, Field, field_validator, field_serializer

from quack_core.core.serialization import normalize_for_json


class ToolContext(BaseModel):
    """
    Immutable context for tool execution.

    The runner constructs this with all required services.
    Tools receive it as read-only and must not modify it.

    METADATA CONTRACT (ENFORCED):
    - Must be a Mapping (dict-like)
    - Must be JSON-serializable (validated on construction)
    - Uses shared normalize_for_json() - same logic as ToolRunner
    - Primitives: str, int, float, bool, None
    - Collections: list, dict (string keys only)
    - Safe types auto-converted: Path→str, datetime→isoformat, Enum→value
    - Pydantic models: converted via model_dump() (strict isinstance)
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

    # Must-fix B: Guard against None for services
    @field_validator('services', mode='before')
    @classmethod
    def validate_and_normalize_services(cls,
                                        v: dict[str, Any] | Mapping[str, Any] | None) -> \
    Mapping[str, Any]:
        """
        Validate services is a Mapping and convert to MappingProxyType.

        Must-fix B: Defensive coding - handle None gracefully.
        """
        if v is None:
            return MappingProxyType({})

        if isinstance(v, MappingProxyType):
            return v

        if not isinstance(v, Mapping):
            raise TypeError(
                f"services must be a Mapping (dict-like), got {type(v).__name__}"
            )

        return MappingProxyType(dict(v))

    # Must-fix #2: Strict type checking for metadata
    @field_validator('metadata', mode='before')
    @classmethod
    def validate_and_normalize_metadata(cls,
                                        v: dict[str, Any] | Mapping[str, Any] | None) -> \
    Mapping[str, Any]:
        """
        Validate metadata is a Mapping and JSON-serializable, then normalize.

        Must-fix #2: Explicitly enforce Mapping type before processing.
        """
        if v is None:
            return MappingProxyType({})

        if isinstance(v, MappingProxyType):
            return v

        # Must-fix #2: Strict type check BEFORE attempting conversion
        if not isinstance(v, Mapping):
            raise TypeError(
                f"metadata must be a Mapping (dict-like), got {type(v).__name__}. "
                f"Example: metadata={{'key': 'value'}}. "
                f"Cannot pass list, string, or other non-mapping types."
            )

        # Now safe to convert to dict
        metadata_dict = dict(v)

        # Use shared normalization logic
        try:
            normalized = normalize_for_json(
                metadata_dict,
                path="metadata",
                allow_pydantic=True,
                allow_string_fallback=False,
                logger=None
            )
        except TypeError as e:
            raise TypeError(
                f"ToolContext metadata validation failed: {e}. "
                f"Metadata must be JSON-serializable. "
                f"See quack_core.core.serialization.normalize_for_json for details."
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
        """Get work directory as Path for path computation (no I/O)."""
        return Path(self.work_dir)

    @property
    def output_path(self) -> Path:
        """Get output directory as Path (reference only, no direct writes)."""
        return Path(self.output_dir)

    # Accessor methods (pure - no side effects)

    def require_logger(self) -> Any:
        """Get logger (guaranteed non-None by runner)."""
        return self.logger

    def require_fs(self) -> Any:
        """Get filesystem service (guaranteed non-None by runner)."""
        return self.fs

    def get_service(self, name: str) -> Any | None:
        """Get a service by name (if runner provided it)."""
        return self.services.get(name)

    def require_service(self, name: str) -> Any:
        """
        Get a service by name (raises if missing).

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