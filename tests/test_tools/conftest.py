# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_tools/conftest.py
# role: tests
# neighbors: __init__.py, mocks.py, test_base.py, test_imports.py (+3 more)
# exports: MockIntegrationService, AnotherMockService, tool_env_initializer_mixin,
#   lifecycle_mixin
# git_branch: feat/9-make-setup-work
# git_commit: f4879df3
# === QV-LLM:END ===

"""
Shared fixtures for QuackTool mixin tests.

NOTE: OutputFormatMixin fixtures/mocks were removed here — output_handler.py
documents its own retirement (Ring C / runner now owns output persistence;
tools return CapabilityResult). See
quack-core/src/quack_core/tools/mixins/output_handler.py's module docstring.

NOTE: the integration_enabled_mixin fixture (built around
IntegrationEnabledMixin[T].resolve_integration()) was also removed. The
current quack_core.tools.mixins.integration_enabled.IntegrationEnabledMixin
is a different, non-generic design (get_service/require_service reading
from ToolContext.services, runner-provided) with no resolve_integration or
.integration property at all -- the old fixture's pattern has no live
equivalent to fall back to here without inventing a ToolContext mock, which
is a design decision, not a rename (see this stream's SOW for the escalation).
"""

from typing import TypeVar

import pytest
from quack_core.integrations.core.base import BaseIntegrationService
from quack_core.tools.mixins.env_init import ToolEnvInitializerMixin
from quack_core.tools.mixins.lifecycle import QuackToolLifecycleMixin


class MockIntegrationService(BaseIntegrationService):
    """
    Mock implementation of BaseIntegrationService for testing.
    """

    @property
    def name(self) -> str:
        return "mock_service"

    def __init__(self) -> None:
        super().__init__()
        self.initialized = False

    def initialize(self) -> None:
        self.initialized = True


class AnotherMockService(BaseIntegrationService):
    """
    Another mock implementation of BaseIntegrationService for testing.
    """

    @property
    def name(self) -> str:
        return "another_service"


T = TypeVar("T", bound=BaseIntegrationService)


@pytest.fixture
def tool_env_initializer_mixin() -> ToolEnvInitializerMixin:
    """Fixture that creates a ToolEnvInitializerMixin."""
    return ToolEnvInitializerMixin()


@pytest.fixture
def lifecycle_mixin() -> QuackToolLifecycleMixin:
    """Fixture that creates a QuackToolLifecycleMixin."""
    return QuackToolLifecycleMixin()
