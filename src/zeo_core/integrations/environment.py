"""Explicit process environment identity shared by integration implementations.

This module has no provider imports, environment mutation or startup I/O.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, cast

IntegrationMode = Literal["test", "production"]
IntegrationBackend = Literal["live", "fixture"]


def integration_mode() -> IntegrationMode | None:
    value = os.environ.get("ZEO_INTEGRATION_MODE")
    if value is None:
        if os.environ.get("ZEO_INTEGRATION_STATE_DIR") or os.environ.get(
            "ZEO_INTEGRATION_BACKEND"
        ):
            raise ValueError(
                "Incomplete integration environment; use the environment launcher"
            )
        return None
    if value not in {"test", "production"}:
        raise ValueError("Integration mode must be test or production")
    return cast(IntegrationMode, value)


def integration_backend() -> IntegrationBackend:
    mode = integration_mode()
    value = os.environ.get("ZEO_INTEGRATION_BACKEND", "live")
    if value not in {"live", "fixture"} or (value == "fixture" and mode != "test"):
        raise ValueError("Fixture execution requires test mode")
    return cast(IntegrationBackend, value)


def managed_state_dir() -> Path | None:
    mode = integration_mode()
    if mode is None:
        return None
    integration_backend()
    value = os.environ.get("ZEO_INTEGRATION_STATE_DIR", "")
    path = Path(value)
    if (
        not value
        or not path.is_absolute()
        or path.name != mode
        or path.resolve() != path
    ):
        raise ValueError(
            "Integration state directory must be the resolved selected mode directory"
        )
    return path


def managed_path(value: str) -> str:
    """Reject credential/config paths outside the selected mode, including symlinks."""
    state = managed_state_dir()
    if state is None:
        return value
    path = Path(value).expanduser().resolve()
    if not path.is_relative_to(state):
        raise ValueError(
            "Credential and config paths must stay inside "
            "the selected integration environment"
        )
    return str(path)
