# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/base.py
# module: quack_core.tools.base
# role: module
# neighbors: __init__.py, context.py, protocol.py
# exports: BaseQuackTool
# git_branch: refactor/toolkitWorkflow
# git_commit: 82e6d2b
# === QV-LLM:END ===


"""
Base class implementation for QuackTool modules.

This module provides the foundational class that all QuackTool modules
should inherit from, implementing common functionality and enforcing
the QuackToolProtocol.

Design principles (Doctrine v3):
- Tools are pure capabilities (request → CapabilityResult)
- Tools receive ToolContext explicitly (no DI magic)
- Tools do NOT handle file I/O, output writing, or manifest creation
- Tools are agnostic to runner implementation (CLI, n8n, Temporal)

What was REMOVED from BaseQuackToolPlugin:
- process_file() - Now in runner
- Filesystem initialization - Now in ToolContext
- Output directory creation - Now in runner
- Temp directory creation - Now in runner/context
- Output writer handling - Now in runner
- FileWorkflowRunner import - Now in runner
- IntegrationResult - Now using CapabilityResult from contracts
"""

import abc
from logging import Logger
from typing import Any

from quack_core.contracts import CapabilityResult
from quack_core.modules.protocols import QuackPluginMetadata
from quack_core.tools.protocol import QuackToolProtocol
from quack_core.tools.context import ToolContext


class BaseQuackTool(QuackToolProtocol, abc.ABC):
    """
    Base class for all QuackTool modules.

    Provides minimal common functionality and enforces the required interface
    for all QuackTool modules. Concrete tool implementations should
    inherit from this class and implement the abstract methods.

    What tools inherit:
    - name, version properties (set in __init__)
    - logger property (for backwards compat)
    - get_metadata() implementation
    - Default initialize() implementation
    - Default is_available() implementation

    What tools MUST implement:
    - run(request, ctx) -> CapabilityResult

    Example tool implementation:
        ```python
        from quack_core.contracts import (
            CapabilityResult,
            TranscribeRequest,
            TranscribeResponse
        )
        from quack_core.tools import BaseQuackTool, ToolContext

        class TranscribeTool(BaseQuackTool):
            def __init__(self):
                super().__init__(
                    name="media.transcribe",
                    version="1.0.0"
                )

            def run(
                self,
                request: TranscribeRequest,
                ctx: ToolContext
            ) -> CapabilityResult[TranscribeResponse]:
                # Validate
                if not request.source:
                    return CapabilityResult.skip(
                        reason="No source provided",
                        code="QC_VAL_NO_INPUT"
                    )

                # Process
                try:
                    result = self._transcribe(request, ctx)
                    return CapabilityResult.ok(
                        data=result,
                        msg="Transcription completed"
                    )
                except Exception as e:
                    return CapabilityResult.fail_from_exc(
                        msg="Transcription failed",
                        code="QC_PROC_ERROR",
                        exc=e
                    )
        ```
    """

    def __init__(self, name: str, version: str):
        """
        Initialize the base QuackTool.

        Args:
            name: The name of the tool (use namespaced format like "media.transcribe")
            version: The semantic version of the tool (e.g., "1.0.0")
        """
        self._name = name
        self._version = version
        self._logger: Logger | None = None

    @property
    def name(self) -> str:
        """
        Returns the name of the tool.

        Returns:
            str: The tool's name identifier.
        """
        return self._name

    @property
    def version(self) -> str:
        """
        Returns the version of the tool.

        Returns:
            str: Semantic version of the tool.
        """
        return self._version

    @property
    def logger(self) -> Logger:
        """
        Returns the logger instance for the tool.

        Note: This is for backwards compatibility. New code should
        use ctx.logger from ToolContext instead.

        Returns:
            Logger: Logger instance for the tool.
        """
        if self._logger is None:
            import logging
            self._logger = logging.getLogger(self._name)
        return self._logger

    def get_metadata(self) -> QuackPluginMetadata:
        """
        Returns metadata about the plugin.

        Returns:
            QuackPluginMetadata: Structured metadata for the plugin.
        """
        return QuackPluginMetadata(
            name=self.name,
            version=self.version,
            description=self.__doc__ or "",
        )

    def initialize(self, ctx: ToolContext) -> CapabilityResult[None]:
        """
        Initialize the tool with the given context.

        Default implementation checks basic availability and returns success.
        Override this method to perform custom initialization.

        Args:
            ctx: Execution context provided by the runner

        Returns:
            CapabilityResult[None]: Success if ready, error if not available
        """
        if not self.is_available(ctx):
            return CapabilityResult.fail(
                msg=f"Tool {self.name} is not available",
                code="QC_TOOL_UNAVAILABLE"
            )

        return CapabilityResult.ok(
            data=None,
            msg=f"Successfully initialized {self.name} v{self.version}"
        )

    def is_available(self, ctx: ToolContext) -> bool:
        """
        Check if the tool is available and ready to use.

        Default implementation always returns True.
        Override this method to perform custom availability checks.

        Args:
            ctx: Execution context

        Returns:
            bool: True if the tool can execute, False otherwise
        """
        return True

    @abc.abstractmethod
    def run(
            self,
            request: Any,
            ctx: ToolContext
    ) -> CapabilityResult[Any]:
        """
        Execute the tool's capability.

        This is the main entrypoint that concrete tools must implement.

        Args:
            request: Typed request model (Pydantic BaseModel)
            ctx: Execution context with services and configuration

        Returns:
            CapabilityResult containing typed response data

        Example:
            >>> def run(
            ...     self,
            ...     request: EchoRequest,
            ...     ctx: ToolContext
            ... ) -> CapabilityResult[str]:
            ...     greeting = request.override_greeting or "Hello"
            ...     result = f"{greeting} {request.text}"
            ...     return CapabilityResult.ok(
            ...         data=result,
            ...         msg="Echo completed"
            ...     )
        """
        pass


# Backwards compatibility alias
# TODO: Remove in next major version
BaseQuackToolPlugin = BaseQuackTool