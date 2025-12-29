
"""
Environment validation mixin for tools.

DOCTRINE STRICT MODE (fix #3):
This mixin VALIDATES existence only. It does NOT create directories.
Runner creates all directories. Tools fail if they don't exist.

This enforces clear responsibility:
- Runner: creates ctx.work_dir and ctx.output_dir
- Tools: validate they exist (fail fast if runner didn't set up correctly)

Tools writing artifacts still go through runner's output mechanisms.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from quack_core.contracts import CapabilityResult

if TYPE_CHECKING:
    from quack_core.tools.context import ToolContext


class ToolEnvInitializerMixin:
    """
    Mixin for tools that need environment validation.

    IMPORTANT: This VALIDATES only. It does NOT create directories.
    Runner creates directories; tools verify they exist.

    This is strict doctrine compliance:
    - Ring C (runner) creates workspace
    - Ring B (tools) validates assumptions
    """

    def initialize_environment(
            self,
            ctx: ToolContext
    ) -> CapabilityResult[None]:
        """
        Validate environment for tool execution (strict validation).

        The runner MUST create work_dir and output_dir.
        This method validates they exist. Fails if missing.

        Override this method to add custom validation logic.

        Args:
            ctx: Tool context

        Returns:
            CapabilityResult indicating success or failure
        """
        try:
            fs = ctx.require_fs()

            # Validate work_dir exists (runner must have created it)
            if ctx.work_dir:
                work_info = fs.get_file_info(ctx.work_dir)
                if not work_info.success:
                    return CapabilityResult.fail_from_exc(
                        msg=f"Failed to check work directory: {work_info.error}",
                        code="QC_ENV_WORK_DIR_CHECK_ERROR",
                        exc=Exception(work_info.error)
                    )
                if not work_info.exists:
                    return CapabilityResult.fail_from_exc(
                        msg=f"Work directory does not exist: {ctx.work_dir}. Runner must create it.",
                        code="QC_ENV_WORK_DIR_MISSING",
                        exc=Exception("Work directory missing")
                    )

            # Validate output_dir exists (runner must have created it)
            if ctx.output_dir:
                output_info = fs.get_file_info(ctx.output_dir)
                if not output_info.success:
                    return CapabilityResult.fail_from_exc(
                        msg=f"Failed to check output directory: {output_info.error}",
                        code="QC_ENV_OUTPUT_DIR_CHECK_ERROR",
                        exc=Exception(output_info.error)
                    )
                if not output_info.exists:
                    return CapabilityResult.fail_from_exc(
                        msg=f"Output directory does not exist: {ctx.output_dir}. Runner must create it.",
                        code="QC_ENV_OUTPUT_DIR_MISSING",
                        exc=Exception("Output directory missing")
                    )

            return CapabilityResult.ok(msg="Environment validated")

        except Exception as e:
            return CapabilityResult.fail_from_exc(
                msg="Environment validation failed",
                code="QC_ENV_INIT_ERROR",
                exc=e
            )