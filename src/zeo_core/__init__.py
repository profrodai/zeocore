"""
zeo_core - Capability authoring framework and infrastructure library
(Ring A/B, Doctrine v3).

This is the package root. `dir(zeo_core)` / `import zeo_core` only
surfaces the zeo_core.tools authoring surface below (BaseZeoTool,
ToolContext, mixins, plus CapabilityResult as the one contracts symbol
every tool's run() signature needs) -- it does NOT re-export
zeo_core.config, zeo_core.core, zeo_core.integrations, zeo_core.modules,
or the rest of zeo_core.contracts. See README.md's "What's in the
package" table for the full module list; each of those modules is its
own import (e.g. `from zeo_core.config import load_config`,
`from zeo_core.contracts import ArtifactRef, RunManifest`), not reachable
from this top level. This is intentional namespacing, not an omission --
but it means dir(zeo_core)/autocomplete alone will undersell the package;
read GET-STARTED.md's "Core Modules Overview" for the rest.

CANONICAL IMPORT PATH for tools:
    from zeo_core.tools import BaseZeoTool, ToolContext, ...
    (equivalently, the same names are importable from zeo_core directly,
    as re-exported below)

DO NOT import from submodules:
    ❌ from zeo_core.tools.mixins import IntegrationEnabledMixin
    ✅ from zeo_core.tools import IntegrationEnabledMixin
    ✅ from zeo_core import IntegrationEnabledMixin

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
- CapabilityResult: The result envelope every tool's run() returns

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
"""

__version__ = "0.2.0"

# Core classes
from zeo_core.contracts.envelopes.result import CapabilityResult
from zeo_core.tools.base import BaseZeoTool
from zeo_core.tools.context import ToolContext
from zeo_core.tools.mixins.env_init import ToolEnvInitializerMixin

# Mixins (all exported at top level for single import path)
from zeo_core.tools.mixins.integration_enabled import IntegrationEnabledMixin
from zeo_core.tools.mixins.lifecycle import LifecycleMixin
from zeo_core.tools.protocol import ZeoToolProtocol

__all__ = [
    # Core
    "BaseZeoTool",
    "CapabilityResult",
    "ToolContext",
    "ZeoToolProtocol",
    # Mixins
    "IntegrationEnabledMixin",
    "LifecycleMixin",
    "ToolEnvInitializerMixin",
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
