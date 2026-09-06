"""Deterministic in-process services for tests and teaching."""

from __future__ import annotations

from collections.abc import Mapping

from zeo_core.core.fs.service import standalone
from zeo_core.integrations.core import IntegrationResult


class FakeGoogleDriveService:
    """Selected-file Drive behavior without credentials or network access."""

    def __init__(self, files: Mapping[str, bytes] | None = None) -> None:
        self._files = dict(files or {})
        self._initialized = False

    @property
    def name(self) -> str:
        return "FakeGoogleDrive"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def integration_id(self) -> str:
        return "google.drive"

    def initialize(self) -> IntegrationResult[None]:
        self._initialized = True
        return IntegrationResult.success_result(message="Fake Google Drive ready")

    def is_available(self) -> bool:
        return self._initialized

    def download_file(
        self, remote_id: str, local_path: str | None = None
    ) -> IntegrationResult[str]:
        if not self._initialized:
            return IntegrationResult.error_result(
                "Fake Google Drive is not initialized"
            )
        content = self._files.get(remote_id)
        if content is None:
            return IntegrationResult.error_result("Selected Drive file is unavailable")
        destination = local_path or remote_id
        write = standalone.write_bytes(destination, content)
        if not write.success:
            return IntegrationResult.error_result("Failed to write fake Drive artifact")
        return IntegrationResult.success_result(content=destination)


__all__ = ["FakeGoogleDriveService"]
