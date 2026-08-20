"""
Protocol definitions for the jupytext integration.

This module defines protocol classes for notebook conversion services,
ensuring proper typing throughout the codebase. All file path parameters
and return types are represented as strings rather than pathlib.Path
objects, matching the pandoc integration's convention.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.jupytext.models import ConversionTask


@runtime_checkable
class NotebookConverterProtocol(Protocol):
    """
    Protocol for notebook converter implementations.
    All file path parameters and return types are strings.
    """

    def convert_file(
        self, input_path: str, output_path: str, output_format: str | None = None
    ) -> IntegrationResult[str]:
        """
        Convert a file from one jupytext-supported format to another.

        Args:
            input_path: The absolute path to the input file (as a string).
            output_path: The absolute path to the output file (as a string).
            output_format: The target jupytext format id (e.g. "ipynb",
                "py:percent"). Guessed from output_path's extension if None.

        Returns:
            IntegrationResult[str]: Result of the conversion, with the output file path.
        """
        ...

    def validate_conversion(self, output_path: str, input_path: str) -> bool:
        """
        Validate the converted file.

        Args:
            output_path: The absolute path to the output file (as a string).
            input_path: The absolute path to the input file (as a string).

        Returns:
            bool: True if validation passed, False otherwise.
        """
        ...


@runtime_checkable
class BatchConverterProtocol(Protocol):
    """
    Protocol for batch notebook conversion.
    File path parameters and results are represented as strings.
    """

    def convert_batch(
        self, tasks: Sequence[ConversionTask], output_dir: str | None = None
    ) -> IntegrationResult[list[str]]:
        """
        Convert a batch of files.

        Args:
            tasks: A list of conversion tasks.
            output_dir: A directory (absolute path as a string) where to save
                        converted files or None to use each task's output
                        configuration.

        Returns:
            IntegrationResult[list[str]]: Result of the batch conversion, with
            a list of output file paths.
        """
        ...


@runtime_checkable
class JupytextConversionProtocol(Protocol):
    """
    Protocol for the main jupytext conversion _ops.
    File path parameters and return types are represented as strings.
    """

    def script_to_notebook(
        self, script_path: str, output_path: str | None = None
    ) -> IntegrationResult[str]:
        """
        Convert a paired script/markdown file (.py, .md, ...) to a Jupyter
        notebook (.ipynb).

        Args:
            script_path: The absolute path to the source script/markdown file.
            output_path: Optional absolute path to save the .ipynb file.

        Returns:
            IntegrationResult[str]: Result of the conversion with the output file path.
        """
        ...

    def notebook_to_script(
        self,
        notebook_path: str,
        output_path: str | None = None,
        script_format: str | None = None,
    ) -> IntegrationResult[str]:
        """
        Convert a Jupyter notebook (.ipynb) to a paired script/markdown file.

        Args:
            notebook_path: The absolute path to the source .ipynb file.
            output_path: Optional absolute path to save the script file.
            script_format: Optional jupytext format id (e.g. "py:percent").
                Defaults to the integration's configured default script format.

        Returns:
            IntegrationResult[str]: Result of the conversion with the output file path.
        """
        ...

    def convert_directory(
        self,
        input_dir: str,
        output_format: str,
        output_dir: str | None = None,
        pattern: str = "*",
    ) -> IntegrationResult[list[str]]:
        """
        Convert all matching files in a directory.

        Args:
            input_dir: The absolute path to the directory containing files to
                convert (as a string).
            output_format: The target jupytext format id (e.g. "ipynb").
            output_dir: Optional absolute path to the directory in which to
                save converted files.
            pattern: Glob pattern used to select input files.

        Returns:
            IntegrationResult[list[str]]: Result of the conversion with a list
            of output file paths.
        """
        ...
