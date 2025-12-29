# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/__init__.py
# module: quack_core.tools.__init__
# role: module
# neighbors: base.py, context.py, protocol.py
# exports: BaseQuackTool, ToolContext, QuackToolProtocol, IntegrationEnabledMixin, LifecycleMixin, ToolEnvInitializerMixin, BaseQuackToolPlugin
# git_branch: refactor/toolkitWorkflow
# git_commit: 234aec0
# === QV-LLM:END ===



"""
quack_core.tools - Capability authoring framework (Ring B, Doctrine v3).

This package provides the base classes and protocols for creating
doctrine-compliant tools that work across all QuackCore orchestrators.

CANONICAL IMPORT PATH:
    from quack_core.tools import BaseQuackTool, ToolContext, ...

DO NOT import from submodules:
    ❌ from quack_core.tools.mixins import IntegrationEnabledMixin
    ✅ from quack_core.tools import IntegrationEnabledMixin

Tool authors should ONLY import from:
- quack_core.tools (this module)
- quack_core.contracts (request/response models, CapabilityResult)

NEVER import from:
- quack_runner.* (Ring C - orchestration)
- quack_core.workflow.* (doesn't exist anymore)

Key classes:
- BaseQuackTool: Base class for all tools
- ToolContext: Immutable dependency container
- QuackToolProtocol: Protocol for tool detection

Mixins (optional):
- IntegrationEnabledMixin: Access services from context
- LifecycleMixin: Pre/post run hooks
- ToolEnvInitializerMixin: Environment setup

Example:
    from quack_core.tools import BaseQuackTool, ToolContext
    from quack_core.contracts import CapabilityResult

    class MyTool(BaseQuackTool):
        def run(self, request, ctx: ToolContext) -> CapabilityResult:
            result = self._process(request, ctx)
            return CapabilityResult.ok(data=result, msg="Success")
"""

# Core classes
from quack_core.tools.base import BaseQuackTool
from quack_core.tools.context import ToolContext
from quack_core.tools.protocol import QuackToolProtocol

# Mixins (all exported at top level for single import path)
from quack_core.tools.mixins.integration_enabled import IntegrationEnabledMixin
from quack_core.tools.mixins.lifecycle import LifecycleMixin
from quack_core.tools.mixins.env_init import ToolEnvInitializerMixin

# Backward compatibility alias
BaseQuackToolPlugin = BaseQuackTool

__all__ = [
    # Core
    'BaseQuackTool',
    'ToolContext',
    'QuackToolProtocol',

    # Mixins
    'IntegrationEnabledMixin',
    'LifecycleMixin',
    'ToolEnvInitializerMixin',

    # Backward compatibility
    'BaseQuackToolPlugin',
]

# Tool Author Guidelines
"""
DOCTRINE COMPLIANCE CHECKLIST:

✅ DO:
- Inherit from BaseQuackTool
- Import from quack_core.tools (this module)
- Import contracts from quack_core.contracts
- Return CapabilityResult
- Receive ToolContext
- Treat context as immutable

❌ DON'T:
- Import from quack_runner.*
- Import from quack_core.workflow.*
- Import from quack_core.tools.mixins.* (use quack_core.tools instead)
- Write files directly (use runner)
- Create RunManifest (runner creates)
- Mutate ToolContext
- Auto-create services

Example imports:
    ✅ from quack_core.tools import BaseQuackTool, ToolContext
    ✅ from quack_core.contracts import CapabilityResult, MyRequest
    ❌ from quack_core.tools.mixins import IntegrationEnabledMixin
    ❌ from quack_runner.workflow import ToolRunner
"""