# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_tools/test_imports.py
# === QV-LLM:END ===

"""
Tests for tools imports.

This module tests that all expected imports from the tools
package are available and functioning correctly.

NOTE: OutputFormatMixin / BaseQuackToolPlugin-as-a-combinable-mixin-base and
QuackToolPluginProtocol references were removed. output_handler.py documents
its own retirement (tools return CapabilityResult, runners persist output);
quack_core.tools.protocol now defines QuackToolProtocol (not
QuackToolPluginProtocol); quack_core.tools.base.BaseQuackTool has a
different, simpler shape (run(request, ctx) -> CapabilityResult) than the
old BaseQuackToolPlugin this test previously exercised. IntegrationEnabledMixin
is also a different, non-generic design now (get_service/require_service off
ToolContext.services) with no resolve_integration method -- see conftest.py's
NOTE for the same finding.
"""

import unittest
from types import ModuleType

# Import the main package
import quack_core.tools

# Import components directly to avoid circular imports
from quack_core.tools.protocol import QuackToolProtocol


class TestToolkitImports(unittest.TestCase):
    """
    Test cases for tools imports.
    """

    def test_base_imports(self) -> None:
        """
        Test that all expected classes and modules are imported.
        """
        # Check that the BaseQuackTool class is available
        self.assertTrue(hasattr(quack_core.tools, "BaseQuackTool"))
        self.assertTrue(callable(quack_core.tools.BaseQuackTool))

        # Check that the protocol is available
        self.assertTrue(hasattr(quack_core.tools, "QuackToolProtocol"))

        # Check that all mixins are available
        self.assertTrue(hasattr(quack_core.tools, "IntegrationEnabledMixin"))
        self.assertTrue(hasattr(quack_core.tools, "ToolEnvInitializerMixin"))
        self.assertTrue(hasattr(quack_core.tools, "QuackToolLifecycleMixin"))


class TestToolkitImportsPytest:
    """
    Pytest-style tests for tools imports.
    """

    def test_module_attributes(self) -> None:
        """Test that the tools module has the expected attributes."""
        assert hasattr(quack_core.tools, "__all__")
        assert isinstance(quack_core.tools.__all__, list)

        # Check that all items in __all__ are actually in the module
        for item in quack_core.tools.__all__:
            assert hasattr(quack_core.tools, item)

    def test_importing_protocol(self) -> None:
        """Test importing the protocol directly."""
        # Protocol is already imported at the top
        assert callable(QuackToolProtocol.__call__)

    def test_importing_base(self) -> None:
        """Test importing the base module directly."""
        import quack_core.tools.base as base

        assert isinstance(base, ModuleType)
        assert hasattr(base, "BaseQuackTool")

    def test_importing_mixins(self) -> None:
        """Test importing the mixins directly."""
        import quack_core.tools.mixins as mixins

        assert isinstance(mixins, ModuleType)

        # Import from individual modules
        from quack_core.tools.mixins import (
            IntegrationEnabledMixin,
            ToolEnvInitializerMixin,
        )
        from quack_core.tools.mixins.lifecycle import QuackToolLifecycleMixin

        # Test functionality of imported mixins
        assert callable(ToolEnvInitializerMixin.initialize_environment)
        assert callable(IntegrationEnabledMixin.get_service)
        assert callable(QuackToolLifecycleMixin.pre_run)


if __name__ == "__main__":
    unittest.main()
