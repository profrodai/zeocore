# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/mocks/media.py
# role: tests
# neighbors: __init__.py, base.py, credentials.py, download.py, requests.py, resources.py (+1 more)
# exports: MockDownloadStatus, MockMediaDownloader, create_mock_media_io_base_download
# git_branch: feat/9-make-setup-work
# git_commit: 41712bc9
# === QV-LLM:END ===

"""
Mock objects for Google Drive media _operations (downloads, uploads).

This module provides mock implementations for media _operations such as
download status, media uploaders, and downloaders.
"""

from collections.abc import Callable


class MockDownloadStatus:
    """
    A special mock for download status that properly supports comparison _operations.

    This is needed because the real MediaIoBaseDownload status has comparison _operations
    that are used internally, and MagicMock doesn't handle these correctly.
    """

    def __init__(self, progress_value: float):
        """
        Initialize with a progress value.

        Args:
            progress_value: The download progress (0.0 to 1.0)
        """
        self._progress_value = float(progress_value)

    def progress(self) -> float:
        """Return the progress value, mimicking real behavior."""
        return self._progress_value

    # Add proper comparison support
    def __eq__(self, other) -> bool:
        if isinstance(other, (int, float)):
            return self._progress_value == other
        if hasattr(other, "progress") and callable(other.progress):
            return self._progress_value == other.progress()
        return NotImplemented

    def __lt__(self, other) -> bool:
        if isinstance(other, (int, float)):
            return self._progress_value < other
        if hasattr(other, "progress") and callable(other.progress):
            return self._progress_value < other.progress()
        return NotImplemented

    def __le__(self, other) -> bool:
        if isinstance(other, (int, float)):
            return self._progress_value <= other
        if hasattr(other, "progress") and callable(other.progress):
            return self._progress_value <= other.progress()
        return NotImplemented

    def __gt__(self, other) -> bool:
        if isinstance(other, (int, float)):
            return self._progress_value > other
        if hasattr(other, "progress") and callable(other.progress):
            return self._progress_value > other.progress()
        return NotImplemented

    def __ge__(self, other) -> bool:
        if isinstance(other, (int, float)):
            return self._progress_value >= other
        if hasattr(other, "progress") and callable(other.progress):
            return self._progress_value >= other.progress()
        return NotImplemented

    def __repr__(self) -> str:
        return f"MockDownloadStatus(progress={self._progress_value})"


class MockMediaDownloader:
    """
    A mock for MediaIoBaseDownload that properly mimics its behavior.

    This is needed because the real MediaIoBaseDownload has complex internal
    logic that regular MagicMock can't properly simulate.
    """

    def __init__(self, progress_sequence: list[tuple[float, bool]] | None = None):
        """
        Initialize the mock downloader with a sequence of progress values.

        Args:
            progress_sequence: List of (progress_value, done) tuples
        """
        self.progress_sequence = progress_sequence or [(0.5, False), (1.0, True)]
        self.call_count = 0

    def next_chunk(self, num_retries: int = 0) -> tuple[MockDownloadStatus, bool]:
        """
        Simulate the next_chunk method of MediaIoBaseDownload.

        Args:
            num_retries: Number of retries to attempt (not used in mock)

        Returns:
            Tuple of (status, done) where status is a MockDownloadStatus
            and done is a boolean

        Raises:
            IndexError: If no more chunks are available
        """
        if self.call_count >= len(self.progress_sequence):
            raise IndexError("No more chunks available")

        progress_value, done = self.progress_sequence[self.call_count]
        self.call_count += 1

        # Return a proper mock status object with progress value
        status = MockDownloadStatus(progress_value)
        return status, done


def create_mock_media_io_base_download() -> Callable:
    """
    Create a factory function for MockMediaDownloader.

    Returns:
        A factory function that produces configured download mock objects
    """

    def create_downloader_factory(
        progress_sequence: list[tuple[float, bool]] | None = None,
    ) -> MockMediaDownloader:
        """
        Create a mock downloader with the specified progress sequence.

        Args:
            progress_sequence: Optional sequence of (progress, done) tuples

        Returns:
            MockMediaDownloader: A mock downloader object with next_chunk method
        """
        return MockMediaDownloader(progress_sequence)

    return create_downloader_factory
