# quack-core/tests/test_integrations/core/base/auth_provider_impl.py
"""
Implementation classes for testing auth providers.
"""

import os

from quack_core.integrations.core.base import BaseAuthProvider
from quack_core.integrations.core.results import AuthResult


class MockAuthProvider(BaseAuthProvider):
    """Mock implementation of BaseAuthProvider for testing."""

    @property
    def name(self) -> str:
        return "test_auth"

    def authenticate(self) -> AuthResult:
        if self.credentials_file and not os.path.exists(self.credentials_file):
            return AuthResult.error_result("Credentials file not found")
        self.authenticated = True
        return AuthResult.success_result(message="Authentication succeeded")

    def refresh_credentials(self) -> AuthResult:
        if not self.authenticated:
            return AuthResult.error_result("Not authenticated")
        return AuthResult.success_result(message="Credentials refreshed")

    def get_credentials(self) -> object:
        if not self.authenticated:
            self.authenticate()
        return {"credentials": "test"}

    def save_credentials(self) -> bool:
        return self._ensure_credentials_directory()
