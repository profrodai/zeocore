

"""
Lifecycle mixin for QuackTool modules.

This module provides a mixin that adds lifecycle hooks to QuackTool modules,
such as pre_run, post_run, validate, and upload.

Changes from original:
- Returns CapabilityResult instead of IntegrationResult
- Hooks receive ToolContext for consistency
- No orchestration logic (kept as pure hooks)
"""

from typing import Any, TYPE_CHECKING

from quack_core.contracts import CapabilityResult

if TYPE_CHECKING:
    from quack_core.tools.context import ToolContext


class QuackToolLifecycleMixin:
    """
    Mixin that provides lifecycle hooks for QuackTool modules.

    This mixin adds optional lifecycle methods that tools can override
    to provide custom behavior at different stages of execution.

    All hooks return CapabilityResult to enable consistent error handling
    and status tracking.

    Example:
        ```python
        from quack_core.tools import BaseQuackTool, ToolContext
        from quack_core.tools.mixins import QuackToolLifecycleMixin
        from quack_core.contracts import CapabilityResult

        class MyTool(QuackToolLifecycleMixin, BaseQuackTool):
            def pre_run(self, ctx: ToolContext) -> CapabilityResult[None]:
                # Check prerequisites
                if not ctx.work_dir:
                    return CapabilityResult.fail(
                        msg="Work directory required",
                        code="QC_CFG_MISSING"
                    )
                return CapabilityResult.ok(data=None, msg="Pre-run checks passed")

            def run(self, request, ctx: ToolContext) -> CapabilityResult:
                # Main execution
                ...

            def post_run(self, ctx: ToolContext) -> CapabilityResult[None]:
                # Cleanup
                ctx.logger.info("Cleaning up temporary files")
                return CapabilityResult.ok(data=None, msg="Cleanup completed")
        ```
    """

    def pre_run(self, ctx: "ToolContext") -> CapabilityResult[None]:
        """
        Prepare before running the tool.

        This hook is called before the tool's run() method. Override this
        to perform any preparation tasks such as checking prerequisites.

        Args:
            ctx: Execution context

        Returns:
            CapabilityResult[None]: Success if ready, error if prerequisites not met

        Example:
            >>> def pre_run(self, ctx: ToolContext) -> CapabilityResult[None]:
            ...     if not ctx.fs:
            ...         return CapabilityResult.fail(
            ...             msg="Filesystem service required",
            ...             code="QC_CFG_MISSING"
            ...         )
            ...     return CapabilityResult.ok(data=None, msg="Ready")
        """
        return CapabilityResult.ok(
            data=None,
            msg="Pre-run completed successfully"
        )

    def post_run(self, ctx: "ToolContext") -> CapabilityResult[None]:
        """
        Clean up or finalize after running the tool.

        This hook is called after the tool's run() method. Override this
        to perform any clean-up or finalization tasks.

        Args:
            ctx: Execution context

        Returns:
            CapabilityResult[None]: Success if cleanup succeeded

        Example:
            >>> def post_run(self, ctx: ToolContext) -> CapabilityResult[None]:
            ...     # Clean up temporary files
            ...     if ctx.work_dir:
            ...         ctx.fs.remove_directory(ctx.work_dir)
            ...     return CapabilityResult.ok(data=None, msg="Cleanup done")
        """
        return CapabilityResult.ok(
            data=None,
            msg="Post-run completed successfully"
        )

    def validate(
            self,
            ctx: "ToolContext",
            input_path: str | None = None,
            output_path: str | None = None
    ) -> CapabilityResult[None]:
        """
        Validate input and/or output files.

        This hook allows tools to validate files before or after processing.
        Override this method to provide custom validation logic.

        Args:
            ctx: Execution context
            input_path: Optional path to the input file to validate
            output_path: Optional path to the output file to validate

        Returns:
            CapabilityResult[None]: Success if validation passed

        Example:
            >>> def validate(
            ...     self,
            ...     ctx: ToolContext,
            ...     input_path: str | None = None,
            ...     output_path: str | None = None
            ... ) -> CapabilityResult[None]:
            ...     if input_path and not ctx.fs.exists(input_path):
            ...         return CapabilityResult.fail(
            ...             msg=f"Input file not found: {input_path}",
            ...             code="QC_IO_NOT_FOUND"
            ...         )
            ...     return CapabilityResult.ok(data=None, msg="Validation passed")
        """
        return CapabilityResult.ok(
            data=None,
            msg="Validation method not implemented"
        )

    def upload(
            self,
            ctx: "ToolContext",
            file_path: str,
            destination: str | None = None
    ) -> CapabilityResult[dict[str, Any]]:
        """
        Upload a file to a destination.

        This hook provides a standard interface for file uploads.
        Override this method to provide custom upload logic.

        Note: Actual upload implementation should use integration services
        resolved via IntegrationEnabledMixin.

        Args:
            ctx: Execution context
            file_path: Path to the file to upload
            destination: Optional destination path or identifier

        Returns:
            CapabilityResult containing upload metadata (URL, ID, etc.)

        Example:
            >>> def upload(
            ...     self,
            ...     ctx: ToolContext,
            ...     file_path: str,
            ...     destination: str | None = None
            ... ) -> CapabilityResult[dict[str, Any]]:
            ...     if not self._upload_service:
            ...         return CapabilityResult.fail(
            ...             msg="Upload service not available",
            ...             code="QC_INT_UNAVAILABLE"
            ...         )
            ...
            ...     result = self._upload_service.upload(file_path, destination)
            ...     return CapabilityResult.ok(
            ...         data={"url": result.url, "id": result.file_id},
            ...         msg="Upload completed"
            ...     )
        """
        return CapabilityResult.ok(
            data={},
            msg="Upload method not implemented"
        )