# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/mixins/env_init.py
# module: quack_core.tools.mixins.env_init
# role: module
# neighbors: __init__.py, integration_enabled.py, lifecycle.py, output_handler.py
# exports: ToolEnvInitializerMixin
# git_branch: refactor/toolkitWorkflow
# git_commit: de0fa70
# === QV-LLM:END ===



"""
Environment validation mixin for tools.

DOCTRINE STRICT MODE:
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
    Runner creates directories; tools verify they exist and are actually directories.

    This is strict doctrine compliance:
    - Ring C (runner) creates workspace
    - Ring B (tools) validates assumptions
    """

    def _validate_directory(
            self,
            path: str,
            name: str,
            fs: Any
    ) -> CapabilityResult[None]:
        """
        Strictly validate a directory exists and is actually a directory.

        Args:
            path: Directory path to validate
            name: Human-readable name (e.g. "work", "output")
            fs: Filesystem service

        Returns:
            CapabilityResult indicating success or failure
        """
        # Check exists
        info = fs.get_file_info(path)
        if not info.success:
            return CapabilityResult.fail_from_exc(
                msg=f"Failed to check {name} directory: {info.error}",
                code=f"QC_ENV_{name.upper()}_DIR_CHECK_ERROR",
                exc=Exception(info.error)
            )

        if not info.exists:
            return CapabilityResult.fail_from_exc(
                msg=f"{name.capitalize()} directory does not exist: {path}. Runner must create it.",
                code=f"QC_ENV_{name.upper()}_DIR_MISSING",
                exc=Exception(f"{name.capitalize()} directory missing")
            )

        # Strict is_dir validation (fix #2)
        # Try to get is_dir from info result
        if hasattr(info, 'is_dir'):
            if not info.is_dir:
                return CapabilityResult.fail_from_exc(
                    msg=f"{name.capitalize()} path exists but is not a directory: {path}",
                    code=f"QC_ENV_{name.upper()}_DIR_NOT_DIR",
                    exc=Exception(f"{name.capitalize()} path is not a directory")
                )
        else:
            # Fallback: try explicit is_dir check if available
            if hasattr(fs, 'is_dir'):
                is_dir_result = fs.is_dir(path)
                if is_dir_result.success and not is_dir_result.data:
                    return CapabilityResult.fail_from_exc(
                        msg=f"{name.capitalize()} path exists but is not a directory: {path}",
                        code=f"QC_ENV_{name.upper()}_DIR_NOT_DIR",
                        exc=Exception(f"{name.capitalize()} path is not a directory")
                    )
            else:
                # FS contract incomplete - this is an error in strict mode
                return CapabilityResult.fail_from_exc(
                    msg=f"Cannot validate {name} directory type: FS service missing is_dir support",
                    code="QC_ENV_FS_CONTRACT_INCOMPLETE",
                    exc=Exception(
                        "FS info missing is_dir and fs.is_dir() not available")
                )

        return CapabilityResult.ok(data=None,
                                   msg=f"{name.capitalize()} directory validated")

    def initialize_environment(
            self,
            ctx: ToolContext
    ) -> CapabilityResult[None]:
        """
        Validate environment for tool execution (strict validation).

        The runner MUST create work_dir and output_dir.
        This method validates they exist AND are directories. Fails if missing or wrong type.

        Override this method to add custom validation logic.

        Args:
            ctx: Tool context

        Returns:
            CapabilityResult indicating success or failure
        """
        try:
            fs = ctx.require_fs()

            # Validate work_dir (strict - fix #2)
            if ctx.work_dir:
                result = self._validate_directory(ctx.work_dir, "work", fs)
                if result.status != CapabilityResult.ok().status:
                    return result

            # Validate output_dir (strict - fix #2)
            if ctx.output_dir:
                result = self._validate_directory(ctx.output_dir, "output", fs)
                if result.status != CapabilityResult.ok().status:
                    return result

            return CapabilityResult.ok(data=None, msg="Environment validated")

        except Exception as e:
            return CapabilityResult.fail_from_exc(
                msg="Environment validation failed",
                code="QC_ENV_INIT_ERROR",
                exc=e
            )