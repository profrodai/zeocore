# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/path_operations.py
# module: quack_core.core.fs.service.path_operations
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, file_operations.py, full_class.py (+4 more)
# exports: PathOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/service/path_operations.py
"""
Path operations utilities for the FileSystemService.

These utilities extend the FileSystemService with methods for path manipulation.
"""

from pathlib import Path

from quack_core.errors import wrap_io_errors
from quack_core.fs._operations import FileSystemOperations
from quack_core.fs.results import DataResult, OperationResult, PathResult
from quack_core.logging import get_logger

# Set up logger
logger = get_logger(__name__)


class PathOperationsMixin:
    """Mixin class for path operations in the FileSystemService."""

    # This ensures the mixin will only be used with classes that have operations
    operations: FileSystemOperations

    # This method is added in the base class
    def _normalize_input_path(self,
                              path: str | Path | DataResult | OperationResult) -> Path:
        """Normalize an input path to a Path object."""
        raise NotImplementedError("This method should be overridden")

    @wrap_io_errors
    def join_path(self, *parts: str | Path | DataResult | OperationResult) -> \
            DataResult[str]:
        """
        Join path components safely, extracting path values from result objects.

        Args:
            *parts: Path parts to join (can be any type of path or result object)

        Returns:
            DataResult with the joined path
        """
        try:
            if not parts:
                result_path = Path()
            else:
                # Extract proper path component from each part
                extracted_parts = []
                for part in parts:
                    # Handle PathResult (path attribute)
                    if hasattr(part, "path") and part.path is not None:
                        extracted_parts.append(part.path)
                    # Handle DataResult (data attribute)
                    elif hasattr(part, "data") and part.data is not None:
                        extracted_parts.append(part.data)
                    else:
                        extracted_parts.append(part)

                # Now normalize each extracted part
                normalized_parts = [self._normalize_input_path(part) for part in
                                    extracted_parts]
                base_path = normalized_parts[0]
                for part in normalized_parts[1:]:
                    base_path = base_path / part
                result_path = base_path

            return DataResult(
                success=True,
                path=result_path,
                data=str(result_path),
                format="path",
                message="Successfully joined path parts",
            )
        except Exception as e:
            if not parts:
                path_for_error = Path()
            else:
                try:
                    path_for_error = self._normalize_input_path(parts[0])
                except:
                    path_for_error = Path()

            return DataResult(
                success=False,
                path=path_for_error,
                data="",
                format="path",
                error=str(e),
                message="Failed to join path parts",
            )

    @wrap_io_errors
    def split_path(self, path: str | Path | DataResult | OperationResult) -> DataResult[
        list[str]]:
        """
        Split a path into its components.

        Args:
            path: Path to split (string, Path, DataResult, or OperationResult)

        Returns:
            DataResult with list of path components
        """
        normalized_path = self._normalize_input_path(path)
        try:
            components = self.operations._split_path(normalized_path)
            return DataResult(
                success=True,
                path=normalized_path,
                data=components,
                format="path_components",
                message=f"Split path into {len(components)} components",
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=normalized_path,
                data=[],
                format="path_components",
                error=str(e),
                message="Failed to split path",
            )

    @wrap_io_errors
    def normalize_path(self, path: str | Path | DataResult | OperationResult) -> \
            PathResult:
        """
        Normalize a path for cross-platform compatibility.

        This does not check if the path exists.

        Args:
            path: Path to normalize (string, Path, DataResult, or OperationResult)

        Returns:
            PathResult with normalized path
        """
        normalized_path = self._normalize_input_path(path)
        try:
            result_path = self.operations._normalize_path(normalized_path)
            return PathResult(
                success=True,
                path=result_path,
                is_absolute=result_path.is_absolute(),
                is_valid=True,
                exists=result_path.exists(),
                message=f"Normalized path: {result_path}",
            )
        except Exception as e:
            return PathResult(
                success=False,
                path=normalized_path,
                is_absolute=normalized_path.is_absolute(),
                is_valid=False,
                exists=False,
                error=str(e),
                message="Failed to normalize path",
            )

    @wrap_io_errors
    def expand_user_vars(self, path: str | Path | DataResult | OperationResult) -> \
            DataResult[str]:
        """
        Expand user variables and environment variables in a path.

        Args:
            path: Path with variables (string, Path, DataResult, or OperationResult)

        Returns:
            DataResult with expanded path
        """
        normalized_path = self._normalize_input_path(path)
        try:
            expanded = self.operations._expand_user_vars(normalized_path)
            return DataResult(
                success=True,
                path=normalized_path,
                data=expanded,
                format="path",
                message=f"Expanded path: {expanded}",
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=normalized_path,
                data=str(normalized_path),
                format="path",
                error=str(e),
                message="Failed to expand variables in path",
            )

    @wrap_io_errors
    def is_same_file(self, path1: str | Path | DataResult | OperationResult,
                     path2: str | Path | DataResult | OperationResult) -> DataResult[
        bool]:
        """
        Check if two paths refer to the same file.

        Args:
            path1: First path (string, Path, DataResult, or OperationResult)
            path2: Second path (string, Path, DataResult, or OperationResult)

        Returns:
            DataResult with True if paths refer to the same file
        """
        normalized_path1 = self._normalize_input_path(path1)
        normalized_path2 = self._normalize_input_path(path2)
        try:
            is_same = self.operations._is_same_file(normalized_path1, normalized_path2)
            return DataResult(
                success=True,
                path=normalized_path1,
                data=is_same,
                format="boolean",
                message=f"Paths {normalized_path1} and {normalized_path2} {'refer to the same file' if is_same else 'do not refer to the same file'}",
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=normalized_path1,
                data=False,
                format="boolean",
                error=str(e),
                message="Failed to check if paths refer to the same file",
            )

    @wrap_io_errors
    def is_subdirectory(
            self, child: str | Path | DataResult | OperationResult,
            parent: str | Path | DataResult | OperationResult
    ) -> DataResult[bool]:
        """
        Check if a path is a subdirectory of another path.

        Args:
            child: Potential child path (string, Path, DataResult, or OperationResult)
            parent: Potential parent path (string, Path, DataResult, or OperationResult)

        Returns:
            DataResult with True if child is a subdirectory of parent
        """
        normalized_child = self._normalize_input_path(child)
        normalized_parent = self._normalize_input_path(parent)
        try:
            is_subdir = self.operations._is_subdirectory(normalized_child,
                                                         normalized_parent)
            return DataResult(
                success=True,
                path=normalized_child,
                data=is_subdir,
                format="boolean",
                message=f"Path {normalized_child} {'is' if is_subdir else 'is not'} a subdirectory of {normalized_parent}",
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=normalized_child,
                data=False,
                format="boolean",
                error=str(e),
                message="Failed to check if path is a subdirectory",
            )

    @wrap_io_errors
    def create_temp_directory(
            self, prefix: str = "quackcore_", suffix: str = ""
    ) -> DataResult[str]:
        """
        Create a temporary directory.

        Args:
            prefix: Prefix for the temporary directory name
            suffix: Suffix for the temporary directory name

        Returns:
            DataResult with path to the created temporary directory
        """
        try:
            temp_dir = self.operations._create_temp_directory(prefix, suffix)
            return DataResult(
                success=True,
                path=temp_dir,
                data=str(temp_dir),
                format="path",
                message=f"Created temporary directory: {temp_dir}",
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=None,
                data="",
                format="path",
                error=str(e),
                message="Failed to create temporary directory",
            )

    @wrap_io_errors
    def get_extension(self, path: str | Path | DataResult | OperationResult) -> \
            DataResult[str]:
        """
        Get the file extension from a path.

        Args:
            path: Path to get extension from (string, Path, DataResult, or OperationResult)

        Returns:
            DataResult with file extension without the dot
        """
        normalized_path = self._normalize_input_path(path)
        try:
            extension = self.operations._get_extension(normalized_path)
            return DataResult(
                success=True,
                path=normalized_path,
                data=extension,
                format="extension",
                message=f"Successfully extracted extension: {extension}",
            )
        except Exception as e:
            return DataResult(
                success=False,
                path=normalized_path,
                data="",
                format="extension",
                error=str(e),
                message="Failed to extract file extension",
            )

    @wrap_io_errors
    def resolve_path(self, path: str | Path | DataResult | OperationResult) -> \
            PathResult:
        """
        Resolve a path relative to the service's base_dir and return as a string.

        This is a public, safe wrapper around _resolve_path that conforms to
        the DataResult structure used throughout quack_core.

        Args:
            path: Input path (absolute or relative) (string, Path, DataResult, or OperationResult)

        Returns:
            PathResult with the fully resolved, absolute path as a string.
        """
        try:
            normalized_path = self._normalize_input_path(path)
            resolved = self.operations._resolve_path(normalized_path)
            return PathResult(
                success=True,
                path=resolved,
                is_absolute=resolved.is_absolute(),
                is_valid=True,
                exists=resolved.exists(),
                message=f"Resolved path to: {resolved}",
            )
        except Exception as e:
            # even on failure we normalize so we have a Path to report on
            normalized = self._normalize_input_path(path)
            return PathResult(
                success=False,
                path=normalized,
                is_absolute=normalized.is_absolute(),
                is_valid=False,
                exists=normalized.exists(),
                message="Failed to resolve path",
                error=str(e),
            )
