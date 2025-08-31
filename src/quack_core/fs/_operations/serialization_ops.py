# quack-core/src/quack-core/fs/_operations/serialization_ops.py
"""
Serialization _operations (JSON, YAML) for filesystem _operations.

This module provides internal _operations for reading and writing
structured data formats (JSON, YAML).
"""

import json
from pathlib import Path
from typing import Any, TypeVar

from quack_core.errors import (
    QuackValidationError,
)
from quack_core.logging import get_logger

# Set up logger
logger = get_logger(__name__)

# Try to import YAML library
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    logger.warning("PyYAML library not found. YAML _operations will not be available.")
    YAML_AVAILABLE = False

# Define type variable for generic typing
T = TypeVar("T")


class SerializationOperationsMixin:
    """
    Serialization _operations mixin class.

    Provides internal methods for serializing and deserializing structured
    data formats (JSON, YAML).
    """

    def _resolve_path(self, path: str | Path) -> Path:
        """
        Resolve a path relative to the base directory.

        Args:
            path: Path to resolve (str or Path)

        Returns:
            Path: Resolved Path object

        Note:
            Internal helper method implemented in the main class.
            Not meant for external consumption.
        """
        # This method is implemented in the main class
        # It's defined here for type checking
        raise NotImplementedError("This method should be overridden")

    def _read_text(self, path: str | Path, encoding: str = "utf-8") -> str:
        """
        Read text from a file.

        Args:
            path: Path to file (str or Path)
            encoding: Text encoding

        Returns:
            str: The file content as text

        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If there's no permission to read the file
            IOError: For other IO-related errors

        Note:
            Method implemented in ReadOperationsMixin.
            Defined here for type checking.
        """
        # This method is implemented in ReadOperationsMixin
        # It's defined here for type checking
        raise NotImplementedError("This method should be overridden")

    def _write_text(
            self, path: str | Path, content: str, encoding: str = "utf-8", **kwargs
    ) -> Path:
        """
        Write text to a file.

        Args:
            path: Path to file (str or Path)
            content: Text content
            encoding: Text encoding
            **kwargs: Additional arguments

        Returns:
            Path: The path where the file was written

        Raises:
            IOError: If an error occurs during writing
            PermissionError: If there's no permission to write to the file

        Note:
            Method implemented in WriteOperationsMixin.
            Defined here for type checking.
        """
        # This method is implemented in WriteOperationsMixin
        # It's defined here for type checking
        raise NotImplementedError("This method should be overridden")

    # -------------------------------
    # YAML _operations
    # -------------------------------
    def _read_yaml(self, path: str | Path) -> dict[str, Any]:
        """
        Read YAML file and parse its contents.

        This method reads a YAML file, parses it, and validates that
        it contains a dictionary. Empty YAML files are treated as
        empty dictionaries.

        Args:
            path: Path to YAML file (str or Path)

        Returns:
            dict[str, Any]: The parsed YAML data as a dictionary

        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If there's no permission to read the file
            ImportError: If the PyYAML library is not available
            QuackFormatError: If the YAML syntax is invalid
            QuackValidationError: If the YAML content is not a dictionary
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        if not YAML_AVAILABLE:
            error_msg = "PyYAML library not available. Cannot read YAML file."
            logger.error(error_msg)
            raise ImportError(error_msg)

        resolved_path = self._resolve_path(path)
        logger.debug(f"Reading YAML from: {resolved_path}")

        text_content = self._read_text(resolved_path)

        logger.debug("Parsing YAML content")
        data = yaml.safe_load(text_content)

        if data is None:
            logger.debug("YAML content is empty, using empty dict")
            data = {}
        elif not isinstance(data, dict):
            logger.error(
                f"YAML content is not a dictionary: {type(data)} in {resolved_path}"
            )
            raise QuackValidationError(
                f"YAML content is not a dictionary: {type(data)}", resolved_path
            )

        logger.info(
            f"Successfully parsed YAML data from {resolved_path} "
            f"with {len(data)} top-level keys"
        )

        return data

    def _write_yaml(
            self, path: str | Path, data: dict[str, Any], atomic: bool = True
    ) -> Path:
        """
        Write data to a YAML file.

        This method serializes a dictionary to YAML format and writes
        it to the specified file.

        Args:
            path: Path to YAML file (str or Path)
            data: Dictionary data to write
            atomic: Whether to use atomic writing (safer but slower)

        Returns:
            Path: The path where the file was written

        Raises:
            ImportError: If the PyYAML library is not available
            QuackFormatError: If the data cannot be serialized to YAML
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        if not YAML_AVAILABLE:
            error_msg = "PyYAML library not available. Cannot write YAML file."
            logger.error(error_msg)
            raise ImportError(error_msg)

        resolved_path = self._resolve_path(path)
        logger.debug(f"Writing YAML to: {resolved_path}, atomic={atomic}")

        logger.debug("Converting data to YAML format")
        yaml_content = yaml.safe_dump(
            data,
            default_flow_style=False,
            sort_keys=False,
        )

        logger.debug(f"Writing YAML content to {resolved_path}")
        return self._write_text(resolved_path, yaml_content, atomic=atomic)

    # -------------------------------
    # JSON _operations
    # -------------------------------
    def _read_json(self, path: str | Path) -> dict[str, Any]:
        """
        Read JSON file and parse its contents.

        This method reads a JSON file, parses it, and validates that
        it contains a dictionary (JSON object).

        Args:
            path: Path to JSON file (str or Path)

        Returns:
            dict[str, Any]: The parsed JSON data as a dictionary

        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If there's no permission to read the file
            json.JSONDecodeError: If the JSON syntax is invalid
            QuackValidationError: If the JSON content is not an object
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(f"Reading JSON from: {resolved_path}")

        text_content = self._read_text(resolved_path)

        logger.debug("Parsing JSON content")
        data = json.loads(text_content)

        if not isinstance(data, dict):
            logger.error(
                f"JSON content is not an object: {type(data)} in {resolved_path}"
            )
            raise QuackValidationError(
                f"JSON content is not an object: {type(data)}", resolved_path
            )

        logger.info(
            f"Successfully parsed JSON data from {resolved_path} "
            f"with {len(data)} top-level keys"
        )

        return data

    def _write_json(
            self,
            path: str | Path,
            data: dict[str, Any],
            atomic: bool = True,
            indent: int = 2,
    ) -> Path:
        """
        Write data to a JSON file.

        This method serializes a dictionary to JSON format and writes
        it to the specified file with optional formatting options.

        Args:
            path: Path to JSON file (str or Path)
            data: Dictionary data to write
            atomic: Whether to use atomic writing (safer but slower)
            indent: Number of spaces to indent (for readability)

        Returns:
            Path: The path where the file was written

        Raises:
            TypeError: If the data cannot be serialized to JSON
            IOError: For other IO-related errors

        Note:
            Internal helper method not meant for external consumption.
            Used by public-facing methods in the service layer.
        """
        resolved_path = self._resolve_path(path)
        logger.debug(
            f"Writing JSON to: {resolved_path}, atomic={atomic}, indent={indent}"
        )

        logger.debug("Converting data to JSON format")
        json_content = json.dumps(
            data,
            indent=indent,
            ensure_ascii=False,
        )

        logger.debug(f"Writing JSON content to {resolved_path}")
        return self._write_text(resolved_path, json_content, atomic=atomic)
