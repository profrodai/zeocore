# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/paths/service.py
# module: quack_core.core.paths.service
# role: service
# neighbors: __init__.py, models.py, plugin.py
# exports: PathService
# git_branch: feat/9-make-setup-work
# git_commit: 19533b6c
# === QV-LLM:END ===

"""
Path service for quack_core.

This module provides the PUBLIC high-level service for path operations.
It delegates logic to the internal Resolver and returns typed Result objects.
"""

import os
from pathlib import Path
from typing import Any

from quack_core.core.fs import DataResult, OperationResult
from quack_core.lib.logging import get_logger
from quack_core.lib.paths._internal.resolver import PathResolver
from quack_core.lib.paths._internal.utils import (
    _find_nearest_directory,
    _infer_module_from_path,
    _resolve_relative_to_project,
    _normalize_path_param,
)
from quack_core.lib.paths.api.public.results import ContextResult, PathResult, \
    StringResult


class PathService:
    """
    Public service for path-related operations.
    Wraps internal logic with consistent error handling and return types.
    """

    def __init__(self) -> None:
        self._resolver = PathResolver()
        self.logger = get_logger(__name__)

    def _norm(self, path_param: Any) -> str:
        """Internal helper to normalize inputs."""
        return _normalize_path_param(path_param)

    def get_project_root(
            self,
            start_dir: str | Path | DataResult | OperationResult | None = None,
            marker_files: list[str | Path | DataResult | OperationResult] | None = None,
            marker_dirs: list[str | Path | DataResult | OperationResult] | None = None,
    ) -> PathResult:
        """Find the project root directory."""
        try:
            start = None if start_dir is None else self._norm(start_dir)
            mf = None if marker_files is None else [self._norm(m) for m in marker_files]
            md = None if marker_dirs is None else [self._norm(d) for d in marker_dirs]

            path = self._resolver._get_project_root(start, mf, md)
            return PathResult(success=True, path=path)
        except Exception as e:
            self.logger.error(f"Failed to get project root: {e}")
            return PathResult(success=False, error=str(e))

    def resolve_project_path(
            self,
            path: str | Path | DataResult | OperationResult,
            project_root: str | Path | DataResult | OperationResult | None = None,
    ) -> PathResult:
        """Resolve a path relative to the project root."""
        try:
            path_str = self._norm(path)
            root = None if project_root is None else self._norm(project_root)
            resolved = self._resolver._resolve_project_path(path_str, root)
            return PathResult(success=True, path=resolved)
        except Exception as e:
            self.logger.error(f"Failed to resolve project path: {e}")
            return PathResult(success=False, error=str(e))

    def detect_project_context(
            self,
            start_dir: str | Path | DataResult | OperationResult | None = None,
    ) -> ContextResult:
        """Detect project context from a directory."""
        try:
            start = None if start_dir is None else self._norm(start_dir)
            ctx = self._resolver._detect_project_context(start)
            return ContextResult(success=True, context=ctx)
        except Exception as e:
            self.logger.error(f"Failed to detect project context: {e}")
            return ContextResult(success=False, error=str(e))

    def get_known_directory(
            self,
            name: str,
            start_dir: str | Path | DataResult | OperationResult | None = None,
    ) -> PathResult:
        """Get a known directory (e.g. 'src', 'output') by name."""
        try:
            # We use detection here to ensure we have the full map
            start = None if start_dir is None else self._norm(start_dir)
            ctx_res = self.detect_project_context(start)

            if not ctx_res.success or not ctx_res.context:
                return PathResult(success=False,
                                  error=ctx_res.error or "Context detection failed")

            dir_path = ctx_res.context._get_directory(name)
            if not dir_path:
                return PathResult(success=False,
                                  error=f"Directory '{name}' not found in project")

            return PathResult(success=True, path=dir_path)
        except Exception as e:
            self.logger.error(f"Failed to get known directory '{name}': {e}")
            return PathResult(success=False, error=str(e))

    def get_module_path(
            self,
            module: str,
            start_dir: str | Path | DataResult | OperationResult | None = None,
    ) -> PathResult:
        """Get the filesystem path for a Python module."""
        try:
            start = None if start_dir is None else self._norm(start_dir)
            ctx_res = self.detect_project_context(start)

            if not ctx_res.success or not ctx_res.context:
                return PathResult(success=False, error=ctx_res.error)

            src_dir = ctx_res.context._get_source_dir()
            if not src_dir:
                return PathResult(success=False, error="Source directory not found")

            # This part still does FS checks, but they are semantic checks specific
            # to module resolution, which is acceptable here.
            module_parts = module.split('.')
            file_path = os.path.join(src_dir, *module_parts)

            if os.path.isdir(file_path):
                init_path = os.path.join(file_path, '__init__.py')
                if os.path.exists(init_path):
                    return PathResult(success=True, path=init_path)
                return PathResult(success=False,
                                  error=f"Package '{module}' has no __init__.py")
            else:
                py_path = file_path + '.py'
                if os.path.exists(py_path):
                    return PathResult(success=True, path=py_path)
                return PathResult(success=False, error=f"Module '{module}' not found")
        except Exception as e:
            return PathResult(success=False, error=str(e))

    def find_nearest_directory(
            self,
            name: str,
            start_dir: str | Path | DataResult | OperationResult | None = None,
            max_levels: int = 5,
    ) -> PathResult:
        """Find the nearest directory with the given name (searching upwards)."""
        try:
            start = None if start_dir is None else self._norm(start_dir)
            path = _find_nearest_directory(name, start, max_levels)
            return PathResult(success=True, path=path)
        except Exception as e:
            return PathResult(success=False, error=str(e))

    def resolve_relative_to_project(
            self,
            path: str | Path | DataResult | OperationResult,
            project_root: str | Path | DataResult | OperationResult | None = None,
    ) -> PathResult:
        """Resolve a path relative to the project root (lightweight)."""
        try:
            p = self._norm(path)
            r = None if project_root is None else self._norm(project_root)
            resolved = _resolve_relative_to_project(p, r)
            return PathResult(success=True, path=resolved)
        except Exception as e:
            return PathResult(success=False, error=str(e))

    def infer_module_from_path(
            self,
            path: str | Path | DataResult | OperationResult,
            project_root: str | Path | DataResult | OperationResult | None = None,
    ) -> StringResult:
        """Infer the Python module name from a file path."""
        try:
            p = self._norm(path)
            r = None if project_root is None else self._norm(project_root)
            module_name = _infer_module_from_path(p, r)
            return StringResult(success=True, value=module_name)
        except Exception as e:
            return StringResult(success=False, error=str(e))

    def get_relative_path(
            self,
            abs_path: str | Path | DataResult | OperationResult,
            start_dir: str | Path | DataResult | OperationResult | None = None,
    ) -> PathResult:
        """Get the path relative to the project root."""
        try:
            p = os.path.abspath(self._norm(abs_path))
            root_res = self.get_project_root(start_dir)

            if not root_res.success or not root_res.path:
                return PathResult(success=False, error=root_res.error)

            root = os.path.abspath(root_res.path)

            # Robust check: ensure p is actually strictly inside root
            # using commonpath to avoid prefix bugs (e.g. /proj vs /proj2)
            try:
                common = os.path.commonpath([root, p])
            except ValueError:
                # Can happen on Windows with different drives
                common = ""

            if common != root:
                return PathResult(success=False,
                                  error=f"Path '{p}' is not inside project root '{root}'")

            rel = os.path.relpath(p, root)
            return PathResult(success=True, path=rel)
        except Exception as e:
            return PathResult(success=False, error=str(e))