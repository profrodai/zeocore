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

import importlib.metadata as _importlib_metadata

try:
    # Single source of truth: pyproject.toml's [project] version. Deriving
    # here means the installed distribution's metadata and this module's
    # __version__ can never disagree -- there is only one place left to
    # edit. A hand-maintained literal desynchronised silently across three
    # releases (RULING-414): real PyPI 0.4.0 shipped __version__ == "0.3.0",
    # and 0.5.0 was only "correct" by coincidence of an unrelated edit.
    __version__ = _importlib_metadata.version("zeocore")
except _importlib_metadata.PackageNotFoundError as _exc:  # pragma: no cover
    # Verified rather than assumed (2026-09-01): every documented install
    # path (`make install`/`make setup`, `pip install zeocore`, even a bare
    # `pip install -e . --no-deps`) registers distribution metadata. And
    # `import zeo_core` itself cannot succeed without that install having
    # happened, because this module unconditionally imports pydantic-backed
    # submodules below -- there is no "source checkout, zero install, but
    # somehow importable" path in this repo to fall back for. So this is
    # NOT a quiet default: a version string here would be indistinguishable
    # from a real one and would silently defeat the very drift this module
    # exists to prevent (RULING-414 §3). Fail loudly and name the fix.
    raise RuntimeError(
        "zeo_core is importable but has no installed distribution metadata "
        "(importlib.metadata.version('zeocore') raised "
        f"PackageNotFoundError: {_exc}). This should not be reachable: run "
        "`pip install -e .` or `make install` and re-import."
    ) from _exc

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
