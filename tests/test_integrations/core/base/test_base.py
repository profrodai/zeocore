# quack-core/tests/test_integrations/core/base/test_base.py
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
