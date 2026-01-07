# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/tools/mixins/env_init.py
# module: quack_core.tools.mixins.env_init
# role: module
# neighbors: __init__.py, integration_enabled.py, lifecycle.py, output_handler.py
# exports: ToolEnvInitializerMixin
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===


"""
Environment validation mixin for tools.

DOCTRINE STRICT MODE:
This mixin VALIDATES existence only. It does NOT create directories.
Runner creates all directories. Tools fail if they don't exist.
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

    FS CONTRACT (MIGRATION COMPAT with deadline):

    STRICT DOCTRINE (v3.0+): FS MUST return Result objects with:
        - .success: bool (operation succeeded)
        - .data: FileInfo object (or None if failed)
        - .error: str (error message if not success)
        - FileInfo MUST have .exists: bool and .is_dir: bool

    MIGRATION COMPAT (v2.x - TEMPORARY): This mixin normalizes variations:
        - .ok vs .success
        - .value vs .data

    DEADLINE: Remove normalization in v3.0.

    TRACKING (Must-fix A - corrected guidance):
    When normalization is used, this is logged at DEBUG level via ctx.logger.

    NOTE: ctx.metadata is immutable (MappingProxyType), so tools cannot modify it.
    To track compat mode in manifests, the RUNNER should add flags when building
    the initial ToolContext, like:

        ctx = ToolContext(
            ...,
            metadata={"fs_contract_mode": "compat"} if using_compat else {}
        )

    Tools cannot and should not modify ctx.metadata after construction.
    """

    @staticmethod
    def _normalize_fs_result(result: Any) -> tuple[bool, Any, str | None, bool]:
        """
        Normalize FS result to common pattern (MIGRATION COMPAT MODE).

        DEADLINE: v3.0 - Remove this method entirely.

        Returns:
            (success, data, error, used_normalization) tuple
        """
        used_normalization = False

        # Try .success first, fall back to .ok (MIGRATION COMPAT)
        success = getattr(result, 'success', None)
        if success is None:
            success = getattr(result, 'ok', False)
            used_normalization = True

        # Try .data first, fall back to .value (MIGRATION COMPAT)
        data = getattr(result, 'data', None)
        if data is None:
            data = getattr(result, 'value', None)
            used_normalization = True

        # Try .error
        error = getattr(result, 'error', None)

        return bool(success), data, error, used_normalization

    def _validate_directory(
            self,
            path: str,
            name: str,
            fs: Any,
            ctx: "ToolContext | None" = None
    ) -> CapabilityResult[None]:
        """
        Strictly validate a directory exists and is actually a directory.

        Args:
            path: Directory path to validate
            name: Human-readable name (e.g. "work", "output")
            fs: Filesystem service
            ctx: Optional context for tracking compat mode (logging only)

        Returns:
            CapabilityResult indicating success or failure
        """
        info_result = fs.get_file_info(path)
        success, info, error, used_normalization = self._normalize_fs_result(
            info_result)

        # Track when compat mode is used (Must-fix A - via logger only)
        if used_normalization and ctx:
            if hasattr(ctx, 'logger') and ctx.logger:
                ctx.logger.debug(
                    f"FS contract compat mode used for {name} directory validation. "
                    f"Update FS implementation to use .success/.data contract. "
                    f"Compat mode will be removed in v3.0."
                )

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

        # STRICT CONTRACT: FileInfo MUST have .exists
        if not hasattr(info, 'exists'):
            return CapabilityResult.fail_from_exc(
                msg=f"FS contract breach: FileInfo missing 'exists' attribute. "
                    f"Cannot validate {name} directory. "
                    f"FileInfo contract requires .exists: bool attribute.",
                code="QC_ENV_FS_CONTRACT_INCOMPLETE",
                exc=Exception("FileInfo.exists not available - FS contract breach")
            )

        if not info.exists:
            return CapabilityResult.fail_from_exc(
                msg=f"{name.capitalize()} directory does not exist: {path}. Runner must create it.",
                code=f"QC_ENV_{name.upper()}_DIR_MISSING",
                exc=Exception(f"{name.capitalize()} directory missing")
            )

        # STRICT CONTRACT: FileInfo MUST have .is_dir
        if not hasattr(info, 'is_dir'):
            return CapabilityResult.fail_from_exc(
                msg=f"FS contract breach: FileInfo missing 'is_dir' attribute. "
                    f"Cannot validate {name} directory type. "
                    f"FileInfo contract requires .is_dir: bool attribute.",
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

        Args:
            ctx: Tool context (immutable)

        Returns:
            CapabilityResult indicating success or failure
        """
        try:
            fs = ctx.require_fs()

            # Validate work_dir (pass ctx for compat tracking via logger)
            if ctx.work_dir:
                result = self._validate_directory(ctx.work_dir, "work", fs, ctx)
                if result.status != CapabilityStatus.success:
                    return result

            # Validate output_dir (pass ctx for compat tracking via logger)
            if ctx.output_dir:
                result = self._validate_directory(ctx.output_dir, "output", fs, ctx)
                if result.status != CapabilityStatus.success:
                    return result

            return CapabilityResult.ok(data=None, msg="Environment validated")

        except Exception as e:
            return CapabilityResult.fail_from_exc(
                msg="Environment validation failed",
                code="QC_ENV_INIT_ERROR",
                exc=e
            )