"""
zeo_core.tools - Capability authoring framework (Ring B, Doctrine v3).

This package provides the base classes and protocols for creating
doctrine-compliant tools that work across all ZeoCore orchestrators.

CANONICAL IMPORT PATH:
    from zeo_core.tools import BaseZeoTool, ToolContext, ...

DO NOT import from submodules:
    ❌ from zeo_core.tools.mixins import IntegrationEnabledMixin
    ✅ from zeo_core.tools import IntegrationEnabledMixin

Tool authors should ONLY import from:
- zeo_core.tools (this module)
- zeo_core.contracts (request/response models, CapabilityResult)

NEVER import from:
- zeo_runner.* (Ring C - orchestration)
- zeo_core.workflow.* (doesn't exist anymore)

Key classes:
- BaseZeoTool: Base class for all tools
- ToolContext: Immutable dependency container
- ZeoToolProtocol: Protocol for tool detection

Mixins (optional):
- IntegrationEnabledMixin: Access services from context
- LifecycleMixin: Pre/post run hooks
- ToolEnvInitializerMixin: Environment setup

Example:
    from zeo_core.tools import BaseZeoTool, ToolContext
    from zeo_core.contracts import CapabilityResult

    class MyTool(BaseZeoTool):
        def run(self, request, ctx: ToolContext) -> CapabilityResult:
            result = self._process(request, ctx)
            return CapabilityResult.ok(data=result, msg="Success")
TERMINOLOGY:
- Tool: A concrete implementation of a capability (inherits BaseZeoTool)
- Capability: The abstract function/transformation a tool provides
- CapabilityResult: The machine-readable outcome of executing a capability

Example: EchoTool is a tool that provides the "echo" capability,
         returning a CapabilityResult when executed.
"""

# Core classes
from zeo_core.tools.adapter import ToolAdapterError, tool_to_capability
from zeo_core.tools.authoring import (
    CapabilityAuthoringError,
    bound_capability_of,
    capability,
)
from zeo_core.tools.base import BaseZeoTool
from zeo_core.tools.capability_protocol import ZeoCapability
from zeo_core.tools.context import ToolContext
from zeo_core.tools.definition_builder import build_definition, coordination_key
from zeo_core.tools.invoke import (
    BoundCapability,
    invocation_record,
    invoke_async,
    invoke_sync,
    resource_coordination_key,
)
from zeo_core.tools.mixins.env_init import ToolEnvInitializerMixin

# Mixins (all exported at top level for single import path)
from zeo_core.tools.mixins.integration_enabled import IntegrationEnabledMixin
from zeo_core.tools.mixins.lifecycle import LifecycleMixin
from zeo_core.tools.operations import register_capability_operation
from zeo_core.tools.protocol import ZeoToolProtocol
from zeo_core.tools.registry import (
    CapabilityProvenance,
    CapabilityRegistry,
    CapabilityRegistryError,
    get_capability_registry,
    reset_capability_registry,
)
from zeo_core.tools.services import (
    NeverCancelled,
    RecordingArtifactSink,
    SystemClock,
)

# Backward compatibility alias
ZeoToolLifecycleMixin = LifecycleMixin

__all__ = [
    # Core
    "BaseZeoTool",
    "ToolContext",
    "ZeoToolProtocol",
    "ZeoCapability",
    "BoundCapability",
    "capability",
    "bound_capability_of",
    "CapabilityAuthoringError",
    "tool_to_capability",
    "ToolAdapterError",
    "build_definition",
    "coordination_key",
    "invoke_sync",
    "invoke_async",
    "invocation_record",
    "resource_coordination_key",
    "CapabilityRegistry",
    "CapabilityRegistryError",
    "CapabilityProvenance",
    "get_capability_registry",
    "reset_capability_registry",
    "register_capability_operation",
    "SystemClock",
    "NeverCancelled",
    "RecordingArtifactSink",
    # Mixins
    "IntegrationEnabledMixin",
    "LifecycleMixin",
    "ToolEnvInitializerMixin",
    # Backward compatibility
    "ZeoToolLifecycleMixin",
]

# Tool Author Guidelines
"""
DOCTRINE COMPLIANCE CHECKLIST:

✅ DO:
- Inherit from BaseZeoTool
- Import from zeo_core.tools (this module)
- Import contracts from zeo_core.contracts
- Return CapabilityResult
- Receive ToolContext
- Treat context as immutable

❌ DON'T:
- Import from zeo_runner.*
- Import from zeo_core.workflow.*
- Import from zeo_core.tools.mixins.* (use zeo_core.tools instead)
- Write files directly (use runner)
- Create RunManifest (runner creates)
- Mutate ToolContext
- Auto-create services

Example imports:
    ✅ from zeo_core.tools import BaseZeoTool, ToolContext
    ✅ from zeo_core.contracts import CapabilityResult, MyRequest
    ❌ from zeo_core.tools.mixins import IntegrationEnabledMixin
    ❌ from zeo_runner.workflow import ToolRunner
"""
