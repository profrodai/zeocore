# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/mail/operations/__init__.py
# module: quack_core.integrations.google.mail.operations.__init__
# role: operations
# neighbors: attachments.py, auth.py, email.py
# exports: email, auth, attachments
# git_branch: refactor/newHeaders
# git_commit: 72778e2
# === QV-LLM:END ===

"""
Operations package for Google Mail integration.

This package contains specialized modules for different Gmail _operations,
such as listing emails, downloading messages, and handling attachments.
"""

from quack_core.integrations.google.mail.operations import attachments, auth, email

__all__ = [
    "email",
    "auth",
    "attachments",
]
