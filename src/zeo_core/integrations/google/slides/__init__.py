"""Google Slides integration for zeo_core.

Read + write access to Google Slides presentations via the
`googleapiclient` Slides v1 REST API, using the same OAuth
(`InstalledAppFlow` + local-server) flow as `integrations.google.drive`/
`mail`/`calendar`/`docs` -- reuses `GoogleAuthProvider` and
`GoogleConfigProvider` as-is, no new auth or config mechanism invented.

Per RULING-408 (the "workspace triple" design ruling) DESIGN-04, this is
the curated subset of Slides' API surface: 3 of its 5 methods
(`get_presentation` / `create_presentation` / `batch_update`, wrapping
`presentations.get` / `presentations.create` / `presentations.
batchUpdate`), omitting both thumbnail-generation methods. No index-free
convenience methods are layered on top of `batch_update` here, unlike
`google.docs`: Slides' hazard is order PRESERVATION, not index
invalidation, so there is no analogous need.

Follows the same registration shape as `integrations.google.docs`: a
shared config model in `google/config.py`, a service class implementing
`SlidesIntegrationProtocol`, and registration under the
`zeo_core.integrations` entry-point group (see this repo's `pyproject.toml`,
`[project.entry-points."zeo_core.integrations"]`, key `google.slides`).

Quickstart::

    from zeo_core.integrations.google.slides import (
        GoogleSlidesService,
        SlidesRequestBuilder,
        new_object_id,
    )

    slides = GoogleSlidesService(
        client_secrets_file="config/google_client_secret.json",
        credentials_file="config/google_credentials.json",
    )
    result = slides.initialize()
    assert result.success

    # Read
    presentation = slides.get_presentation("1AbCDeFGhijKLmnoPQRstuVWxyz")

    # Write: create a presentation, then add a slide and text on it in
    # ONE batch -- caller order is preserved, so the second request can
    # safely reference the objectId the first request creates.
    created = slides.create_presentation(title="Q3 review")
    presentation_id = created.content["presentationId"]

    slide_id = new_object_id("slide")
    requests = (
        SlidesRequestBuilder()
        .add({"createSlide": {"objectId": slide_id}})
        .add(
            {
                "createShape": {
                    "objectId": new_object_id("box"),
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {"pageObjectId": slide_id},
                }
            }
        )
        .build()
    )
    slides.batch_update(presentation_id, requests)

Every call returns an `IntegrationResult[T]` (`.success`, `.content`,
`.error`) -- see `zeo_core.integrations.core.results`.
"""

from __future__ import annotations

from zeo_core.integrations.google.slides.models import Color
from zeo_core.integrations.google.slides.protocols import (
    SlidesIntegrationProtocol,
)
from zeo_core.integrations.google.slides.request_builder import (
    SlidesRequestBuilder,
    new_object_id,
)
from zeo_core.integrations.google.slides.service import GoogleSlidesService

__all__ = [
    "GoogleSlidesService",
    "Color",
    "SlidesRequestBuilder",
    "SlidesIntegrationProtocol",
    "new_object_id",
    "create_integration",
]


def create_integration() -> SlidesIntegrationProtocol:
    """
    Create and configure a Google Slides integration.

    This function is used as an entry point for automatic integration
    discovery.

    Returns:
        SlidesIntegrationProtocol: Configured Google Slides service.
    """
    return GoogleSlidesService()
