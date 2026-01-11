# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/__init__.py
# module: quack_core.integrations.google.__init__
# role: module
# neighbors: config.py, auth.py, serialization.py
# exports: GoogleAuthProvider, GoogleConfigProvider
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
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
