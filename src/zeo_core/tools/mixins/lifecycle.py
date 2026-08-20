"""
Lifecycle hooks for tools (doctrine-compliant).

⚠️ DO NOT import LifecycleMixin from this module ⚠️
This is an internal implementation file. The canonical import path is:
    ✅ from zeo_core.tools import LifecycleMixin
    ❌ from zeo_core.tools.mixins.lifecycle import LifecycleMixin
See zeo_core/tools/mixins/__init__.py's module docstring for why (opt in
to ZEO_WARN_NONCANONICAL_IMPORTS=1 to get a runtime FutureWarning on the
non-canonical path too, though it cannot fire in every case -- this
docstring is the reliable signal).

All hooks return CapabilityResult and receive ToolContext.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from zeo_core.contracts import CapabilityResult

if TYPE_CHECKING:
    from zeo_core.tools.context import ToolContext


class LifecycleMixin:
    """
    Mixin providing lifecycle hooks for tools.

    All hooks:
    - Return CapabilityResult (machine-readable)
    - Receive ToolContext (immutable)
    - Are optional (default: success)

    Example:
        >>> class MyTool(BaseZeoTool, LifecycleMixin):
        ...     def pre_run(self, request, ctx):
        ...         # Validation logic
        ...         return CapabilityResult.ok(data=None, msg="Pre-run passed")
        ...
        ...     def run(self, request, ctx):
        ...         return CapabilityResult.ok(data=result)
    """

    def pre_run(
        self,
        request: Any,  # noqa: ANN401 -- request type is per-tool (subclasses override with their own Pydantic request model)
        ctx: ToolContext,
    ) -> CapabilityResult[None]:
        """
        Hook called before run().

        Use for validation, pre-checks, etc.

        Args:
            request: Tool request
            ctx: Tool context

        Returns:
            CapabilityResult (success to continue, error to abort)
        """
        # Fix #5: explicit data=None for honest typing
        return CapabilityResult.ok(data=None, msg="Pre-run checks passed")

    def post_run(
        self,
        request: Any,  # noqa: ANN401 -- request type is per-tool (subclasses override with their own Pydantic request model)
        result: CapabilityResult,
        ctx: ToolContext,
    ) -> CapabilityResult:
        """
        Hook called after run().

        Use for post-processing, cleanup, etc.

        Args:
            request: Tool request
            result: Result from run()
            ctx: Tool context

        Returns:
            CapabilityResult (can modify or pass through)
        """
        return result

    def validate(
        self,
        request: Any,  # noqa: ANN401 -- request type is per-tool (subclasses override with their own Pydantic request model)
        ctx: ToolContext,
    ) -> CapabilityResult[None]:
        """
        Validation hook.

        Args:
            request: Tool request
            ctx: Tool context

        Returns:
            CapabilityResult (success if valid, error otherwise)
        """
        # Fix #5: explicit data=None for honest typing
        return CapabilityResult.ok(data=None, msg="Validation passed")

    def cleanup(self, ctx: ToolContext) -> CapabilityResult[None]:
        """
        Cleanup hook (called even on error).

        Args:
            ctx: Tool context

        Returns:
            CapabilityResult
        """
        # Fix #5: explicit data=None for honest typing
        return CapabilityResult.ok(data=None, msg="Cleanup completed")


# Backward compatibility alias
ZeoToolLifecycleMixin = LifecycleMixin
