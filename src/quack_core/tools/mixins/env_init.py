# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/mixins/env_init.py
# module: quack_core.tools.mixins.env_init
# role: module
# neighbors: __init__.py, integration_enabled.py, lifecycle.py, output_handler.py
# exports: ToolEnvInitializerMixin
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===



"""
Environment validation mixin for tools.

DOCTRINE STRICT MODE:
This mixin VALIDATES existence only. It does NOT create directories.
Runner creates all directories. Tools fail if they don't exist.

USAGE PATTERN:
Tools that inherit this mixin should call initialize_environment() from their
initialize() or validate() hook:

    class MyTool(BaseQuackTool, ToolEnvInitializerMixin):
        def initialize(self, ctx: ToolContext) -> CapabilityResult[None]:
            # Validate environment
            env_result = self.initialize_environment(ctx)
            if env_result.status != CapabilityStatus.success:
                return env_result

            # Continue with tool-specific initialization
            return CapabilityResult.ok(data=None, msg="Initialized")

This enforces clear responsibility:
- Runner: creates ctx.work_dir and ctx.output_dir
- Tools: validate they exist (fail fast if runner didn't set up correctly)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quack_core.contracts import CapabilityResult, CapabilityStatus

if TYPE_CHECKING:
    from quack_core.tools.context import ToolContext


class ToolEnvInitializerMixin:
    """
    Mixin for tools that need environment validation.

    IMPORTANT: This VALIDATES only. It does NOT create directories.

    USAGE: Tools must explicitly call initialize_environment() from initialize() or validate().

    FS CONTRACT (fix #3 - with normalization for drift):
    Expects fs.get_file_info(path) to return result with success/data/error.
    Normalizes both .success/.ok and common field name variations.
    """

    @staticmethod
    def _normalize_fs_result(result: Any) -> tuple[bool, Any, str | None]:
        """
        Normalize FS result to common pattern (fix #3 - handle drift).

        Returns:
            (success, data, error) tuple
        """
        # Try .success first, fall back to .ok
        success = getattr(result, 'success', None)
        if success is None:
            success = getattr(result, 'ok', False)

        # Try .data first, fall back to .value
        data = getattr(result, 'data', None)
        if data is None:
            data = getattr(result, 'value', None)

        # Try .error
        error = getattr(result, 'error', None)

        return bool(success), data, error

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
        # Check file info exists (fix #3 - use normalization)
        info_result = fs.get_file_info(path)
        success, info, error = self._normalize_fs_result(info_result)

        if not success:
            return CapabilityResult.fail_from_exc(
                msg=f"Failed to check {name} directory: {error}",
                code=f"QC_ENV_{name.upper()}_DIR_CHECK_ERROR",
                exc=Exception(error or "Unknown error")
            )

        if info is None:
            return CapabilityResult.fail_from_exc(
                msg=f"FS returned no info for {name} directory: {path}",
                code=f"QC_ENV_{name.upper()}_DIR_NO_INFO",
                exc=Exception("FileInfo data is None")
            )

        # Check exists
        if not info.exists:
            return CapabilityResult.fail_from_exc(
                msg=f"{name.capitalize()} directory does not exist: {path}. Runner must create it.",
                code=f"QC_ENV_{name.upper()}_DIR_MISSING",
                exc=Exception(f"{name.capitalize()} directory missing")
            )

        # Check is_dir - fail explicitly if contract incomplete (fix #1)
        # We check hasattr to give a clear error, not as a fallback
        if not hasattr(info, 'is_dir'):
            return CapabilityResult.fail_from_exc(
                msg=f"FS contract breach: FileInfo missing 'is_dir' attribute. Cannot validate {name} directory type.",
                code="QC_ENV_FS_CONTRACT_INCOMPLETE",
                exc=Exception("FileInfo.is_dir not available - FS contract breach")
            )

        if not info.is_dir:
            return CapabilityResult.fail_from_exc(
                msg=f"{name.capitalize()} path exists but is not a directory: {path}",
                code=f"QC_ENV_{name.upper()}_DIR_NOT_DIR",
                exc=Exception(f"{name.capitalize()} path is not a directory")
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
        This method validates they exist AND are directories.

        IMPORTANT: Tools must call this explicitly from initialize() or validate().
        See module docstring for usage pattern.

        Override this method to add custom validation logic.

        Args:
            ctx: Tool context

        Returns:
            CapabilityResult indicating success or failure
        """
        try:
            fs = ctx.require_fs()

            # Validate work_dir
            if ctx.work_dir:
                result = self._validate_directory(ctx.work_dir, "work", fs)
                if result.status != CapabilityStatus.success:
                    return result

            # Validate output_dir
            if ctx.output_dir:
                result = self._validate_directory(ctx.output_dir, "output", fs)
                if result.status != CapabilityStatus.success:
                    return result

            return CapabilityResult.ok(data=None, msg="Environment validated")

        except Exception as e:
            return CapabilityResult.fail_from_exc(
                msg="Environment validation failed",
                code="QC_ENV_INIT_ERROR",
                exc=e
            )