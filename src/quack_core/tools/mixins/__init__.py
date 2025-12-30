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

Tool authors should import from the canonical path:
    ✅ from quack_core.tools import LifecycleMixin
    ❌ from quack_core.tools.mixins import LifecycleMixin

This module exists for internal organization only.
Direct submodule imports may break in future versions.
"""

import os
import warnings

# Optional warning for non-canonical imports (fix #2 - gated by env var)
# Set QUACK_WARN_NONCANONICAL_IMPORTS=1 to enable in dev/CI
if os.environ.get("QUACK_WARN_NONCANONICAL_IMPORTS"):
    warnings.warn(
        "Importing from quack_core.tools.mixins is discouraged. "
        "Use canonical path: from quack_core.tools import LifecycleMixin, etc. "
        "Direct submodule imports may break in future versions.",
        FutureWarning,
        stacklevel=2
    )

from quack_core.tools.mixins.integration_enabled import IntegrationEnabledMixin
from quack_core.tools.mixins.lifecycle import LifecycleMixin
from quack_core.tools.mixins.env_init import ToolEnvInitializerMixin

__all__ = [
    'IntegrationEnabledMixin',
    'LifecycleMixin',
    'ToolEnvInitializerMixin',
]