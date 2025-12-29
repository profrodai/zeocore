# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/mail/test_mail.py
# role: tests
# neighbors: __init__.py, mocks.py, test_mail_service.py
# exports: TestGoogleMailService, TestGmailEmailOperations, TestGmailAttachmentOperations, TestGmailAuthOperations, TestGmailApiUtils
# git_branch: refactor/toolkitWorkflow
# git_commit: de0fa70
# === QV-LLM:END ===

"""
Main entry point for Google Mail integration tests.

This file imports all the specific test modules to ensure they are discovered
by pytest when running the test suite.
"""

# Import test modules to ensure they are discovered by pytest
from tests.test_integrations.google.mail.operations.test_attachments import (
    TestGmailAttachmentOperations,
)
from tests.test_integrations.google.mail.operations.test_auth import (
    TestGmailAuthOperations,
)
from tests.test_integrations.google.mail.operations.test_email import (
    TestGmailEmailOperations,
)
from tests.test_integrations.google.mail.test_mail_service import (
    TestGoogleMailService,
)
from tests.test_integrations.google.mail.utils.test_api import (
    TestGmailApiUtils,
)

# Export the test classes for direct import
__all__ = [
    "TestGoogleMailService",
    "TestGmailEmailOperations",
    "TestGmailAttachmentOperations",
    "TestGmailAuthOperations",
    "TestGmailApiUtils",
]
