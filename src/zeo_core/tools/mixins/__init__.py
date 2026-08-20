"""
Internal mixin exports.

⚠️ IMPORT FROM zeo_core.tools, NOT THIS MODULE ⚠️

Tool authors should NEVER import from this module directly.
Use canonical path: from zeo_core.tools import LifecycleMixin

This module exists for internal organization only.

ENFORCEMENT STRATEGY (Must-fix #4 - WARNING ONLY):

1. Default (no env vars): Silent - allows non-canonical imports

2. ZEO_WARN_NONCANONICAL_IMPORTS=1: Warning mode (RECOMMENDED for CI/dev)
   - Emits FutureWarning to stderr
   - Code continues to work
   - Good for development, migration, and CI pipelines

3. NO strict ImportError mode (Must-fix #4 - REMOVED)
   - Import-time ImportError breaks too much tooling
   - Use linter-based enforcement instead (see below)

WHY THE DEFAULT STAYS SILENT (investigated and confirmed, not just
inherited, during the zeocore-legibility-fixes stream -- see
CHANGELOG.md's Unreleased section): zeo_core.tools/__init__.py (the
canonical re-export site) imports from zeo_core.tools.mixins.env_init at
its own module scope. Because Python always fully imports a parent
package before any of its submodules, this means EVERY import of
anything under zeo_core.tools.* -- whether it is the canonical
`from zeo_core.tools import LifecycleMixin` or a non-canonical
`from zeo_core.tools.mixins import LifecycleMixin` -- causes
zeo_core.tools/__init__.py to run first, which in turn causes this
module's body (including this warning check) to execute as a side
effect. There is no way for code running inside this module to tell
those two cases apart: they produce an identical call stack, and no
sentinel set by zeo_core.tools/__init__.py can help either, because by
the time ANY import of zeo_core.tools.mixins.* resolves, the module is
already fully bootstrapped and cached -- the check-then-import ordering
below only ever executes once, on whichever import (canonical or not)
happens to be first in the process. A default-on warning was tried and
reverted after confirming it fires unconditionally on the fully correct,
documented `import zeo_core.tools` / `from zeo_core.tools import X` path
too -- which would be strictly worse than today's silent default (a
guaranteed false positive on every canonical import, versus zero signal
on a plausible-but-wrong one). Given that a runtime check cannot
distinguish the two cases, the actual fix for "an agent that greps the
repo tree and imports directly from a leaf module gets no signal" lives
where static reading (not runtime execution) can see it: see the banner
docstrings at the top of env_init.py, integration_enabled.py, and
lifecycle.py, which an agent opening any of those files via grep/IDE
navigation -- the discovery path this concern is actually about -- sees
immediately, with no import required to trigger it.

RECOMMENDED ENFORCEMENT (linter rules, not import-time behavior):

Use static analysis tools to enforce canonical imports:

Example ruff configuration (.ruff.toml or pyproject.toml):
    [tool.ruff.lint.flake8-import-conventions.banned-from]
    "zeo_core.tools.mixins" = "Import from zeo_core.tools instead"

Example pylint configuration (.pylintrc):
    [IMPORTS]
    forbidden-imports = zeo_core.tools.mixins

Example import-linter (.import-linter):
    [[contracts]]
    name = "Canonical imports only"
    type = "forbidden"
    source_modules = ["*"]
    forbidden_modules = ["zeo_core.tools.mixins"]

These approaches:
- Work in CI without breaking docs/IDEs
- Give better error messages
- Don't interfere with reflection/introspection
- Are opt-in per project
"""

import os
import warnings

# Warning mode (recommended for development and CI)
warn_mode = os.environ.get("ZEO_WARN_NONCANONICAL_IMPORTS")

if warn_mode:
    # Must-fix #3: Corrected warning message
    warnings.warn(
        "Non-canonical import path detected: importing from zeo_core.tools.mixins. "
        "Use canonical path instead: from zeo_core.tools import LifecycleMixin, etc. "
        "Direct submodule imports are discouraged and may break in future versions. "
        "(Disable this warning by unsetting ZEO_WARN_NONCANONICAL_IMPORTS)",
        FutureWarning,
        stacklevel=2,
    )

# Must-fix #4: NO strict ImportError mode
# Import-time enforcement breaks too many tools (Sphinx, MkDocs, IDEs, pytest fixtures).
# Use linter rules instead (see docstring for examples).

# INTERNAL IMPORTS: Always import specific modules, not package
# These sit below the warn_mode check above deliberately: the deprecation
# warning must fire as a consequence of importing this module, so the
# check-then-import ordering is load-bearing, not accidental placement.
from zeo_core.tools.mixins.env_init import ToolEnvInitializerMixin  # noqa: E402
from zeo_core.tools.mixins.integration_enabled import (  # noqa: E402
    IntegrationEnabledMixin,
)
from zeo_core.tools.mixins.lifecycle import LifecycleMixin  # noqa: E402

__all__ = [
    "IntegrationEnabledMixin",
    "LifecycleMixin",
    "ToolEnvInitializerMixin",
]
