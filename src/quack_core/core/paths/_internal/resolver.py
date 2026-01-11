# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/paths/_internal/resolver.py
# module: quack_core.core.paths._internal.resolver
# role: module
# neighbors: __init__.py, utils.py, context.py
# exports: PathResolver
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

"""
Path resolver internal logic.

This module contains the semantic logic for resolving paths and detecting context.
It is an internal dependency of the public PathService.
"""

from os import getcwd
from os import path as ospath

from quack_core.core.errors import QuackFileNotFoundError, wrap_io_errors
from quack_core.core.fs.service import standalone
from quack_core.core.logging import LOG_LEVELS, LogLevel, get_logger
from quack_core.core.paths.models import ContentContext, ProjectContext
from quack_core.core.paths._internal.utils import (
    _find_nearest_directory,
    _find_project_root,
    _normalize_path_param,
)


class PathResolver:
    """
    Internal service for path logic.
    """

    def __init__(self, log_level: int = LOG_LEVELS[LogLevel.INFO]) -> None:
        self.logger = get_logger(__name__)
        # No setLevel here - defer to global config
        self._cache: dict[str, ProjectContext] = {}

    def _get_project_root(
            self,
            start_dir: str | None = None,
            marker_files: list[str] | None = None,
            marker_dirs: list[str] | None = None,
    ) -> str:
        return _find_project_root(start_dir, marker_files, marker_dirs)

    def _detect_standard_directories(self, context: ProjectContext) -> None:
        """Detect standard directories and populate the context."""
        root_dir = context.root_dir

        # Source directory
        try:
            src_dir = self._find_source_directory(root_dir)
            context._add_directory("src", src_dir, is_source=True)
        except QuackFileNotFoundError:
            pass

        # Output directory
        join_res = standalone.join_path(root_dir, "output")
        if join_res.success and join_res.data:
            out_path = str(join_res.data)
            if ospath.exists(out_path):
                context._add_directory("output", out_path, is_output=True)

        # Other standard directories
        standard_dirs = {
            "tests": {"is_test": True},
            "data": {"is_data": True},
            "config": {"is_config": True},
            "docs": {},
            "assets": {"is_asset": True},
            "scripts": {},
        }
        for name, attrs in standard_dirs.items():
            join_res = standalone.join_path(root_dir, name)
            if not join_res.success or not join_res.data:
                continue

            dir_path = str(join_res.data)
            if ospath.exists(dir_path) and ospath.isdir(dir_path):
                context._add_directory(name, dir_path, **attrs)

    def _find_source_directory(self, start_dir: str | None = None) -> str:
        """Find the source directory."""
        current_dir = start_dir if start_dir is not None else getcwd()

        # 1. Look for src
        try:
            return _find_nearest_directory("src", current_dir)
        except QuackFileNotFoundError:
            pass

        # 2. Look for project root that contains __init__.py
        join_res = standalone.join_path(current_dir, "__init__.py")
        if join_res.success and join_res.data:
            if ospath.exists(str(join_res.data)):
                return current_dir

        raise QuackFileNotFoundError("src", "Could not find source directory.")

    def _find_output_directory(self, start_dir: str | None = None,
                               create: bool = False) -> str:
        """Find or create output directory."""
        try:
            root_dir = self._get_project_root(start_dir)

            for candidate in ["output", "build"]:
                join_res = standalone.join_path(root_dir, candidate)
                if join_res.success and join_res.data:
                    path = str(join_res.data)
                    if ospath.exists(path):
                        return path

            if create:
                res = standalone.join_path(root_dir, "output")
                if res.success and res.data:
                    out_path = str(res.data)
                    standalone.create_directory(out_path, exist_ok=True)
                    return out_path

            raise QuackFileNotFoundError("output", f"No output directory in {root_dir}")

        except QuackFileNotFoundError as e:
            if create:
                current = start_dir or getcwd()
                res = standalone.join_path(current, "output")
                if res.success and res.data:
                    out_path = str(res.data)
                    standalone.create_directory(out_path, exist_ok=True)
                    return out_path
            raise e

    def _resolve_project_path(
            self,
            path_value: str | None,
            project_root: str | None = None,
    ) -> str:
        if path_value is None:
            return ""
        if ospath.isabs(path_value):
            return path_value

        root = project_root or self._get_project_root()
        res = standalone.join_path(root, path_value)
        if res.success and res.data:
            return str(res.data)
        return ospath.join(root, path_value)

    @wrap_io_errors
    def _detect_project_context(self, start_dir: str | None = None) -> ProjectContext:
        """Core logic for context detection."""
        start = start_dir or getcwd()
        if not ospath.exists(start):
            raise QuackFileNotFoundError(start)

        try:
            root = _find_project_root(start)
        except QuackFileNotFoundError:
            root = start

        key = ospath.abspath(root)
        if key in self._cache:
            return self._cache[key]

        context = ProjectContext(root_dir=root)
        context.name = ospath.basename(ospath.abspath(root))

        self._detect_standard_directories(context)

        # Config file detection
        for fname in ["quack_config.yaml", "pyproject.toml", "setup.py"]:
            res = standalone.join_path(root, fname)
            if res.success and res.data:
                check_path = str(res.data)
                if ospath.exists(check_path):
                    context.config_file = check_path
                    break

        self._cache[key] = context
        return context

    def _detect_content_context(
            self,
            start_dir: str | None = None,
            content_type: str | None = None,
    ) -> ContentContext:
        proj_ctx = self._detect_project_context(start_dir)
        context = ContentContext(
            root_dir=proj_ctx.root_dir,
            directories=proj_ctx.directories,
            config_file=proj_ctx.config_file,
            name=proj_ctx.name,
            content_type=content_type,
        )
        return context