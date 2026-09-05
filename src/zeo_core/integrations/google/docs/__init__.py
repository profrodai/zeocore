"""Google Docs integration for zeo_core.

Read + write access to Google Docs documents via the `googleapiclient` Docs
v1 REST API, using the same OAuth (`InstalledAppFlow` + local-server) flow
as `integrations.google.drive`/`mail`/`calendar` -- reuses `GoogleAuthProvider`
and `GoogleConfigProvider` as-is, no new auth or config mechanism invented.

Per RULING-408 (the "workspace triple" design ruling), this is the smallest
of the Sheets/Docs/Slides follow-on integrations: exactly 3 API methods
(`get_document` / `create_document` / `batch_update`, wrapping
`documents.get` / `documents.create` / `documents.batchUpdate`), plus two
index-free convenience methods built on `batch_update`
(`replace_text`/`append_text`) and a recursive plain-text extraction helper
(`get_document_text`).

Follows the same registration shape as `integrations.google.calendar`: a
shared config model in `google/config.py`, a service class implementing
`DocsIntegrationProtocol`, and registration under the
`zeo_core.integrations` entry-point group (see this repo's `pyproject.toml`,
`[project.entry-points."zeo_core.integrations"]`, key `google.docs`).

Quickstart::

    from zeo_core.integrations.google.docs import GoogleDocsService

    docs = GoogleDocsService(
        client_secrets_file="config/google_client_secret.json",
        credentials_file="config/google_credentials.json",
    )
    result = docs.initialize()
    assert result.success

    # Read: fetch a document and its plain text
    doc = docs.get_document("1AbCDeFGhijKLmnoPQRstuVWxyz")
    text = docs.get_document_text("1AbCDeFGhijKLmnoPQRstuVWxyz")

    # Write: create a document, then edit it index-free
    created = docs.create_document(title="Meeting notes")
    document_id = created.content["documentId"]
    docs.append_text(document_id, "Agenda:\\n")
    docs.replace_text(document_id, find="TODO", replace="DONE")

Every call returns an `IntegrationResult[T]` (`.success`, `.content`,
`.error`) -- see `zeo_core.integrations.core.results`.
"""

from __future__ import annotations

from zeo_core.integrations.google.docs.models import Color
from zeo_core.integrations.google.docs.protocols import (
    DocsIntegrationProtocol,
    DocsReadProtocol,
)
from zeo_core.integrations.google.docs.request_builder import DocsRequestBuilder
from zeo_core.integrations.google.docs.service import GoogleDocsService

__all__ = [
    "GoogleDocsService",
    "Color",
    "DocsRequestBuilder",
    "DocsIntegrationProtocol",
    "DocsReadProtocol",
    "create_integration",
]


def create_integration() -> DocsIntegrationProtocol:
    """
    Create and configure a Google Docs integration.

    This function is used as an entry point for automatic integration
    discovery.

    Returns:
        DocsIntegrationProtocol: Configured Google Docs service.
    """
    return GoogleDocsService()
