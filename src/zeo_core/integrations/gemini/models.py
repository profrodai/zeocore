"""Closed, credential-free contracts for one reference-image generation."""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DIGEST = r"^sha256:[0-9a-f]{64}$"
IDENTIFIER = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$"
MAX_IMAGE_BYTES = 24 * 1024 * 1024
ImageMime = Literal["image/png", "image/jpeg", "image/webp"]


def digest_bytes(value: bytes) -> str:
    """Use the same explicit digest prefix as the production artifact IR."""
    return "sha256:" + hashlib.sha256(value).hexdigest()


class ImageArtifact(BaseModel):
    """An image in the trusted organization's project artifact store."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    digest: str = Field(pattern=DIGEST)
    mime_type: ImageMime
    byte_count: int = Field(gt=0, le=MAX_IMAGE_BYTES)


class ImageGenerationRequest(BaseModel):
    """One billed operation; references and intent are covered by authorization."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["zeo-image-generation/1"] = "zeo-image-generation/1"
    project_id: str = Field(pattern=IDENTIFIER)
    model: Literal["gemini-3.1-flash-image"] = "gemini-3.1-flash-image"
    prompt: str = Field(min_length=1, max_length=16_000)
    references: tuple[ImageArtifact, ...] = Field(min_length=1, max_length=6)
    output_mime_type: Literal["image/png", "image/jpeg"] = "image/png"
    aspect_ratio: Literal["1:1", "3:2", "2:3", "16:9", "9:16"] = "1:1"
    image_size: Literal["1K", "2K"] = "1K"

    @model_validator(mode="after")
    def _bounded_distinct_references(self) -> ImageGenerationRequest:
        if len({ref.digest for ref in self.references}) != len(self.references):
            raise ValueError("reference images must be distinct")
        if sum(ref.byte_count for ref in self.references) > 32 * 1024 * 1024:
            raise ValueError("reference images exceed the aggregate byte budget")
        if not self.prompt.strip():
            raise ValueError("prompt must contain text")
        return self


class InteractionBinding(BaseModel):
    """Durable provider identifier, bound to an exact broker dispatch."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    organization_id: str
    execution_id: str
    request_digest: str = Field(pattern=DIGEST)
    project_id: str = Field(pattern=IDENTIFIER)
    interaction_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,1024}$")


class ImageGenerationReceipt(InteractionBinding):
    """Artifact evidence, not an authorization or artistic acceptance verdict."""

    schema_version: Literal["zeo-generated-image-evidence/1"] = (
        "zeo-generated-image-evidence/1"
    )
    images: tuple[ImageArtifact, ...] = Field(min_length=1, max_length=4)
    qualification: Literal["UNREVIEWED"] = "UNREVIEWED"


def check_image_signature(value: bytes, mime_type: ImageMime) -> None:
    """Reject non-image transport; downstream image decoding remains mandatory."""
    signatures = {
        "image/png": value.startswith(b"\x89PNG\r\n\x1a\n") and len(value) >= 24,
        "image/jpeg": value.startswith(b"\xff\xd8\xff") and value.endswith(b"\xff\xd9"),
        "image/webp": value.startswith(b"RIFF") and value[8:12] == b"WEBP",
    }
    if not 0 < len(value) <= MAX_IMAGE_BYTES or not signatures[mime_type]:
        raise ValueError("image transport signature or byte budget is invalid")
