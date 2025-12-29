# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/mixins/integration_enabled.py
# module: quack_core.tools.mixins.integration_enabled
# role: module
# neighbors: __init__.py, env_init.py, lifecycle.py, output_handler.py
# exports: IntegrationEnabledMixin
# git_branch: refactor/toolkitWorkflow
# git_commit: 07a259e
# === QV-LLM:END ===


"""
Integration support for tools (doctrine-compliant).

Services come from ToolContext (runner-provided), NOT from global registry.
No service discovery. No hidden initialization.

Changes from legacy:
- Services must be in ctx.metadata['services'] dict
- Runner populates services, not mixin
- No global get_integration_service() calls
- No automatic initialization
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar, Any

if TYPE_CHECKING:
    from quack_core.tools.context import ToolContext

T = TypeVar("T")


class IntegrationEnabledMixin(Generic[T]):
    """
    Mixin for tools that need integration services.

    Services must be provided by runner in ToolContext.
    This mixin just provides convenient access.

    Example:
        >>> class MyTool(BaseQuackTool, IntegrationEnabledMixin):
        ...     def run(self, request, ctx):
        ...         service = self.get_service(MyServiceType, ctx)
        ...         if service:
        ...             service.do_something()
    """

    def get_service(self, service_type: type[T], ctx: ToolContext) -> T | None:
        """
        Get a service from the context (if runner provided it).

        Args:
            service_type: The type of service to retrieve
            ctx: Tool context with services

        Returns:
            Service instance or None if not available

        Note:
            Services come from ctx.metadata['services'].
            Runner is responsible for populating this dict.
        """
        services = ctx.metadata.get('services', {})
        return services.get(service_type)

    def require_service(self, service_type: type[T], ctx: ToolContext) -> T:
        """
        Get a service from context (raises if missing).

        Args:
            service_type: The type of service to retrieve
            ctx: Tool context with services

        Returns:
            Service instance

        Raises:
            ValueError: If service not available in context
        """
        service = self.get_service(service_type, ctx)
        if service is None:
            raise ValueError(
                f"Service {service_type.__name__} not available in context. "
                f"Runner must provide it in ctx.metadata['services']."
            )
        return service