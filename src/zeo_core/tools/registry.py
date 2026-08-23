"""Canonical in-process capability registry. Instance-first."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import entry_points

from zeo_core.contracts import CapabilityId, CapabilityManifest
from zeo_core.contracts.capabilities.identity import parse_semver
from zeo_core.tools.invoke import BoundCapability

ENTRY_POINT_GROUP = "zeo_core.capabilities"


class CapabilityRegistryError(ValueError):
    """Registry contract violation (duplicates, missing identity, etc.)."""


@dataclass(frozen=True, slots=True)
class CapabilityProvenance:
    source: str
    entry_point: str | None = None


class CapabilityRegistry:
    """
    Explicit in-process registry.

    Duplicate identity is rejected. Listing is sorted by canonical id.
    A process-global instance exists only as a test-resettable convenience
    and is never required by runners.
    """

    def __init__(self) -> None:
        self._by_canonical: dict[str, BoundCapability] = {}
        self._provenance: dict[str, CapabilityProvenance] = {}

    def register(
        self,
        capability: BoundCapability,
        *,
        provenance: CapabilityProvenance | None = None,
    ) -> None:
        key = capability.definition.id.canonical()
        if key in self._by_canonical:
            raise CapabilityRegistryError(f"duplicate capability identity: {key}")
        self._by_canonical[key] = capability
        self._provenance[key] = provenance or CapabilityProvenance(source="explicit")

    def get(self, identity: CapabilityId | str) -> BoundCapability:
        key = identity if isinstance(identity, str) else identity.canonical()
        if "@" not in key:
            resolved = self.resolve(key)
            if resolved is None:
                raise CapabilityRegistryError(f"capability not found: {key}")
            return resolved
        cap = self._by_canonical.get(key)
        if cap is None:
            raise CapabilityRegistryError(f"capability not found: {key}")
        return cap

    def resolve(
        self, namespace_name: str, *, version: str | None = None
    ) -> BoundCapability | None:
        """Exact version, or highest compatible same-major version."""
        matches: list[BoundCapability] = []
        for cap in self._by_canonical.values():
            ident = cap.definition.id
            prefix = f"{ident.namespace}.{ident.name}"
            if prefix != namespace_name:
                continue
            if version is None or ident.version == version:
                matches.append(cap)
        if version is not None:
            return matches[0] if matches else None
        if not matches:
            return None
        return max(matches, key=lambda c: parse_semver(c.definition.id.version))

    def resolve_compatible(self, identity: CapabilityId) -> BoundCapability | None:
        candidates: list[BoundCapability] = []
        want = parse_semver(identity.version)
        for cap in self._by_canonical.values():
            ident = cap.definition.id
            if ident.namespace != identity.namespace or ident.name != identity.name:
                continue
            got = parse_semver(ident.version)
            if got[0] != want[0]:
                continue
            if got >= want:
                candidates.append(cap)
        if not candidates:
            return None
        return min(candidates, key=lambda c: parse_semver(c.definition.id.version))

    def list_all(self) -> list[BoundCapability]:
        """Deterministic listing ordered by canonical identity."""
        return [self._by_canonical[k] for k in sorted(self._by_canonical)]

    def manifests(self) -> list[CapabilityManifest]:
        return [
            CapabilityManifest.from_definition(c.definition) for c in self.list_all()
        ]

    def provenance_of(
        self, identity: CapabilityId | str
    ) -> CapabilityProvenance | None:
        key = identity if isinstance(identity, str) else identity.canonical()
        return self._provenance.get(key)

    def load_entry_points(self, group: str = ENTRY_POINT_GROUP) -> list[str]:
        loaded: list[str] = []
        for ep in entry_points().select(group=group):
            obj = ep.load()
            bound = getattr(obj, "__zeo_capability__", None)
            if isinstance(bound, BoundCapability):
                cap = bound
            elif isinstance(obj, BoundCapability):
                cap = obj
            elif callable(obj):
                cap = obj()
                nested = getattr(cap, "__zeo_capability__", None)
                if isinstance(nested, BoundCapability):
                    cap = nested
            else:
                cap = obj
            if not isinstance(cap, BoundCapability):
                raise CapabilityRegistryError(
                    f"entry point {ep.name} did not yield a BoundCapability"
                )
            self.register(
                cap,
                provenance=CapabilityProvenance(
                    source="entry_point", entry_point=ep.name
                ),
            )
            loaded.append(cap.definition.id.canonical())
        return loaded

    def clear(self) -> None:
        self._by_canonical.clear()
        self._provenance.clear()


_global_registry: CapabilityRegistry | None = None


def get_capability_registry() -> CapabilityRegistry:
    """Convenience process registry. Resettable. Not required by runners."""
    global _global_registry
    if _global_registry is None:
        _global_registry = CapabilityRegistry()
    return _global_registry


def reset_capability_registry() -> None:
    global _global_registry
    _global_registry = None
