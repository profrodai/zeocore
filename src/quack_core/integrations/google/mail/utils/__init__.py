# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/mail/utils/__init__.py
# module: quack_core.integrations.google.mail.utils.__init__
# role: utils
# neighbors: api.py
# exports: api
# git_branch: feat/9-make-setup-work
# git_commit: 8234fdcd
# === QV-LLM:END ===

"""
Utilities package for Google Mail integration.

This package provides reusable utility functions for Gmail _ops,
including API wrappers and error handling.
"""

from quack_core.integrations.google.mail.utils import api

__all__ = [
    "api",
]
