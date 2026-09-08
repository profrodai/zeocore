"""Organization/project-scoped immutable image evidence outside authored IR."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from zeo_core.contracts.connections import OrganizationId

from .models import (
    ImageArtifact,
    ImageGenerationReceipt,
    ImageMime,
    InteractionBinding,
    check_image_signature,
    digest_bytes,
)


def _segment(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _persist(file: Path, value: bytes) -> None:
    """Publish fully written bytes once, and refuse conflicting rewrites."""
    file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(dir=file.parent, prefix=".pending-")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, file)
        except FileExistsError:
            if file.is_symlink() or file.read_bytes() != value:
                raise ValueError("immutable artifact conflict") from None
        directory = os.open(file.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)


class ImageArtifactStore:
    """The root is trusted Runtime configuration, never a provider request field."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _file(self, organization_id: OrganizationId, *segments: str) -> Path:
        file = self.root.joinpath(_segment(str(organization_id)), *segments)
        if file.resolve() != file:
            raise ValueError("artifact path escapes trusted store")
        return file

    def put_image(
        self,
        organization_id: OrganizationId,
        project_id: str,
        value: bytes,
        mime_type: ImageMime,
    ) -> ImageArtifact:
        check_image_signature(value, mime_type)
        artifact = ImageArtifact(
            digest=digest_bytes(value), mime_type=mime_type, byte_count=len(value)
        )
        file = self._file(
            organization_id, "projects", _segment(project_id), artifact.digest[7:]
        )
        _persist(file, value)
        return artifact

    def read_image(
        self, organization_id: OrganizationId, project_id: str, artifact: ImageArtifact
    ) -> bytes:
        file = self._file(
            organization_id, "projects", _segment(project_id), artifact.digest[7:]
        )
        if file.stat().st_size != artifact.byte_count:
            raise ValueError("image size changed")
        value = file.read_bytes()
        if digest_bytes(value) != artifact.digest:
            raise ValueError("image digest changed")
        check_image_signature(value, artifact.mime_type)
        return value

    def bind_interaction(self, binding: InteractionBinding) -> None:
        _persist(
            self._execution_file(binding, "interaction.json"),
            binding.model_dump_json().encode(),
        )

    def complete(self, receipt: ImageGenerationReceipt) -> None:
        _persist(
            self._execution_file(receipt, "complete.json"),
            receipt.model_dump_json().encode(),
        )

    def _execution_file(self, binding: InteractionBinding, name: str) -> Path:
        return self._file(
            OrganizationId(value=binding.organization_id),
            "executions",
            _segment(binding.execution_id),
            name,
        )

    def interaction(
        self, organization_id: OrganizationId, execution_id: str
    ) -> InteractionBinding | None:
        file = self._file(
            organization_id, "executions", _segment(execution_id), "interaction.json"
        )
        if not file.exists():
            return None
        return InteractionBinding.model_validate_json(file.read_bytes())

    def receipt(
        self, organization_id: OrganizationId, execution_id: str
    ) -> ImageGenerationReceipt | None:
        file = self._file(
            organization_id, "executions", _segment(execution_id), "complete.json"
        )
        if not file.exists():
            return None
        receipt = ImageGenerationReceipt.model_validate_json(file.read_bytes())
        if (
            receipt.organization_id != str(organization_id)
            or receipt.execution_id != execution_id
        ):
            raise ValueError("image evidence scope mismatch")
        for artifact in receipt.images:
            self.read_image(organization_id, receipt.project_id, artifact)
        return receipt
