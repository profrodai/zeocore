# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/mixins/lifecycle.py
# module: quack_core.tools.mixins.lifecycle
# role: module
# neighbors: __init__.py, env_init.py, integration_enabled.py, output_handler.py
# exports: LifecycleMixin
# git_branch: feat/9-make-setup-work
# git_commit: ccfbaeea
# === QV-LLM:END ===



"""
Lifecycle hooks for tools (doctrine-compliant).

All hooks return CapabilityResult and receive ToolContext.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quack_core.contracts import CapabilityResult

if TYPE_CHECKING:
    from quack_core.tools.context import ToolContext


class LifecycleMixin:
    """
    Mixin providing lifecycle hooks for tools.

    All hooks:
    - Return CapabilityResult (machine-readable)
    - Receive ToolContext (immutable)
    - Are optional (default: success)

    Example:
        >>> class MyTool(BaseQuackTool, LifecycleMixin):
        ...     def pre_run(self, request, ctx):
        ...         # Validation logic
        ...         return CapabilityResult.ok(data=None, msg="Pre-run passed")
        ...
        ...     def run(self, request, ctx):
        ...         return CapabilityResult.ok(data=result)
    """

    def pre_run(
            self,
            request: Any,
            ctx: ToolContext
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
            request: Any,
            result: CapabilityResult,
            ctx: ToolContext
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
            request: Any,
            ctx: ToolContext
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

    def cleanup(
            self,
            ctx: ToolContext
    ) -> CapabilityResult[None]:
        """
        Cleanup hook (called even on error).

        Args:
            ctx: Tool context

        Returns:
            CapabilityResult
        """
        # Fix #5: explicit data=None for honest typing
        return CapabilityResult.ok(data=None, msg="Cleanup completed")