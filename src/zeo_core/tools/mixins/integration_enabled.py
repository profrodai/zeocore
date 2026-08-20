"""
Integration support for tools (doctrine-compliant).
Services come from ToolContext.services (runner-provided).

⚠️ DO NOT import IntegrationEnabledMixin from this module ⚠️
This is an internal implementation file. The canonical import path is:
    ✅ from zeo_core.tools import IntegrationEnabledMixin
    ❌ from zeo_core.tools.mixins.integration_enabled import IntegrationEnabledMixin
See zeo_core/tools/mixins/__init__.py's module docstring for why (opt in
to ZEO_WARN_NONCANONICAL_IMPORTS=1 to get a runtime FutureWarning on the
non-canonical path too, though it cannot fire in every case -- this
docstring is the reliable signal).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from zeo_core.tools.context import ToolContext

T = TypeVar("T")


class IntegrationEnabledMixin:
    """
    Mixin for tools that need integration services.
    Services must be provided by runner in ToolContext.services.
    """

    def get_service(
        self, name: str, ctx: ToolContext, expected_type: type[T] | None = None
    ) -> T | Any | None:  # noqa: ANN401 -- return is an arbitrary integration instance from the heterogeneous services registry; isinstance() narrows the runtime class but cannot prove T for the type checker
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
        self, name: str, ctx: ToolContext, expected_type: type[T] | None = None
    ) -> T | Any:  # noqa: ANN401 -- same rationale as get_service: arbitrary integration instance, isinstance() cannot prove T for the type checker
        """Get a service from context (raises if missing)."""
        svc = ctx.require_service(name)

        if expected_type is not None:
            if not isinstance(svc, expected_type):
                raise TypeError(
                    f"Service '{name}' is {type(svc).__name__}, "
                    f"expected {expected_type.__name__}"
                )
        return svc
