# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/github/utils/__init__.py
# module: quack_core.integrations.github.utils.__init__
# role: utils
# neighbors: api.py
# exports: make_request
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

"""Utility functions for GitHub integration."""

from .api import make_request

__all__ = ["make_request"]
