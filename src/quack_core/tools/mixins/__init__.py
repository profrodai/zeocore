# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/mixins/__init__.py
# module: quack_core.tools.mixins.__init__
# role: module
# neighbors: env_init.py, integration_enabled.py, lifecycle.py, output_handler.py
# exports: IntegrationEnabledMixin, LifecycleMixin, ToolEnvInitializerMixin
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===



"""
Internal mixin exports.

⚠️ IMPORT FROM quack_core.tools, NOT THIS MODULE ⚠️

Tool authors should NEVER import from this module directly.
Use canonical path: from quack_core.tools import LifecycleMixin

This module exists for internal organization only.

ENFORCEMENT MODES (Fix #1 - documented behavior):

1. Default (no env vars): Silent - allows non-canonical imports

2. QUACK_WARN_NONCANONICAL_IMPORTS=1: Warning mode
   - Emits FutureWarning to stderr
   - Code continues to work
   - Good for development/migration

3. QUACK_ENFORCE_CANONICAL_IMPORTS=1: Strict mode (CI/production)
   - Raises ImportError immediately
   - Prevents non-canonical imports entirely
   - Use in CI pipelines for strict compliance

NOTE (Fix #1): Import-time enforcement can cause issues with:
- IDE auto-imports and static analyzers
- Documentation generators
- Third-party tooling that imports for inspection

For production enforcement, consider:
- Lint rules (e.g., pylint, ruff) checking import paths
- Runtime checks in quack_core.tools.__init__ instead
- Pre-commit hooks

If tooling breaks with QUACK_ENFORCE_CANONICAL_IMPORTS=1, unset it
and use linter-based enforcement instead.
"""

import os
import warnings

# Optional warning/enforcement for non-canonical imports
warn_mode = os.environ.get("QUACK_WARN_NONCANONICAL_IMPORTS")
enforce_mode = os.environ.get("QUACK_ENFORCE_CANONICAL_IMPORTS")

if enforce_mode:
    raise ImportError(
        "Importing from quack_core.tools.mixins is forbidden (QUACK_ENFORCE_CANONICAL_IMPORTS=1). "
        "Use canonical path: from quack_core.tools import LifecycleMixin, etc. "
        "\n\n"
        "This ensures single import path doctrine compliance. "
        "\n\n"
        "If this breaks tooling (IDEs, docs generators), unset QUACK_ENFORCE_CANONICAL_IMPORTS "
        "and use linter-based enforcement instead. See module docstring for details."
    )
elif warn_mode:
    warnings.warn(
        "Importing from quack_core.tools.mixins is discouraged. "
        "Use canonical path: from quack_core.tools import LifecycleMixin, etc. "
        "Direct submodule imports may break in future versions.",
        FutureWarning,
        stacklevel=2
    )

# INTERNAL IMPORTS: Always import specific modules, not package
# This avoids triggering enforcement when quack_core.tools.__init__ imports these
from quack_core.tools.mixins.integration_enabled import IntegrationEnabledMixin
from quack_core.tools.mixins.lifecycle import LifecycleMixin
from quack_core.tools.mixins.env_init import ToolEnvInitializerMixin

__all__ = [
    'IntegrationEnabledMixin',
    'LifecycleMixin',
    'ToolEnvInitializerMixin',
]