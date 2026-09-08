"""Resolved Python/kernel identity, without ambient kernelspec discovery."""

import hashlib
import json
import sys
from importlib.metadata import distributions
from pathlib import Path


def environment_identity() -> dict[str, str]:
    """Hash the actual interpreter and installed distribution inventory."""
    inventory = sorted((d.metadata["Name"].lower(), d.version) for d in distributions())
    with Path(sys.executable).open("rb") as handle:
        executable_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    return {
        "executable_sha256": executable_hash,
        "environment_sha256": hashlib.sha256(
            json.dumps(inventory).encode()
        ).hexdigest(),
        "environment_identity_schema": "installed-distributions-v1",
    }


def resolved_identity(spec: Path, *, absolute_paths: bool = False) -> dict[str, str]:
    """Local paths are explicit opt-in; the managed location is otherwise logical."""
    result = environment_identity()
    result.update(
        kernelspec_sha256=hashlib.sha256(spec.read_bytes()).hexdigest(),
        kernelspec_location="managed/data/kernels/python3/kernel.json",
    )
    if absolute_paths:
        result.update(
            executable_path=str(Path(sys.executable).resolve()),
            kernelspec_path=str(spec),
        )
    return result
