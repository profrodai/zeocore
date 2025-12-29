# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/__init__.py
# module: quack_core.tools.__init__
# role: module
# neighbors: base.py, context.py, protocol.py
# exports: BaseQuackTool, BaseQuackToolPlugin, QuackToolProtocol, ToolContext, IntegrationEnabledMixin, QuackToolLifecycleMixin, ToolEnvInitializerMixin
# git_branch: refactor/toolkitWorkflow
# git_commit: 82e6d2b
# === QV-LLM:END ===



"""
Developer interface layer for creating QuackTools.

This package provides the foundation for building QuackTool modules,
following Doctrine v3 architecture principles.

What tool authors import:
- quack_core.contracts (for CapabilityResult, request/response models)
- quack_core.tools (this package - for BaseQuackTool, ToolContext, mixins)
- quack_core.integrations.* (optional - for service integrations)

What tool authors do NOT import:
- quack_runner.* (orchestration is separate)
- quack_core.workflow.* (runners handle I/O)
- Output writers, file runners, manifest builders (runner responsibilities)

Core components:
- BaseQuackTool: Base class that tools inherit from
- ToolContext: Execution context provided by runners
- QuackToolProtocol: Protocol that defines the required interface
- Mixins: Optional features (integrations, lifecycle hooks)

Example usage:
    ```python
    from quack_core.contracts import (
        CapabilityResult,
        EchoRequest,
    )
    from quack_core.tools import BaseQuackTool, ToolContext

    class EchoTool(BaseQuackTool):
        def __init__(self):
            super().__init__(
                name="demo.echo",
                version="1.0.0"
            )

        def run(
            self,
            request: EchoRequest,
            ctx: ToolContext
        ) -> CapabilityResult[str]:
            greeting = request.override_greeting or "Hello"
            result = f"{greeting} {request.text}"

            return CapabilityResult.ok(
                data=result,
                msg="Echo completed",
                metadata={"preset": request.preset}
            )
    ```

With integrations:
    ```python
    from quack_core.tools import BaseQuackTool, ToolContext
    from quack_core.tools.mixins import IntegrationEnabledMixin
    from quack_core.integrations.google.drive import GoogleDriveService
    from quack_core.contracts import CapabilityResult

    class MyTool(
        IntegrationEnabledMixin[GoogleDriveService],
        BaseQuackTool
    ):
        def initialize(self, ctx: ToolContext) -> CapabilityResult[None]:
            self._drive = self.resolve_integration(GoogleDriveService)

            if not self._drive:
                return CapabilityResult.fail(
                    msg="Google Drive integration not available",
                    code="QC_INT_UNAVAILABLE"
                )

            return CapabilityResult.ok(
                data=None,
                msg="Integration initialized"
            )

        def run(self, request, ctx: ToolContext) -> CapabilityResult:
            # Use self._drive here
            ...
    ```
"""

# Core classes
from quack_core.tools.base import BaseQuackTool, BaseQuackToolPlugin
from quack_core.tools.protocol import QuackToolProtocol
from quack_core.tools.context import ToolContext

# Mixins
from quack_core.tools.mixins.integration_enabled import IntegrationEnabledMixin
from quack_core.tools.mixins.lifecycle import QuackToolLifecycleMixin
from quack_core.tools.mixins.env_init import ToolEnvInitializerMixin

# Note: OutputFormatMixin has been removed - output handling is runner responsibility

__all__ = [
    # Core classes
    "BaseQuackTool",
    "BaseQuackToolPlugin",  # Backwards compatibility alias
    "QuackToolProtocol",
    "ToolContext",

    # Mixins
    "IntegrationEnabledMixin",
    "QuackToolLifecycleMixin",
    "ToolEnvInitializerMixin",
]

__version__ = "2.0.0"  # Major version bump - breaking changes