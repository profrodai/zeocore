# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/github/utils/__init__.py
# module: quack_core.integrations.github.utils.__init__
# role: utils
# neighbors: api.py
# exports: make_request
# git_branch: main
# git_commit: f0715f0c
# === QV-LLM:END ===

"""Utility functions for GitHub integration."""

from .api import make_request

__all__ = ["make_request"]
