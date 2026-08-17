"""
Tests for tools imports.

This module tests that all expected imports from the tools
package are available and functioning correctly.

NOTE: OutputFormatMixin / BaseZeoToolPlugin-as-a-combinable-mixin-base and
ZeoToolPluginProtocol references were removed. output_handler.py documents
its own retirement (tools return CapabilityResult, runners persist output);
zeo_core.tools.protocol now defines ZeoToolProtocol (not
ZeoToolPluginProtocol); zeo_core.tools.base.BaseZeoTool has a
different, simpler shape (run(request, ctx) -> CapabilityResult) than the
old BaseZeoToolPlugin this test previously exercised. IntegrationEnabledMixin
is also a different, non-generic design now (get_service/require_service off
ToolContext.services) with no resolve_integration method -- see conftest.py's
NOTE for the same finding.
"""

import unittest
from types import ModuleType

# Import the main package
import zeo_core.tools

# Import components directly to avoid circular imports
from zeo_core.tools.protocol import ZeoToolProtocol


class TestToolkitImports(unittest.TestCase):
    """
    Test cases for tools imports.
    """

    def test_base_imports(self) -> None:
        """
        Test that all expected classes and modules are imported.
        """
        # Check that the BaseZeoTool class is available
        self.assertTrue(hasattr(zeo_core.tools, "BaseZeoTool"))
        self.assertTrue(callable(zeo_core.tools.BaseZeoTool))

        # Check that the protocol is available
        self.assertTrue(hasattr(zeo_core.tools, "ZeoToolProtocol"))

        # Check that all mixins are available
        self.assertTrue(hasattr(zeo_core.tools, "IntegrationEnabledMixin"))
        self.assertTrue(hasattr(zeo_core.tools, "ToolEnvInitializerMixin"))
        self.assertTrue(hasattr(zeo_core.tools, "ZeoToolLifecycleMixin"))


class TestToolkitImportsPytest:
    """
    Pytest-style tests for tools imports.
    """

    def test_module_attributes(self) -> None:
        """Test that the tools module has the expected attributes."""
        assert hasattr(zeo_core.tools, "__all__")
        assert isinstance(zeo_core.tools.__all__, list)

        # Check that all items in __all__ are actually in the module
        for item in zeo_core.tools.__all__:
            assert hasattr(zeo_core.tools, item)

    def test_importing_protocol(self) -> None:
        """Test importing the protocol directly."""
        # Protocol is already imported at the top
        assert callable(ZeoToolProtocol.__call__)

    def test_importing_base(self) -> None:
        """Test importing the base module directly."""
        import zeo_core.tools.base as base

        assert isinstance(base, ModuleType)
        assert hasattr(base, "BaseZeoTool")

    def test_importing_mixins(self) -> None:
        """Test importing the mixins directly."""
        import zeo_core.tools.mixins as mixins

        assert isinstance(mixins, ModuleType)

        # Import from individual modules
        from zeo_core.tools.mixins import (
            IntegrationEnabledMixin,
            ToolEnvInitializerMixin,
        )
        from zeo_core.tools.mixins.lifecycle import ZeoToolLifecycleMixin

        # Test functionality of imported mixins
        assert callable(ToolEnvInitializerMixin.initialize_environment)
        assert callable(IntegrationEnabledMixin.get_service)
        assert callable(ZeoToolLifecycleMixin.pre_run)


if __name__ == "__main__":
    unittest.main()
