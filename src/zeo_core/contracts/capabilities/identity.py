"""
Capability identity: immutable namespace, name, and semantic version.

Canonical string form: <namespace>.<name>@<version>
Example: google.calendar.event.create@1.0.0
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SEGMENT = r"[a-z][a-z0-9_]*"
_NAMESPACE_RE = re.compile(rf"^{_SEGMENT}(\.{_SEGMENT})*$")
_NAME_RE = re.compile(rf"^{_SEGMENT}$")
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_CANONICAL_RE = re.compile(
    rf"^(?P<namespace>{_SEGMENT}(?:\.{_SEGMENT})*)\.(?P<name>{_SEGMENT})"
    r"@(?P<version>.+)$"
)


class CapabilityId(BaseModel):
    """Immutable capability identity. Mutation after construction is forbidden."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    namespace: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)

    @field_validator("namespace")
    @classmethod
    def _validate_namespace(cls, value: str) -> str:
        if not _NAMESPACE_RE.match(value):
            raise ValueError(
                "namespace must be one or more dotted lowercase segments "
                f"(e.g. math or google.calendar), got {value!r}"
            )
        return value

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        if not _NAME_RE.match(value):
            raise ValueError(
                f"name must be a single lowercase identifier, got {value!r}"
            )
        return value

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str) -> str:
        if not _SEMVER_RE.match(value):
            raise ValueError(f"version must be a semantic version, got {value!r}")
        return value

    def canonical(self) -> str:
        """Return <namespace>.<name>@<version>."""
        return f"{self.namespace}.{self.name}@{self.version}"

    def __str__(self) -> str:
        return self.canonical()

    @classmethod
    def parse(cls, value: str) -> CapabilityId:
        """Parse a canonical identity string."""
        match = _CANONICAL_RE.match(value)
        if match is None:
            raise ValueError(
                f"capability id must look like 'namespace.name@1.0.0', got {value!r}"
            )
        version = match.group("version")
        if not _SEMVER_RE.match(version):
            raise ValueError(f"version must be a semantic version, got {version!r}")
        return cls(
            namespace=match.group("namespace"),
            name=match.group("name"),
            version=version,
        )

    @model_validator(mode="before")
    @classmethod
    def _coerce_canonical_string(cls, value: object) -> object:
        if isinstance(value, str):
            parsed = cls.parse(value)
            return {
                "namespace": parsed.namespace,
                "name": parsed.name,
                "version": parsed.version,
            }
        return value


def parse_semver(version: str) -> tuple[int, int, int]:
    """Return (major, minor, patch), ignoring pre-release/build metadata."""
    core = version.split("-", 1)[0].split("+", 1)[0]
    major, minor, patch = core.split(".")
    return int(major), int(minor), int(patch)
