"""Fixed-origin Gemini Interactions transport with no automatic request retry."""

from __future__ import annotations

import base64
import json

import httpx
from pydantic import BaseModel, ConfigDict, Field

from .models import ImageGenerationRequest

ORIGIN = "https://generativelanguage.googleapis.com"
API_PATH = "/v1beta/interactions"
MAX_RESPONSE_BYTES = 48 * 1024 * 1024


class ProviderStep(BaseModel):
    """Only model output steps may contribute generated images."""

    model_config = ConfigDict(extra="ignore")
    type: str
    content: tuple[dict[str, object], ...] = ()


class ProviderInteraction(BaseModel):
    """Narrow response projection; unrecognized transport is never guessed."""

    model_config = ConfigDict(extra="ignore")
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,1024}$")
    status: str
    steps: tuple[ProviderStep, ...] = ()


class ProviderRejectedError(RuntimeError):
    """An explicit request rejection, containing no raw provider content."""

    def __init__(self, status: int) -> None:
        self.status = status
        super().__init__(f"Image provider rejected the request with HTTP {status}")


class GeminiImageTransport:
    """Credentials remain inside this custody callback's transport instance."""

    def __init__(
        self, material: str, *, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._material = material.strip()
        self._transport = transport

    def create(
        self, request: ImageGenerationRequest, references: tuple[bytes, ...]
    ) -> ProviderInteraction:
        if len(references) != len(request.references):
            raise ValueError("reference byte inventory mismatch")
        content: list[dict[str, object]] = [{"type": "text", "text": request.prompt}]
        content.extend(
            {
                "type": "image",
                "mime_type": reference.mime_type,
                "data": base64.b64encode(value).decode(),
            }
            for reference, value in zip(request.references, references, strict=True)
        )
        payload = {
            "model": request.model,
            "input": content,
            "store": True,
            "response_format": {
                "type": "image",
                "mime_type": request.output_mime_type,
                "image_size": request.image_size,
                "aspect_ratio": request.aspect_ratio,
            },
        }
        return self._request("POST", API_PATH, payload)

    def get(self, interaction_id: str) -> ProviderInteraction:
        # Validate before interpolating even a provider-derived identifier into a URL.
        identifier = ProviderInteraction(id=interaction_id, status="unknown").id
        return self._request("GET", API_PATH + "/" + identifier, None)

    def _request(
        self, method: str, route: str, payload: dict[str, object] | None
    ) -> ProviderInteraction:
        status = 0
        body = bytearray()
        failed = False
        try:
            with httpx.Client(
                transport=self._transport,
                timeout=120,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                with client.stream(
                    method,
                    ORIGIN + route,
                    headers={
                        "x-goog-api-key": self._material,
                        "Content-Type": "application/json",
                    },
                    content=None if payload is None else json.dumps(payload).encode(),
                    # No user-supplied header or origin.
                ) as response:
                    status = response.status_code
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_RESPONSE_BYTES:
                            raise ValueError("response byte budget exceeded")
        except Exception:
            failed = True
        if failed:
            raise RuntimeError("Image provider response requires reconciliation")
        if status in {400, 401, 403, 404, 422, 429}:
            raise ProviderRejectedError(status)
        if status != 200:
            raise RuntimeError("Image provider response requires reconciliation")
        parsed: ProviderInteraction | None = None
        try:
            parsed = ProviderInteraction.model_validate_json(body)
        except Exception:
            parsed = None
        if parsed is None:
            raise RuntimeError("Image provider response shape requires reconciliation")
        return parsed
