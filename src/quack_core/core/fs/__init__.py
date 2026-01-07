# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/__init__.py
# module: quack_core.core.fs.__init__
# role: module
# neighbors: protocols.py, plugin.py, results.py
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

"""
LEGACY MODULE - DEPRECATED

Use `quack_core.core.fs.api.public` or `quack_core.core.fs.service`.
"""
import warnings

warnings.warn(
    "quack_core.core.fs is deprecated. Use quack_core.core.fs.api.public or quack_core.core.fs.service instead.",
    DeprecationWarning,
    stacklevel=2
)