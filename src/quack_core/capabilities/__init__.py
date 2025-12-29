# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/capabilities/__init__.py
# module: quack_core.capabilities.__init__
# role: module
# neighbors: base.py, protocol.py
# exports: BaseQuackToolPlugin, QuackToolPluginProtocol, IntegrationEnabledMixin, OutputFormatMixin, ToolEnvInitializerMixin, QuackToolLifecycleMixin
# git_branch: refactor/toolkitWorkflow
# git_commit: 66ff061
# === QV-LLM:END ===

"""
Developer interface layer for creating QuackTools.

This package provides the foundation for building QuackTool modules,
including the base class, protocol, and mixins that add optional features.

# Core components
- BaseQuackToolPlugin: Base class that tools can inherit from
- QuackToolPluginProtocol: Protocol that defines the required interface
- Various mixins that add optional features

# Example usage
```python
from quack_core.capabilities import BaseQuackToolPlugin, IntegrationEnabledMixin
from quack_core.integrations.google.drive import GoogleDriveService

class MyTool(IntegrationEnabledMixin[GoogleDriveService], BaseQuackToolPlugin):
    def _initialize_plugin(self):
        self._drive = self.resolve_integration(GoogleDriveService)

    def process_content(self, content, options):
        # Process content here
        return {"result": "processed content"}
```
"""

# First import the protocol
# Then import base which depends on the protocol
from .base import BaseQuackToolPlugin

# Import the mixins which don't have circular dependencies
from .mixins.env_init import ToolEnvInitializerMixin
from .mixins.integration_enabled import IntegrationEnabledMixin
from .mixins.lifecycle import QuackToolLifecycleMixin
from .mixins.output_handler import OutputFormatMixin
from .protocol import QuackToolPluginProtocol

__all__ = [
    "BaseQuackToolPlugin",
    "QuackToolPluginProtocol",
    "IntegrationEnabledMixin",
    "OutputFormatMixin",
    "ToolEnvInitializerMixin",
    "QuackToolLifecycleMixin",
]
