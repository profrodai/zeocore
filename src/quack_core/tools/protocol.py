# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/protocol.py
# module: quack_core.tools.protocol
# role: module
# neighbors: __init__.py, base.py, context.py
# exports: QuackToolProtocol
# git_branch: refactor/toolkitWorkflow
# git_commit: 234aec0
# === QV-LLM:END ===


"""
Protocol definition for QuackTool modules.

This module defines the interface that all QuackTool modules must implement
to be discoverable and usable within the QuackCore ecosystem.

Design principles:
- Tools return CapabilityResult (from contracts), not IntegrationResult
- Tools receive ToolContext explicitly, not via DI
- Tools do NOT handle file I/O, output writing, or manifest creation
- Tools are pure capabilities: request → CapabilityResult
"""

from typing import Protocol, Any
from logging import Logger

from quack_core.contracts import CapabilityResult
from quack_core.modules.protocols import QuackPluginMetadata

# Import ToolContext via TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quack_core.tools.context import ToolContext


class QuackToolProtocol(Protocol):
    """
    Protocol defining the required interface for QuackTool modules.

    All QuackTool modules must implement this interface to be discoverable
    and usable within the QuackCore ecosystem.

    Key methods:
    - initialize(ctx): Set up tool with given context
    - is_available(ctx): Check if tool can run
    - run(request, ctx): Execute the tool's capability

    Tools should NOT implement:
    - process_file() - File handling is runner responsibility
    - File I/O operations - Use ctx.fs if needed, but runners orchestrate
    - Output writing - Runners handle artifact persistence
    - Manifest creation - Runners build manifests from CapabilityResult
    """

    @property
    def name(self) -> str:
        """
        Returns the name of the tool.

        Convention: Use namespaced names for clarity.
        Examples: "media.transcribe", "text.summarize", "crm.sync_contacts"

        Returns:
            str: The tool's name identifier.
        """
        ...

    @property
    def version(self) -> str:
        """
        Returns the version of the tool.

        Returns:
            str: Semantic version of the tool (e.g., "1.0.0")
        """
        ...

    @property
    def logger(self) -> Logger:
        """
        Returns the logger instance for the tool.

        Note: This is for backwards compatibility. New code should
        use ctx.logger instead.

        Returns:
            Logger: Logger instance for the tool.
        """
        ...

    def get_metadata(self) -> QuackPluginMetadata:
        """
        Returns metadata about the plugin.

        Returns:
            QuackPluginMetadata: Structured metadata for the plugin.
        """
        ...

    def initialize(self, ctx: "ToolContext") -> CapabilityResult[None]:
        """
        Initialize the tool with the given context.

        This method is called once by the runner before executing the tool.
        Tools should use this to:
        - Validate required services are available
        - Set up any cached state
        - Verify configuration

        Tools should NOT:
        - Create output directories (runner's job)
        - Write files (runner's job)
        - Make network requests (unless checking availability)

        Args:
            ctx: Execution context provided by the runner

        Returns:
            CapabilityResult[None]: Success if ready, error if not available

        Example:
            >>> def initialize(self, ctx: ToolContext) -> CapabilityResult[None]:
            ...     if not ctx.fs:
            ...         return CapabilityResult.fail(
            ...             msg="Filesystem service required",
            ...             code="QC_CFG_MISSING"
            ...         )
            ...     return CapabilityResult.ok(data=None, msg="Tool ready")
        """
        ...

    def is_available(self, ctx: "ToolContext") -> bool:
        """
        Check if the tool is available and ready to use.

        This is a lightweight check that can be called frequently.
        For heavy initialization, use initialize() instead.

        Args:
            ctx: Execution context

        Returns:
            bool: True if the tool can execute, False otherwise

        Example:
            >>> def is_available(self, ctx: ToolContext) -> bool:
            ...     return ctx.fs is not None
        """
        ...

    def run(
            self,
            request: Any,  # Should be a Pydantic BaseModel in practice
            ctx: "ToolContext"
    ) -> CapabilityResult[Any]:
        """
        Execute the tool's capability.

        This is the main entrypoint for tool execution. The tool receives:
        - request: A Pydantic model with typed inputs (from contracts)
        - ctx: Execution context with services and configuration

        The tool returns a CapabilityResult containing:
        - Typed response data (from contracts)
        - Status (success/skip/error)
        - Logs and metadata

        The tool should NOT:
        - Write output files (return data, runner persists)
        - Create RunManifest (runner builds from result)
        - Handle retries (runner's responsibility)

        Args:
            request: Typed request model (e.g., TranscribeRequest)
            ctx: Execution context

        Returns:
            CapabilityResult containing typed response

        Example:
            >>> def run(
            ...     self,
            ...     request: TranscribeRequest,
            ...     ctx: ToolContext
            ... ) -> CapabilityResult[TranscribeResponse]:
            ...     # Validate input
            ...     if not request.source:
            ...         return CapabilityResult.skip(
            ...             reason="No source provided",
            ...             code="QC_VAL_NO_INPUT"
            ...         )
            ...
            ...     # Process (implementation details)
            ...     try:
            ...         result = self._transcribe_internal(request, ctx)
            ...         return CapabilityResult.ok(
            ...             data=result,
            ...             msg="Transcription completed"
            ...         )
            ...     except Exception as e:
            ...         return CapabilityResult.fail_from_exc(
            ...             msg="Transcription failed",
            ...             code="QC_PROC_ERROR",
            ...             exc=e
            ...         )
        """
        ...