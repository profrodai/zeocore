"""Resolve an explicit fake Drive service; no pairing, credential or network."""

from pathlib import Path
from tempfile import TemporaryDirectory

from zeo_core.integrations.hosted import (
    ExecutionProfile,
    FakeGoogleDriveService,
    Ready,
    ServiceRequirement,
    ServiceResolver,
)


def main() -> None:
    requirement = ServiceRequirement(
        service="google.drive",
        operations=("google.drive.file.download",),
    )
    resolver = ServiceResolver(
        profile=ExecutionProfile.FAKE,
        fake_services={
            "google.drive": FakeGoogleDriveService({"selected": b"sample\n"})
        },
    )
    resolved = resolver.resolve(requirement)
    assert isinstance(resolved, Ready)
    assert resolved.service.initialize().success
    with TemporaryDirectory(prefix="zeocore-profile-", dir=Path.cwd()) as temporary:
        path = Path(temporary) / "selected.txt"
        result = resolved.service.download_file("selected", str(path))
        assert result.success and path.read_bytes() == b"sample\n"
    print("FAKE: selected Drive bytes verified; no credential or network")


if __name__ == "__main__":
    main()
