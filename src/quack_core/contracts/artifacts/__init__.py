# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/artifacts/__init__.py
# module: quack_core.contracts.artifacts.__init__
# role: module
# neighbors: manifest.py, refs.py
# exports: StorageRef, Checksum, ArtifactRef, ToolInfo, Provenance, ManifestInput, RunManifest
# git_branch: feat/9-make-setup-work
# git_commit: ccfbaeea
# === QV-LLM:END ===

"""
Artifact and manifest models for tracking data flow.

These models define how artifacts are referenced, stored, and tracked
throughout the QuackCore system.
"""

from quack_core.contracts.artifacts.manifest import (
    ManifestInput,
    Provenance,
    RunManifest,
    ToolInfo,
)
from quack_core.contracts.artifacts.refs import (
    ArtifactRef,
    Checksum,
    StorageRef,
)

__all__ = [
    # Refs
    "StorageRef",
    "Checksum",
    "ArtifactRef",
    # Manifest
    "ToolInfo",
    "Provenance",
    "ManifestInput",
    "RunManifest",
]
