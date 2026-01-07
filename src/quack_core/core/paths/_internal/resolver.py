# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/paths/_internal/resolver.py
# module: quack_core.core.paths._internal.resolver
# role: module
# neighbors: __init__.py, utils.py, context.py
# exports: PathResolver
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

# quack-core/src/quack_core/paths/_internal/resolver.py
"""
Path resolver service for quack_core.

This module provides a high-level service for resolving paths
in a QuackCore project, using string-based path parameters internally.
It detects project structure and infers context from file locations.
"""

from os import getcwd
from os import path as ospath

from quack_core.errors import QuackFileNotFoundError, wrap_io_errors
from quack_core.fs.service import standalone
from quack_core.logging import LOG_LEVELS, LogLevel, get_logger
from quack_core.paths._internal.context import ContentContext, ProjectContext
from quack_core.paths._internal.utils import _find_nearest_directory, _find_project_root


# Helper function to determine if one path is relative to another.
def _is_relative_to(child: str, parent: str) -> bool:
    try:
        return ospath.commonpath([
            ospath.abspath(child), ospath.abspath(parent)
        ]) == ospath.abspath(parent)
    except Exception:
        return False


# Helper function to get parent directory from a string path.
def _get_parent_dir(p: str) -> str:
    split_result = standalone.split_path(p)
    if not split_result.success:
        return p
    comps = split_result.data
    if len(comps) <= 1:
        return p
    join_result = standalone.join_path(*comps[:-1])
    return join_result.data if join_result.success else p


# Helper function to compute relative path.
def _compute_relative_path(full_path: str, base_path: str) -> str | None:
    try:
        abs_full = ospath.abspath(full_path)
        abs_base = ospath.abspath(base_path)
        if abs_full.startswith(abs_base):
            rel = abs_full[len(abs_base):]
            return rel.lstrip("/\\")
    except Exception:
        pass
    return None


