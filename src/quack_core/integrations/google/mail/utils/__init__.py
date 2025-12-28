# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/mail/utils/__init__.py
# module: quack_core.integrations.google.mail.utils.__init__
# role: utils
# neighbors: api.py
# exports: api
# git_branch: refactor/newHeaders
# git_commit: 175956c
# === QV-LLM:END ===

"""
Utilities package for Google Mail integration.

This package provides reusable utility functions for Gmail _operations,
including API wrappers and error handling.
"""

from quack_core.integrations.google.mail.utils import api

__all__ = [
    "api",
]
