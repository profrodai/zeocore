"""
Notebook converter for the jupytext integration.

Mirrors the pandoc integration's ``DocumentConverter`` shape: a thin
dispatch layer that resolves a source/target format pair to the right
``operations`` function, wraps the result, and offers a batch entry point.
The actual jupytext calls live in ``operations/to_notebook.py`` and
``operations/to_script.py``, never here -- matching pandoc's own separation
between ``converter.py`` (dispatch) and ``operations/*.py`` (the pypandoc
calls).
"""

import logging
import os
from collections.abc import Sequence
from datetime import datetime

from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.jupytext.config import JupytextConfig
from zeo_core.integrations.jupytext.models import ConversionDetails, ConversionTask
from zeo_core.integrations.jupytext.operations.to_notebook import convert_to_notebook
from zeo_core.integrations.jupytext.operations.to_script import convert_to_script
from zeo_core.integrations.jupytext.operations.utils import verify_jupytext
from zeo_core.integrations.jupytext.protocols import (
    BatchConverterProtocol,
    NotebookConverterProtocol,
)

logger = logging.getLogger(__name__)


class NotebookConverter(NotebookConverterProtocol, BatchConverterProtocol):
    """Converts between jupytext-paired script/markdown formats and .ipynb."""

    def __init__(self, config: JupytextConfig) -> None:
        self.config: JupytextConfig = config
        self.start_time: datetime = datetime.now()
        try:
            self._jupytext_version: str = verify_jupytext()
        except Exception as e:
            logger.warning(f"jupytext availability check failed: {e}")
            self._jupytext_version = "unknown"

    @property
    def jupytext_version(self) -> str:
        """The detected jupytext package version, or "unknown"."""
        return self._jupytext_version

    def convert_file(
        self,
        input_path: str,
        output_path: str,
        output_format: str | None = None,
    ) -> IntegrationResult[str]:
        """
        Convert a file to the given target format, dispatching on whether
        the target is a notebook (``ipynb``) or a paired script/markdown
        format.

        Args:
            input_path: Path to the source file.
            output_path: Path to write the converted file.
            output_format: Target jupytext format id. Guessed from
                ``output_path``'s extension when omitted.

        Returns:
            IntegrationResult[str]: The output path on success.
        """
        target = output_format or self._guess_target_format(output_path)

        if target == "ipynb" or output_path.endswith(".ipynb"):
            result = convert_to_notebook(input_path, output_path, self.config)
        else:
            result = convert_to_script(
                input_path, output_path, self.config, target_format=target
            )

        return self._unwrap(result)

    def convert_batch(
        self,
        tasks: Sequence[ConversionTask],
        output_dir: str | None = None,
    ) -> IntegrationResult[list[str]]:
        """
        Convert a batch of files.

        Args:
            tasks: Conversion tasks to run.
            output_dir: Optional directory to write all outputs into,
                overriding each task's own output_path directory.

        Returns:
            IntegrationResult[list[str]]: Output paths for every task that
            succeeded. Succeeds with a "Partially successful" message if
            some tasks failed, and only fails outright if every task failed.
        """
        successful: list[str] = []
        failed: list[str] = []

        for task in tasks:
            output_path = self._resolve_batch_output_path(task, output_dir)
            result = self.convert_file(
                task.source.path, output_path, task.target_format
            )
            if result.success and result.content:
                successful.append(result.content)
            else:
                failed.append(f"{task.source.path}: {result.error}")

        if not tasks:
            return IntegrationResult.success_result([], message="No tasks to convert")

        if successful and not failed:
            return IntegrationResult.success_result(
                successful, message=f"Converted {len(successful)} file(s)"
            )
        if successful and failed:
            return IntegrationResult(
                success=True,
                content=successful,
                message=(
                    f"Partially successful: {len(successful)} converted, "
                    f"{len(failed)} failed"
                ),
                error="; ".join(failed[:5])
                + (f" (and {len(failed) - 5} more)" if len(failed) > 5 else ""),
            )
        return IntegrationResult.error_result(
            "; ".join(failed[:5])
            + (f" (and {len(failed) - 5} more)" if len(failed) > 5 else "")
        )

    def validate_conversion(self, output_path: str, input_path: str) -> bool:
        """
        Validate that a conversion produced a real, non-trivial output file.

        Args:
            output_path: Path to the converted output file.
            input_path: Path to the original source file (unused directly,
                kept for protocol-shape parity with pandoc's converter).

        Returns:
            bool: True if the output file exists and meets the minimum size.
        """
        del input_path  # protocol parity only, see docstring
        try:
            size = os.path.getsize(output_path)
        except OSError:
            return False
        return size >= self.config.validation.min_file_size

    def _guess_target_format(self, output_path: str) -> str:
        """Guess a jupytext format id from the output path's extension."""
        from zeo_core.integrations.jupytext.operations.utils import (
            guess_format_from_path,
        )

        return guess_format_from_path(
            output_path, default=self.config.default_script_format
        )

    def _resolve_batch_output_path(
        self, task: ConversionTask, batch_output_dir: str | None
    ) -> str:
        """Resolve a task's effective output path, honoring a batch override dir."""
        if task.output_path:
            if batch_output_dir:
                return os.path.join(
                    batch_output_dir, os.path.basename(task.output_path)
                )
            return task.output_path

        extension = ".ipynb" if task.target_format == "ipynb" else ".py"
        name, _ = os.path.splitext(os.path.basename(task.source.path))
        directory = batch_output_dir or os.path.dirname(task.source.path)
        return os.path.join(directory, name + extension)

    @staticmethod
    def _unwrap(
        result: IntegrationResult[tuple[str, ConversionDetails]],
    ) -> IntegrationResult[str]:
        """Narrow an operations-layer (path, details) result to a bare path result."""
        if not result.success or result.content is None:
            return IntegrationResult.error_result(
                error=result.error or "Conversion failed",
                message=result.message,
            )
        output_path, _details = result.content
        return IntegrationResult.success_result(output_path, message=result.message)
