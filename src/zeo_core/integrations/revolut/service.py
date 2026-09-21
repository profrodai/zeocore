"""Explicit integration loading; initialization does not claim live authentication."""

from __future__ import annotations

import os

from zeo_core.integrations.core import IntegrationResult

from .models import RevolutEnvironment


class RevolutBusinessIntegration:
    integration_id = "revolut.business"
    name = "Revolut Business"
    version = "1.0.0"

    def __init__(self) -> None:
        self._enrollment: object | None = None

    @property
    def enrollment(self) -> object:
        if self._enrollment is None:
            raise ValueError("Revolut Business integration is not initialized")
        return self._enrollment

    def initialize(self) -> IntegrationResult[object]:
        """Select the LOCAL profile. Configuration only; no secret is read here."""

        value = os.environ.get("REVOLUT_ENVIRONMENT", "")
        if value not in {item.value for item in RevolutEnvironment}:
            return IntegrationResult.error_result(
                "Set REVOLUT_ENVIRONMENT to sandbox or production"
            )
        try:
            from .local import LocalRevolutEnrollment
        except ImportError:
            return IntegrationResult.error_result(
                'Install the local profile with: pip install "zeocore[revolut]"'
            )
        enrollment = LocalRevolutEnrollment(RevolutEnvironment(value))
        state = enrollment.status()
        if state is None or state.refresh_token is None:
            return IntegrationResult.error_result(
                "Not enrolled; run python -m zeo_core.integrations.revolut.local setup"
            )
        self._enrollment = enrollment
        return IntegrationResult.success_result(
            message="Local Revolut enrollment found; live access is unverified"
        )

    def is_available(self) -> bool:
        return self._enrollment is not None


def create_integration() -> RevolutBusinessIntegration:
    return RevolutBusinessIntegration()
