# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/boot.py
# module: quack_core.integrations.boot
# role: module
# neighbors: __init__.py, config.py, loader.py
# exports: get_global_registry, load_integrations
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

"""
Boot API for QuackCore integrations.

This is the public entry point for applications (like QuackChat or CLI)
to explicitly load runtime dependencies. It manages a global registry instance
for convenience but allows for dependency injection.
"""


from quack_core.integrations.core.registry import IntegrationRegistry
from quack_core.integrations.core.results import IntegrationLoadReport
from quack_core.integrations.loader import load_enabled_entry_points

# Global default registry (convenience for simple apps)
_global_registry = IntegrationRegistry()


def get_global_registry() -> IntegrationRegistry:
    """
    Get the global integration registry.

    Returns:
        IntegrationRegistry: The global singleton registry.
    """
    return _global_registry


def load_integrations(
        enabled: list[str],
        registry: IntegrationRegistry | None = None,
        strict: bool = True,
        initialize: bool = True
) -> IntegrationLoadReport:
    """
    Boot specific integrations.

    Args:
        enabled: List of integration IDs (e.g. ['github', 'llms', 'google.mail'])
        registry: Optional registry instance. Defaults to global.
        strict: Whether to fail if an integration is missing.
        initialize: Whether to run .initialize() on loaded integrations.

    Returns:
        IntegrationLoadReport: Result of the load operation.
    """
    target_registry = registry or _global_registry

    return load_enabled_entry_points(
        registry=target_registry,
        enabled=enabled,
        strict=strict,
        initialize=initialize
    )
