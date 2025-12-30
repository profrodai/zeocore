# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/mixins/integration_enabled.py
# module: quack_core.tools.mixins.integration_enabled
# role: module
# neighbors: __init__.py, env_init.py, lifecycle.py, output_handler.py
# exports: IntegrationEnabledMixin
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===



"""
Integration support for tools (doctrine-compliant).

Services come from ToolContext.services (runner-provided), NOT from global registry.
No service discovery. No hidden initialization.

Changes from legacy:
- Services must be in ctx.services dict (keyed by name string)
- Runner populates services, not mixin
- No global get_integration_service() calls
- No automatic initialization
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from quack_core.tools.context import ToolContext

T = TypeVar("T")


class IntegrationEnabledMixin:
    """
    Mixin for tools that need integration services.

    Services must be provided by runner in ToolContext.services.
    This mixin provides convenient typed access with optional validation.

    Example:
        >>> class MyTool(BaseQuackTool, IntegrationEnabledMixin):
        ...     def run(self, request, ctx):
        ...         # Get service by name (returns Any)
        ...         slack = self.get_service("slack", ctx)
        ...         if slack:
        ...             slack.send_message("Hello")
        ...
        ...         # Get with type validation
        ...         github = self.get_service("github", ctx, expected_type=GitHubService)
        ...         github.create_issue("Bug")  # IDE knows type
    """

    def get_service(
            self,
            name: str,
            ctx: ToolContext,
            expected_type: type[T] | None = None
    ) -> T | Any | None:
        """
        Get a service from the context (if runner provided it).

        Args:
            name: Service name (e.g. "slack", "github")
            ctx: Tool context with services
            expected_type: Optional type to validate against

        Returns:
            Service instance or None if not available

        Raises:
            TypeError: If service exists but doesn't match expected_type

        Example:
            >>> # Without type checking (returns Any | None)
            >>> slack = self.get_service("slack", ctx)
            >>>
            >>> # With type checking (returns SlackService | None)
            >>> slack = self.get_service("slack", ctx, expected_type=SlackService)
            >>> if slack:
            ...     slack.send_message("Hello")  # Type-safe
        """
        svc = ctx.get_service(name)
        if svc is None:
            return None

        # Optional type validation (fix #1 - actually useful)
        if expected_type is not None:
            if not isinstance(svc, expected_type):
                raise TypeError(
                    f"Service '{name}' is {type(svc).__name__}, "
                    f"expected {expected_type.__name__}"
                )

        return svc

    def require_service(
            self,
            name: str,
            ctx: ToolContext,
            expected_type: type[T] | None = None
    ) -> T | Any:
        """
        Get a service from context (raises if missing).

        Args:
            name: Service name (e.g. "slack", "github")
            ctx: Tool context with services
            expected_type: Optional type to validate against

        Returns:
            Service instance

        Raises:
            ValueError: If service not available in context
            TypeError: If service exists but doesn't match expected_type

        Example:
            >>> # Without type checking
            >>> github = self.require_service("github", ctx)
            >>>
            >>> # With type checking (type-safe)
            >>> github = self.require_service("github", ctx, expected_type=GitHubService)
            >>> github.create_issue("Bug")  # IDE knows type
        """
        svc = ctx.require_service(name)

        # Optional type validation (fix #1)
        if expected_type is not None:
            if not isinstance(svc, expected_type):
                raise TypeError(
                    f"Service '{name}' is {type(svc).__name__}, "
                    f"expected {expected_type.__name__}"
                )

        return svc
