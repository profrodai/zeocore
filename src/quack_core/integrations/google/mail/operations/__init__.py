# quack-core/src/quack-core/integrations/google/mail/operations/__init__.py
"""
Operations package for Google Mail integration.

This package contains specialized modules for different Gmail _operations,
such as listing emails, downloading messages, and handling attachments.
"""

from quackcore.integrations.google.mail.operations import attachments, auth, email

__all__ = [
    "email",
    "auth",
    "attachments",
]
