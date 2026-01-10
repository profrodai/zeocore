# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/mixins/integration_enabled.py
# module: quack_core.tools.mixins.integration_enabled
# role: module
# neighbors: __init__.py, env_init.py, lifecycle.py, output_handler.py
# exports: IntegrationEnabledMixin
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===


"""
Integration support for tools (doctrine-compliant).
Services come from ToolContext.services (runner-provided).
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
    """

    def get_service(
            self,
            name: str,
            ctx: ToolContext,
            expected_type: type[T] | None = None
    ) -> T | Any | None:
        """Get a service from the context (if runner provided it)."""
        svc = ctx.get_service(name)
        if svc is None:
            return None

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
        """Get a service from context (raises if missing)."""
        svc = ctx.require_service(name)

        if expected_type is not None:
            if not isinstance(svc, expected_type):
                raise TypeError(
                    f"Service '{name}' is {type(svc).__name__}, "
                    f"expected {expected_type.__name__}"
                )
        return svc