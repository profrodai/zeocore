# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/mail/operations/__init__.py
# module: quack_core.integrations.google.mail.operations.__init__
# role: module
# neighbors: attachments.py, auth.py, email.py
# exports: email, auth, attachments
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
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
