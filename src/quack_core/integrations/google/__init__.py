# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/__init__.py
# module: quack_core.integrations.google.__init__
# role: module
# neighbors: config.py, auth.py, serialization.py
# exports: GoogleAuthProvider, GoogleConfigProvider
# git_branch: refactor/toolkitWorkflow
# git_commit: 5d876e8
# === QV-LLM:END ===

"""
Google integrations package for quack_core.

This package provides integrations with Google services,
such as Google Drive and Gmail, handling authentication
and API interactions with a consistent interface.
"""

from quack_core.integrations.google.auth import GoogleAuthProvider
from quack_core.integrations.google.config import GoogleConfigProvider

__all__ = [
    "GoogleAuthProvider",
    "GoogleConfigProvider",
]
