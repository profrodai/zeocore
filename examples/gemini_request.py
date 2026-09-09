"""Build and verify a Gemini image request locally; never call a provider."""

import base64
from pathlib import Path
from tempfile import TemporaryDirectory

from zeo_core.contracts.connections import OrganizationId
from zeo_core.integrations.gemini import (
    OPERATION_ID,
    ImageArtifactStore,
    ImageGenerationRequest,
)

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8A"
    "AwMCAO+/l9sAAAAASUVORK5CYII="
)


def main() -> None:
    with TemporaryDirectory(prefix="zeocore-image-request-") as temporary:
        artifacts = ImageArtifactStore(Path(temporary))
        organization = OrganizationId(value="example-test")
        reference = artifacts.put_image(organization, "sample", PNG, "image/png")
        request = ImageGenerationRequest(
            project_id="sample",
            prompt="Preserve the reference design.",
            references=(reference,),
        )
        assert (
            artifacts.read_image(organization, "sample", request.references[0]) == PNG
        )
        print(f"Operation: {OPERATION_ID}")
        print("Reference bytes verified: True")
        print("REQUEST ONLY: no authorization minted; no provider called")


if __name__ == "__main__":
    main()
