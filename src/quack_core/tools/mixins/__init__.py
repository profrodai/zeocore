# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/mixins/__init__.py
# module: quack_core.tools.mixins.__init__
# role: module
# neighbors: env_init.py, integration_enabled.py, lifecycle.py, output_handler.py
# exports: IntegrationEnabledMixin, LifecycleMixin, ToolEnvInitializerMixin
# git_branch: refactor/toolkitWorkflow
# git_commit: 5d876e8
# === QV-LLM:END ===



"""
Internal mixin exports.

⚠️ IMPORT FROM quack_core.tools, NOT THIS MODULE ⚠️

Tool authors should NEVER import from this module directly.
Use canonical path: from quack_core.tools import LifecycleMixin

This module exists for internal organization only.

ENFORCEMENT STRATEGY (Recommendation A - softened):

1. Default (no env vars): Silent - allows non-canonical imports

2. QUACK_WARN_NONCANONICAL_IMPORTS=1: Warning mode (RECOMMENDED)
   - Emits FutureWarning to stderr
   - Code continues to work
   - Good for development/migration/CI

3. QUACK_ENFORCE_CANONICAL_IMPORTS=1: Strict mode (USE WITH CAUTION)
   - Raises ImportError immediately
   - WILL BREAK: IDEs, docs generators, test harnesses, introspection tools
   - NOT RECOMMENDED for general use
   - Use linter rules instead (see below)

RECOMMENDED ENFORCEMENT (instead of import-time ImportError):
- Use ruff/pylint rules to check import paths
- Add pre-commit hooks
- Use import-linter in CI
- These won't break tooling and give better error messages

Example ruff rule:
    [tool.ruff.lint.flake8-import-conventions.banned-from]
    "quack_core.tools.mixins" = "Import from quack_core.tools instead"

If you must use QUACK_ENFORCE_CANONICAL_IMPORTS=1, be aware:
- pytest fixtures that import this may break
- sphinx-autodoc may fail
- IDE autocomplete may be affected
- mypy/pyright in some configurations may fail
"""

import os
import warnings

# Warning mode (recommended for CI/development)
warn_mode = os.environ.get("QUACK_WARN_NONCANONICAL_IMPORTS")

# Strict mode (use with caution - see docstring)
enforce_mode = os.environ.get("QUACK_ENFORCE_CANONICAL_IMPORTS")

if enforce_mode:
    # Recommendation A: Make it very clear this is risky
    raise ImportError(
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "QUACK_ENFORCE_CANONICAL_IMPORTS=1 blocks non-canonical imports.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Import from: from quack_core.tools import LifecycleMixin\n"
        "Not from:    from quack_core.tools.mixins import LifecycleMixin\n"
        "\n"
        "⚠️  WARNING: This enforcement can break tooling:\n"
        "   - IDEs and autocomplete\n"
        "   - Documentation generators (sphinx, mkdocs)\n"
        "   - Test frameworks and fixtures\n"
        "   - Static analysis tools\n"
        "\n"
        "RECOMMENDED: Use linter-based enforcement instead:\n"
        "   - ruff banned-imports rule\n"
        "   - pylint import-checker\n"
        "   - import-linter in CI\n"
        "\n"
        "See module docstring for examples and safer alternatives.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
elif warn_mode:
    warnings.warn(
        "Importing from quack_core.tools.mixins is discouraged. "
        "Use canonical path: from quack_core.tools import LifecycleMixin, etc. "
        "Set QUACK_WARN_NONCANONICAL_IMPORTS=1 to enable this check.",
        FutureWarning,
        stacklevel=2
    )

# INTERNAL IMPORTS: Always import specific modules, not package
from quack_core.tools.mixins.integration_enabled import IntegrationEnabledMixin
from quack_core.tools.mixins.lifecycle import LifecycleMixin
from quack_core.tools.mixins.env_init import ToolEnvInitializerMixin

__all__ = [
    'IntegrationEnabledMixin',
    'LifecycleMixin',
    'ToolEnvInitializerMixin',
]