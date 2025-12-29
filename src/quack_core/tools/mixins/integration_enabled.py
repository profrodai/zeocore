# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/mixins/integration_enabled.py
# module: quack_core.tools.mixins.integration_enabled
# role: module
# neighbors: __init__.py, env_init.py, lifecycle.py, output_handler.py
# exports: IntegrationEnabledMixin
# git_branch: refactor/toolkitWorkflow
# git_commit: 234aec0
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

from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from quack_core.tools.context import ToolContext

T = TypeVar("T")


class IntegrationEnabledMixin(Generic[T]):
    """
    Mixin for tools that need integration services.

    Services must be provided by runner in ToolContext.services.
    This mixin just provides convenient typed access.

    Example:
        >>> class MyTool(BaseQuackTool, IntegrationEnabledMixin):
        ...     def run(self, request, ctx):
        ...         # Get service by name (string key)
        ...         slack = ctx.get_service("slack")
        ...         if slack:
        ...             slack.send_message("Hello")
        ...
        ...         # Or require it (raises if missing)
        ...         github = ctx.require_service("github")
        ...         github.create_issue("Bug report")
    """

    def get_service(self, name: str, ctx: ToolContext) -> T | None:
        """
        Get a service from the context (if runner provided it).

        Args:
            name: Service name (e.g. "slack", "github")
            ctx: Tool context with services

        Returns:
            Service instance or None if not available

        Note:
            Services come from ctx.services (dict keyed by name).
            Runner is responsible for populating this dict.
        """
        return ctx.get_service(name)

    def require_service(self, name: str, ctx: ToolContext) -> T:
        """
        Get a service from context (raises if missing).

        Args:
            name: Service name (e.g. "slack", "github")
            ctx: Tool context with services

        Returns:
            Service instance

        Raises:
            ValueError: If service not available in context
        """
        return ctx.require_service(name)