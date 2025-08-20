# quack-core/src/quack-core/integrations/google/__init__.py
"""
Google integrations package for QuackCore.

This package provides integrations with Google services,
such as Google Drive and Gmail, handling authentication
and API interactions with a consistent interface.
"""

from quackcore.integrations.google.auth import GoogleAuthProvider
from quackcore.integrations.google.config import GoogleConfigProvider

__all__ = [
    "GoogleAuthProvider",
    "GoogleConfigProvider",
]
