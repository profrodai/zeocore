# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/mixins/__init__.py
# module: quack_core.tools.mixins.__init__
# role: module
# neighbors: env_init.py, integration_enabled.py, lifecycle.py, output_handler.py
# exports: IntegrationEnabledMixin, LifecycleMixin, ToolEnvInitializerMixin
# git_branch: feat/9-make-setup-work
# git_commit: ccfbaeea
# === QV-LLM:END ===


"""
Internal mixin exports.

⚠️ IMPORT FROM quack_core.tools, NOT THIS MODULE ⚠️

Tool authors should NEVER import from this module directly.
Use canonical path: from quack_core.tools import LifecycleMixin

This module exists for internal organization only.

ENFORCEMENT STRATEGY (Must-fix #4 - WARNING ONLY):

1. Default (no env vars): Silent - allows non-canonical imports

2. QUACK_WARN_NONCANONICAL_IMPORTS=1: Warning mode (RECOMMENDED for CI/dev)
   - Emits FutureWarning to stderr
   - Code continues to work
   - Good for development, migration, and CI pipelines

3. NO strict ImportError mode (Must-fix #4 - REMOVED)
   - Import-time ImportError breaks too much tooling
   - Use linter-based enforcement instead (see below)

RECOMMENDED ENFORCEMENT (linter rules, not import-time behavior):

Use static analysis tools to enforce canonical imports:

Example ruff configuration (.ruff.toml or pyproject.toml):
    [tool.ruff.lint.flake8-import-conventions.banned-from]
    "quack_core.tools.mixins" = "Import from quack_core.tools instead"

Example pylint configuration (.pylintrc):
    [IMPORTS]
    forbidden-imports = quack_core.tools.mixins

Example import-linter (.import-linter):
    [[contracts]]
    name = "Canonical imports only"
    type = "forbidden"
    source_modules = ["*"]
    forbidden_modules = ["quack_core.tools.mixins"]

These approaches:
- Work in CI without breaking docs/IDEs
- Give better error messages
- Don't interfere with reflection/introspection
- Are opt-in per project
"""

import os
import warnings

# Warning mode (recommended for development and CI)
warn_mode = os.environ.get("QUACK_WARN_NONCANONICAL_IMPORTS")

if warn_mode:
    # Must-fix #3: Corrected warning message
    warnings.warn(
        "Non-canonical import path detected: importing from quack_core.tools.mixins. "
        "Use canonical path instead: from quack_core.tools import LifecycleMixin, etc. "
        "Direct submodule imports are discouraged and may break in future versions. "
        "(Disable this warning by unsetting QUACK_WARN_NONCANONICAL_IMPORTS)",
        FutureWarning,
        stacklevel=2
    )

# Must-fix #4: NO strict ImportError mode
# Import-time enforcement breaks too many tools (Sphinx, MkDocs, IDEs, pytest fixtures).
# Use linter rules instead (see docstring for examples).

# INTERNAL IMPORTS: Always import specific modules, not package
from quack_core.tools.mixins.integration_enabled import IntegrationEnabledMixin
from quack_core.tools.mixins.lifecycle import LifecycleMixin
from quack_core.tools.mixins.env_init import ToolEnvInitializerMixin

__all__ = [
    'IntegrationEnabledMixin',
    'LifecycleMixin',
    'ToolEnvInitializerMixin',
]