class PathResolver:
    """
    High-level service for path resolution in QuackCore projects.

    This service uses string paths internally to resolve paths, detect project
    structure, and infer context from file locations.
    """

    def __init__(self, log_level: int = LOG_LEVELS[LogLevel.INFO]) -> None:
        """
        Initialize the path resolver service.

        Args:
            log_level: Logging level for the service.
        """
        self.logger = get_logger(__name__)
        self.logger.setLevel(log_level)
        self._cache: dict[str, ProjectContext] = {}

    def _get_project_root(
        self,
        start_dir: str | None = None,
        marker_files: list[str] | None = None,
        marker_dirs: list[str] | None = None,
    ) -> str:
        """
        Find the project root directory.

        Args:
            start_dir: Directory to start searching from (string; default: current directory)
            marker_files: List of filenames that indicate a project root
            marker_dirs: List of directory names that indicate a project root

        Returns:
            Absolute path (string) to the project root directory.

        Raises:
            QuackFileNotFoundError: If project root cannot be found.
        """
        start = start_dir if start_dir is not None else getcwd()
        root = _find_project_root(start, marker_files, marker_dirs)
        return root

    def _detect_standard_directories(self, context: ProjectContext) -> None:
        """
        Detect standard directories in a project and add them to the context.

        Args:
            context: ProjectContext to update.
        """
        root_dir = context.root_dir

        # Source directory
        try:
            src_dir = self._find_source_directory(root_dir)
            context._add_directory("src", src_dir, is_source=True)
        except QuackFileNotFoundError:
            try:
                src_dir = _find_nearest_directory("src", root_dir)
                context._add_directory("src", src_dir, is_source=True)
            except QuackFileNotFoundError:
                pass

        # Output directory
        try:
            output_dir = self._find_output_directory(root_dir)
            context._add_directory("output", output_dir, is_output=True)
        except QuackFileNotFoundError:
            pass

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
            join_result = standalone.join_path(root_dir, name)
            if not join_result.success:
                continue
            dir_path = join_result.data
            info = standalone.get_file_info(dir_path)
            if info.success and info.exists and info.is_dir:
                context._add_directory(name, dir_path, **attrs)

    def _find_source_directory(
        self,
        start_dir: str | None = None,
    ) -> str:
        """
        Find the source directory of a project.

        Args:
            start_dir: Directory to start searching from (string; default: current directory)

        Returns:
            Absolute path (string) to the source directory.

        Raises:
            QuackFileNotFoundError: If a source directory cannot be found.
        """
        current_dir = start_dir if start_dir is not None else getcwd()
        join_result = standalone.join_path(current_dir, "__init__.py")
        if not join_result.success:
            raise QuackFileNotFoundError("__init__.py", f"Failed to join path: {join_result.error}")
        init_path = join_result.data
        info = standalone.get_file_info(init_path)
        if info.success and info.exists:
            return current_dir

        try:
            return _find_nearest_directory("src", current_dir)
        except QuackFileNotFoundError as e:
            for _ in range(5):
                join_result = standalone.join_path(current_dir, "__init__.py")
                if not join_result.success:
                    continue
                init_path = join_result.data
                info = standalone.get_file_info(init_path)
                if info.success and info.exists:
                    return current_dir
                current_dir = _get_parent_dir(current_dir)
            raise QuackFileNotFoundError(
                "src",
                f"Could not find source directory in or near {start_dir or getcwd()}"
            ) from e

    def _find_output_directory(
        self,
        start_dir: str | None = None,
        create: bool = False,
    ) -> str:
        """
        Find or create an output directory for a project.

        Args:
            start_dir: Directory to start searching from (string; default: current directory)
            create: Whether to create the directory if it doesn't exist

        Returns:
            Absolute path (string) to the output directory.

        Raises:
            QuackFileNotFoundError: If output directory cannot be found and create is False.
        """
        if start_dir and create:
            join_result = standalone.join_path(start_dir, "output")
            if not join_result.success:
                raise QuackFileNotFoundError("output", f"Failed to join path: {join_result.error}")
            output_dir = join_result.data
            create_result = standalone.create_directory(output_dir, exist_ok=True)
            if not create_result.success:
                raise QuackFileNotFoundError("output", f"Failed to create directory: {create_result.error}")
            return output_dir

        try:
            root_dir = self._get_project_root(start_dir)
            for candidate in ["output", "build"]:
                join_result = standalone.join_path(root_dir, candidate)
                if not join_result.success:
                    continue
                output_dir = join_result.data
                info = standalone.get_file_info(output_dir)
                if info.success and info.exists:
                    return output_dir
            if create:
                join_result = standalone.join_path(root_dir, "output")
                if not join_result.success:
                    raise QuackFileNotFoundError("output", f"Failed to join path: {join_result.error}")
                output_dir = join_result.data
                create_result = standalone.create_directory(output_dir, exist_ok=True)
                if not create_result.success:
                    raise QuackFileNotFoundError("output", f"Failed to create directory: {create_result.error}")
                return output_dir
            raise QuackFileNotFoundError(
                "output", f"Could not find output directory in project root {root_dir}"
            )
        except QuackFileNotFoundError as e:
            current_dir = start_dir or getcwd()
            if create:
                join_result = standalone.join_path(current_dir, "output")
                if not join_result.success:
                    raise QuackFileNotFoundError("output", f"Failed to join path: {join_result.error}")
                output_dir = join_result.data
                create_result = standalone.create_directory(output_dir, exist_ok=True)
                if not create_result.success:
                    raise QuackFileNotFoundError("output", f"Failed to create directory: {create_result.error}")
                return output_dir
            raise QuackFileNotFoundError(
                "output", f"Could not find output directory in or near {current_dir}"
            ) from e

    def _resolve_project_path(
        self,
        path_value: str | None,
        project_root: str | None = None,
    ) -> str:
        """
        Resolve a path relative to the project root.

        Args:
            path_value: Path to resolve (string; if None returns empty string)
            project_root: Project root directory (string; default: auto-detected)

        Returns:
            Resolved absolute path as a string.
        """
        if path_value is None:
            return ""
        if ospath.isabs(path_value):
            return path_value
        root = project_root or self._get_project_root()
        join_result = standalone.join_path(root, path_value)
        if not join_result.success:
            self.logger.error(f"Failed to join path: {join_result.error}")
            # Fallback to using os.path.join directly
            return ospath.join(root, path_value)
        return join_result.data

    def _infer_content_structure(
        self,
        context: ContentContext,
        current_dir: str | None = None,
    ) -> None:
        """
        Infer content structure from directory and update context.

        Args:
            context: ContentContext to update
            current_dir: Current directory (string; default: current working directory)
        """
        current = current_dir or getcwd()
        src_dir = context._get_source_dir()
        if not src_dir or not _is_relative_to(current, src_dir):
            return
        rel = ospath.relpath(current, src_dir)
        parts = rel.split(ospath.sep)
        if parts and parts[0] in ["tutorials", "videos"]:
            context.content_type = parts[0]
            if len(parts) > 1:
                context.content_name = parts[1]
                join_result = standalone.join_path(src_dir, parts[0], parts[1])
                if join_result.success:
                    context.content_dir = join_result.data

    @wrap_io_errors
    def _detect_project_context(
        self,
        start_dir: str | None = None,
    ) -> ProjectContext:
        """
        Detect project context from a directory.

        Args:
            start_dir: Directory to start searching from (string; default: current directory)

        Returns:
            ProjectContext object.

        Raises:
            QuackFileNotFoundError: If the start directory does not exist.
        """
        start = start_dir or getcwd()
        info = standalone.get_file_info(start)
        if not (info.success and info.exists):
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
        self._detect_config_file(context)
        self._cache[key] = context
        return context

    def _detect_config_file(self, context: ProjectContext) -> None:
        """
        Detect configuration file in a project.

        Args:
            context: ProjectContext to update
        """
        root = context.root_dir
        for fname in ["quack_config.yaml", "pyproject.toml", "setup.py"]:
            join_result = standalone.join_path(root, fname)
            if not join_result.success:
                continue
            fp = join_result.data
            info = standalone.get_file_info(fp)
            if info.success and info.exists and info.is_file:
                context.config_file = fp
                break

    def _detect_content_context(
        self,
        start_dir: str | None = None,
        content_type: str | None = None,
    ) -> ContentContext:
        """
        Detect content context from a directory.

        Args:
            start_dir: Directory to start searching from (string; default: current directory)
            content_type: Type of content (string; optional)

        Returns:
            ContentContext object.
        """
        proj_ctx = self._detect_project_context(start_dir)
        context = ContentContext(
            root_dir=proj_ctx.root_dir,
            directories=proj_ctx.directories,
            config_file=proj_ctx.config_file,
            name=proj_ctx.name,
            content_type=content_type,
        )
        if content_type is None:
            self._infer_content_structure(context, start_dir)
        return context

    def _infer_current_content(
        self,
        start_dir: str | None = None,
    ) -> dict[str, str]:
        """
        Infer current content type and name from a directory.

        Args:
            start_dir: Directory to start from (string; default: current directory)

        Returns:
            Dict with 'type' and 'name' keys.
        """
        context = self._detect_content_context(start_dir)
        result: dict[str, str] = {}
        if context.content_type:
            result["type"] = context.content_type
        if context.content_name:
            result["name"] = context.content_name
        return result


# Module-level convenience functions.
def _get_project_root(
    start_dir: str | None = None,
    marker_files: list[str] | None = None,
    marker_dirs: list[str] | None = None,
) -> str:
    """
    Convenience to find project root without instantiating resolver.

    Args:
        start_dir: Directory to start searching from (string; default: current directory)
        marker_files: List of filenames that indicate a project root
        marker_dirs: List of directory names that indicate a project root

    Returns:
        Absolute project root path as a string.
    """
    return PathResolver()._get_project_root(start_dir, marker_files, marker_dirs)


def _resolve_project_path(
    path_value: str,
    project_root: str | None = None,
) -> str:
    """
    Convenience to resolve a path relative to project root.

    Args:
        path_value: Path to resolve (string)
        project_root: Project root directory (string; default: auto-detected)

    Returns:
        Resolved absolute path as a string.
    """
    return PathResolver()._resolve_project_path(path_value, project_root)
