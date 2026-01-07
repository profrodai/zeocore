# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/path_validation.py
# module: quack_core.core.fs.service.path_validation
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, file_operations.py, full_class.py (+4 more)
# exports: PathValidationMixin
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/service/path_validation.py
"""
Path validation utilities for the FileSystemService.

These utilities extend the FileSystemService with methods to validate
and inspect paths, primarily used for configuration validation.
"""

from pathlib import Path

from quack_core.errors import wrap_io_errors
from quack_core.fs._operations import FileSystemOperations
from quack_core.fs.results import DataResult, OperationResult, PathResult
from quack_core.logging import get_logger

logger = get_logger(__name__)


class PathValidationMixin:
    """
    Mixin class for path validation operations in the FileSystemService.

    This mixin "dogfoods" our existing implementation from FileInfoOperationsMixin
    (or any compatible implementation exposed via `self._operations`) to check if a path exists.
    """

    # This ensures the mixin will only be used with classes that have an '_operations' attribute.
    operations: FileSystemOperations

    # This method is added in the base class
    def _normalize_input_path(self,
                              path: str | Path | DataResult | OperationResult) -> Path:
        """Normalize an input path to a Path object."""
        raise NotImplementedError("This method should be overridden")

    def path_exists(self, path: str | Path | DataResult | OperationResult) -> \
            DataResult[bool]:
        """
        Check if a path exists in the filesystem by leveraging the existing
        FileInfoOperationsMixin implementation via self._operations.

        Args:
            path: Path to check for existence (string, Path, DataResult, or OperationResult)

        Returns:
            DataResult with boolean indicating if the path exists
        """
        normalized_path = self._normalize_input_path(path)
        try:
            # Delegate to the file_info's path_exists implementation
            exists = self.operations._path_exists(normalized_path)

            return DataResult(
                success=True,
                path=normalized_path,
                data=exists,
                format="boolean",
                message=f"Path {normalized_path} {'exists' if exists else 'does not exist'}",
            )
        except Exception as exc:
            logger.error(f"Error checking if path exists using _operations: {exc}")
            # Fallback: use the standard pathlib.Path.exists() check
            try:
                exists = normalized_path.exists()
                logger.debug(f"Fallback check for {normalized_path} returned: {exists}")

                return DataResult(
                    success=True,
                    path=normalized_path,
                    data=exists,
                    format="boolean",
                    message=f"Path {normalized_path} {'exists' if exists else 'does not exist'} (fallback check)",
                )
            except Exception as fallback_exc:
                logger.error(
                    f"Fallback direct check failed for {normalized_path}: {fallback_exc}"
                )

                return DataResult(
                    success=False,
                    path=normalized_path,
                    data=False,
                    format="boolean",
                    error=f"Failed to check if path exists: {str(fallback_exc)}",
                )

    def get_path_info(self,
                      path: str | Path | DataResult | OperationResult) -> PathResult:
        """
        Get information about a path's validity and format.

        This method checks whether a path is valid and provides information
        without requiring the path to exist.

        Args:
            path: Path to check (string, Path, DataResult, or OperationResult)

        Returns:
            PathResult with validation results
        """
        try:
            normalized_path = self._normalize_input_path(path)
            is_absolute = normalized_path.is_absolute()

            # Check if the path syntax is valid without requiring existence
            is_valid = self.operations._is_path_syntax_valid(str(normalized_path))

            # Check for existence (optional info)
            exists_result = self.path_exists(normalized_path)
            exists = exists_result.data if exists_result.success else False

            return PathResult(
                success=True,
                path=normalized_path,
                is_absolute=is_absolute,
                is_valid=is_valid,
                exists=exists,
                message="Path validation successful",
            )
        except Exception as e:
            try:
                normalized_path = self._normalize_input_path(path)
            except:
                normalized_path = Path()

            return PathResult(
                success=False,
                path=normalized_path,
                is_valid=False,
                error=f"Path validation failed: {str(e)}",
            )

    def is_valid_path(self, path: str | Path | DataResult | OperationResult) -> \
            DataResult[bool]:
        """
        Check if a path has valid syntax.

        This method checks only the syntax validity of a path,
        not whether it exists or is accessible.

        Args:
            path: Path to check (string, Path, DataResult, or OperationResult)

        Returns:
            DataResult with boolean indicating if the path has valid syntax
        """
        normalized_path = self._normalize_input_path(path)
        try:
            is_valid = self.operations._is_path_syntax_valid(str(normalized_path))

            return DataResult(
                success=True,
                path=normalized_path,
                data=is_valid,
                format="boolean",
                message=f"Path {normalized_path} {'has valid' if is_valid else 'has invalid'} syntax",
            )
        except Exception as e:
            logger.error(f"Error checking path validity for {normalized_path}: {e}")

            return DataResult(
                success=False,
                path=normalized_path,
                data=False,
                format="boolean",
                error=f"Failed to check path validity: {str(e)}",
            )

    @wrap_io_errors
    def normalize_path_with_info(self,
                                 path: str | Path | DataResult | OperationResult) -> PathResult:
        """
        Normalize a path and return detailed information.

        This enhanced version of normalize_path returns a PathResult object
        with success status and additional information.

        Args:
            path: Path to normalize (string, Path, DataResult, or OperationResult)

        Returns:
            PathResult with the normalized path and status information
        """
        try:
            normalized_path = self._normalize_input_path(path)
            normalized_path = self.operations._normalize_path(normalized_path)

            exists_result = self.path_exists(normalized_path)
            exists = exists_result.data if exists_result.success else False

            return PathResult(
                success=True,
                path=normalized_path,
                is_absolute=normalized_path.is_absolute(),
                is_valid=True,
                exists=exists,
                message="Path normalized successfully",
            )
        except Exception as e:
            try:
                normalized_path = self._normalize_input_path(path)
            except:
                normalized_path = Path()

            return PathResult(
                success=False,
                path=normalized_path,
                is_valid=False,
                error=f"Path normalization failed: {e}",
            )

    def resolve_path_strict(self,
                            path: str | Path | DataResult | OperationResult) -> PathResult:
        """
        Resolve a path and verify it exists.

        Args:
            path: Path to resolve (string, Path, DataResult, or OperationResult)

        Returns:
            PathResult with the resolved path and validation information
        """
        normalized_path = self._normalize_input_path(path)
        try:
            resolved = self.operations._resolve_path(normalized_path)
            if not resolved.exists():
                return PathResult(
                    success=False,
                    path=resolved,
                    is_valid=False,
                    exists=False,
                    error="Resolved path does not exist",
                )
            return PathResult(
                success=True,
                path=resolved,
                is_valid=True,
                exists=True,
                message="Successfully resolved existing path",
            )
        except Exception as e:
            return PathResult(
                success=False,
                path=normalized_path,
                is_valid=False,
                exists=False,
                error=f"Failed to resolve path: {str(e)}",
            )
