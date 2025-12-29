"""
Explicit loader for QuackCore integrations.

This module handles discovering entry points, filtering them against an allow-list,
instantiating the integration factories, initializing them, and registering them
into a registry. It ensures no side effects occur unless explicitly requested.
"""

import logging
from importlib.metadata import entry_points
from typing import Any

from quack_core.integrations.core.protocols import IntegrationProtocol
from quack_core.integrations.core.registry import IntegrationRegistry
from quack_core.integrations.core.results import IntegrationLoadReport

logger = logging.getLogger(__name__)

DEFAULT_ENTRY_GROUP = "quack_core.integrations"


def list_available_entry_points(group: str = DEFAULT_ENTRY_GROUP) -> list[
    dict[str, str]]:
    """
    List available integration entry points without loading them.

    Args:
        group: The entry point group to search.

    Returns:
        list[dict]: Metadata about available integrations containing
                    'integration_id', 'value', and 'module'.
    """
    results = []
    # Python 3.10+ style entry_points selection
    eps = entry_points(group=group)
    for ep in eps:
        results.append({
            "integration_id": ep.name,
            "value": ep.value,
            "module": ep.module,
        })
    return results


def load_enabled_entry_points(
        registry: IntegrationRegistry,
        enabled: list[str],
        group: str = DEFAULT_ENTRY_GROUP,
        strict: bool = True,
        initialize: bool = True
) -> IntegrationLoadReport:
    """
    Load specific integrations by ID from entry points.

    Args:
        registry: The registry to populate.
        enabled: List of integration_ids to load. Order is preserved.
        group: Entry point group.
        strict: If True, fails if a requested integration is missing.
        initialize: If True, calls .initialize() on the integration instance.

    Returns:
        IntegrationLoadReport: Detailed report of what happened.
    """
    report = IntegrationLoadReport(success=True)

    # Get all available entry points map: name -> EntryPoint
    eps = entry_points(group=group)
    ep_map = {ep.name: ep for ep in eps}

    for integration_id in enabled:
        if integration_id not in ep_map:
            msg = f"Integration '{integration_id}' not found in entry points."
            if strict:
                report.errors.append(msg)
                report.success = False
                logger.error(msg)
                # In strict mode, fail immediately on missing requirements
                return report
            else:
                report.warnings.append(msg)
                report.skipped.append(integration_id)
                logger.warning(msg)
                continue

        # Load the integration
        entry_point = ep_map[integration_id]
        try:
            logger.debug(f"Loading integration: {integration_id}")
            factory = entry_point.load()

            if not callable(factory):
                error_msg = f"Entry point {integration_id} is not callable."
                report.errors.append(error_msg)
                report.success = False
                continue

            instance = factory()

            if not isinstance(instance, IntegrationProtocol):
                # Duck-typing check if isinstance fails due to import quirks
                if not (hasattr(instance, "initialize") and hasattr(instance, "name")):
                    error_msg = f"Instance for {integration_id} does not satisfy IntegrationProtocol."
                    report.errors.append(error_msg)
                    report.success = False
                    continue

            # Initialize if requested
            if initialize:
                init_result = instance.initialize()
                if not init_result.success:
                    error_msg = f"Failed to initialize {integration_id}: {init_result.error}"
                    report.errors.append(error_msg)
                    # If initialization fails, we generally consider the load failed
                    report.success = False
                    continue

            # Register
            registry.register(instance)
            report.loaded.append(integration_id)

        except Exception as e:
            error_msg = f"Unexpected error loading {integration_id}: {str(e)}"
            report.errors.append(error_msg)
            report.success = False
            logger.exception(error_msg)

    return report