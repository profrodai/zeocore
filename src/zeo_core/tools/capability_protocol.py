"""Runtime-checkable capability protocol."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from zeo_core.contracts import CapabilityDefinition, CapabilityResult
from zeo_core.tools.context import ToolContext


@runtime_checkable
class ZeoCapability(Protocol):
    """
    Canonical capability protocol.

    Inheritance is not required. Class-based BaseZeoTool instances and
    function capabilities both satisfy this after adaptation.
    """

    definition: CapabilityDefinition

    def invoke(
        self,
        request: BaseModel,
        ctx: ToolContext,
    ) -> CapabilityResult[Any] | Awaitable[CapabilityResult[Any]]: ...

    def is_available(self, ctx: ToolContext) -> bool: ...
