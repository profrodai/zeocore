# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/mail/operations/__init__.py
# === QV-LLM:END ===

"""
Operations package for Google Mail integration.

This package contains specialized modules for different Gmail _ops,
such as listing emails, downloading messages, and handling attachments.
"""

from quack_core.integrations.google.mail.operations import attachments, auth, email

__all__ = [
    "email",
    "auth",
    "attachments",
]
