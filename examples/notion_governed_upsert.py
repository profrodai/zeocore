"""Inspect the governed Notion page-upsert contract without credentials.

This example constructs the exact request that an authorized effect would
carry. It deliberately stops before custody or provider dispatch.
"""

from __future__ import annotations

import hashlib

from zeo_core.integrations.notion import (
    CitedText,
    NotionPageUpsertRequest,
    notion_page_upsert_revision,
)

DESTINATION = "87654321-4321-4321-8321-cba987654321"


def main() -> int:
    """Render an immutable request and its admitted operation."""
    source = b"meeting transcript bytes"
    source_digest = hashlib.sha256(source).hexdigest()
    marker = NotionPageUpsertRequest.marker_for(
        meeting_artifact_sha256=source_digest,
        destination_parent_id=DESTINATION,
    )
    request = NotionPageUpsertRequest(
        meeting_id="meeting-course",
        meeting_artifact_sha256=source_digest,
        interpretation_id="interpretation-course",
        interpretation_sha256="b" * 64,
        destination_parent_id=DESTINATION,
        title="Weekly course review",
        summary=CitedText(
            text="The cohort completed the lab.",
            source_citations=("transcript:12-18",),
        ),
        decisions=(
            CitedText(
                text="Keep the next lab local-first.",
                source_citations=("transcript:31-34",),
            ),
        ),
        idempotency_marker=marker,
    )
    revision = notion_page_upsert_revision()

    print("operation:", revision.operations[0].operation_id)
    print("revision:", revision.revision_id)
    print("marker bound:", request.idempotency_marker == marker)
    print("source cited:", "transcript:12-18" in request.canonical_markdown())
    print("provider called: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
