# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/structured_data.py
# module: quack_core.core.fs.service.structured_data
# role: service
# neighbors: __init__.py, base.py, directory_operations.py, factory.py, file_operations.py, full_class.py (+4 more)
# exports: StructuredDataMixin
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

# quack-core/src/quack_core/fs/service/structured_data.py
"""
Structured data operations (JSON, YAML) for the FileSystemService.
"""

from pathlib import Path

from quack_core.errors import wrap_io_errors
from quack_core.fs._operations import FileSystemOperations
from quack_core.fs.results import DataResult, OperationResult, WriteResult
from quack_core.logging import get_logger

# Set up logger
logger = get_logger(__name__)


class StructuredDataMixin:
    """Mixin class for structured data operations in the FileSystemService."""

    # This ensures the mixin will only be used with classes that have operations
    operations: FileSystemOperations

    # This method is added in the base class
    def _normalize_input_path(self,
                              path: str | Path | DataResult | OperationResult) -> Path:
        """Normalize an input path to a Path object."""
        raise NotImplementedError("This method should be overridden")

    # --- Structured Data Operations ---

    @wrap_io_errors
    def read_yaml(self, path: str | Path | DataResult | OperationResult) -> DataResult[
        dict]:
        """
        Read YAML file and parse its contents.

        Args:
            path: Path to YAML file (string, Path, DataResult, or OperationResult)

        Returns:
            DataResult with parsed YAML data
        """
        normalized_path = self._normalize_input_path(path)
        try:
            data = self.operations._read_yaml(normalized_path)
            logger.info(f"Successfully read YAML data from {normalized_path} with {len(data)} top-level keys")
            return DataResult(
                success=True,
                path=normalized_path,
                data=data,
                format="yaml",
                message=f"Successfully read YAML data from {normalized_path}"
            )
        except ImportError as e:
            logger.error(f"YAML library not available: {str(e)}")
            return DataResult(
                success=False,
                path=normalized_path,
                data={},
                format="yaml",
                error=f"YAML library not available: {str(e)}",
                message="Failed to read YAML due to missing library"
            )
        except Exception as e:
            logger.error(f"Error reading YAML file {normalized_path}: {str(e)}")
            return DataResult(
                success=False,
                path=normalized_path,
                data={},
                format="yaml",
                error=str(e),
                message=f"Failed to read YAML from {normalized_path}"
            )

    @wrap_io_errors
    def write_yaml(
            self,
            path: str | Path | DataResult | OperationResult,
            data: dict,
            atomic: bool = True,
    ) -> WriteResult:
        """
        Write data to a YAML file.

        Args:
            path: Path to YAML file (string, Path, DataResult, or OperationResult)
            data: Data to write
            atomic: Whether to use atomic writing

        Returns:
            WriteResult with operation status
        """
        normalized_path = self._normalize_input_path(path)
        try:
            result_path = self.operations._write_yaml(normalized_path, data, atomic)
            logger.info(f"Successfully wrote YAML data to {result_path}")
            return WriteResult(
                success=True,
                path=result_path,
                message=f"Successfully wrote YAML data to {result_path}"
            )
        except ImportError as e:
            logger.error(f"YAML library not available: {str(e)}")
            return WriteResult(
                success=False,
                path=normalized_path,
                error=f"YAML library not available: {str(e)}",
                message="Failed to write YAML due to missing library"
            )
        except Exception as e:
            logger.error(f"Error writing YAML to {normalized_path}: {str(e)}")
            return WriteResult(
                success=False,
                path=normalized_path,
                error=str(e),
                message=f"Failed to write YAML to {normalized_path}"
            )

    @wrap_io_errors
    def read_json(self, path: str | Path | DataResult | OperationResult) -> DataResult[
        dict]:
        """
        Read JSON file and parse its contents.

        Args:
            path: Path to JSON file (string, Path, DataResult, or OperationResult)

        Returns:
            DataResult with parsed JSON data
        """
        normalized_path = self._normalize_input_path(path)
        try:
            data = self.operations._read_json(normalized_path)
            logger.info(f"Successfully read JSON data from {normalized_path} with {len(data)} top-level keys")
            return DataResult(
                success=True,
                path=normalized_path,
                data=data,
                format="json",
                message=f"Successfully read JSON data from {normalized_path}"
            )
        except Exception as e:
            logger.error(f"Error reading JSON file {normalized_path}: {str(e)}")
            return DataResult(
                success=False,
                path=normalized_path,
                data={},
                format="json",
                error=str(e),
                message=f"Failed to read JSON from {normalized_path}"
            )

    @wrap_io_errors
    def write_json(
            self,
            path: str | Path | DataResult | OperationResult,
            data: dict,
            atomic: bool = True,
            indent: int = 2,
    ) -> WriteResult:
        """
        Write data to a JSON file.

        Args:
            path: Path to JSON file (string, Path, DataResult, or OperationResult)
            data: Data to write
            atomic: Whether to use atomic writing
            indent: Number of spaces to indent

        Returns:
            WriteResult with operation status
        """
        normalized_path = self._normalize_input_path(path)
        try:
            result_path = self.operations._write_json(normalized_path, data, atomic, indent)
            logger.info(f"Successfully wrote JSON data to {result_path}")
            return WriteResult(
                success=True,
                path=result_path,
                message=f"Successfully wrote JSON data to {result_path}"
            )
        except Exception as e:
            logger.error(f"Error writing JSON to {normalized_path}: {str(e)}")
            return WriteResult(
                success=False,
                path=normalized_path,
                error=str(e),
                message=f"Failed to write JSON to {normalized_path}"
            )
