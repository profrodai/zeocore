# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/core/base/test_base.py
# role: tests
# neighbors: __init__.py, auth_provider_impl.py, config_provider_impl.py, integration_service_impl.py, test_auth_provider.py, test_config_provider.py (+3 more)
# exports: TestBaseAuthProvider, TestBaseConfigProvider, TestBaseConfigProviderDiscovery, TestBaseIntegrationService
# git_branch: refactor/newHeaders
# git_commit: 72778e2
# === QV-LLM:END ===

"""
Main entry point for base integration tests.

This file imports all the specific test modules to ensure they are discovered
by pytest when running the test suite.
"""

from .test_auth_provider import (
    TestBaseAuthProvider,
)
from .test_config_provider import (
    TestBaseConfigProvider,
)
from .test_config_provider_discovery import (
    TestBaseConfigProviderDiscovery,
)

# Import test modules to ensure they are discovered by pytest
from .test_integration_service import (
    TestBaseIntegrationService,
)

# Export the test classes for direct import
__all__ = [
    "TestBaseAuthProvider",
    "TestBaseConfigProvider",
    "TestBaseConfigProviderDiscovery",
    "TestBaseIntegrationService",
]
