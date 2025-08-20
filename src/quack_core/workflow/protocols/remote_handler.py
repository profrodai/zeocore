# quack-core/src/quack-core/workflow/protocols/remote_handler.py
from __future__ import annotations

from typing import Protocol, runtime_checkable

from quackcore.workflow.results import InputResult


@runtime_checkable
class RemoteFileHandler(Protocol):
    """Protocol defining the interface for remote file handlers."""

    def is_remote(self, source: str) -> bool:
        """
        Determine if the given source is a remote file.

        Args:
            source: The source path or URL.

        Returns:
            True if the source is remote, False otherwise.
        """
        ...

    def download(self, source: str) -> InputResult:
        """
        Download a remote file and return an InputResult.

        Args:
            source: The remote source path or URL.

        Returns:
            InputResult containing the path to the downloaded file.
        """
        ...
