import os
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from quack_core.core.errors import QuackIntegrationError
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.pandoc import (
    ConversionMetrics,
    ConversionTask,
    DocumentConverter,
    FileInfo,
    PandocConfig,
)

# --- Tests for DocumentConverter ---


def test_document_converter_initialization(mock_pypandoc: MagicMock) -> None:
    """Test DocumentConverter initialization."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    assert converter.config == config
    assert isinstance(converter.metrics, ConversionMetrics)
    assert converter.pandoc_version == "2.11.0"


def test_document_converter_initialization_verify_pandoc_fails(
    fs_stub: SimpleNamespace,
) -> None:
    """When verify_pandoc() raises, __init__ swallows it and falls back to
    an "unknown" version rather than propagating (converter.py:89-92)."""
    with patch(
        "quack_core.integrations.pandoc.converter.verify_pandoc"
    ) as mock_verify:
        mock_verify.side_effect = RuntimeError("pandoc not installed")

        config = PandocConfig()
        converter = DocumentConverter(config)

        assert converter.pandoc_version == "unknown"


def test_convert_file_html_to_markdown_success(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """Test successful HTML to Markdown conversion."""
    # Setup
    config = PandocConfig()
    converter = DocumentConverter(config)

    # Mock the conversion operation
    with patch(
        "quack_core.integrations.pandoc.operations.convert_html_to_markdown"
    ) as mock_convert:
        mock_convert.return_value = IntegrationResult.success_result(
            ("output.md", MagicMock()), message="Success"
        )

        # Run conversion
        result = converter.convert_file("input.html", "output.md", "markdown")

        # Verify
        assert result.success
        assert mock_convert.called
        mock_convert.assert_called_once_with(
            "input.html", "output.md", config, converter.metrics
        )


def test_convert_file_markdown_to_docx_success(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """Test successful Markdown to DOCX conversion."""
    # Setup
    config = PandocConfig()
    converter = DocumentConverter(config)

    # Mock the conversion operation
    with patch(
        "quack_core.integrations.pandoc.operations.convert_markdown_to_docx"
    ) as mock_convert:
        mock_convert.return_value = IntegrationResult.success_result(
            ("output.docx", MagicMock()), message="Success"
        )

        # Run conversion
        result = converter.convert_file("input.md", "output.docx", "docx")

        # Verify
        assert result.success
        assert mock_convert.called
        mock_convert.assert_called_once_with(
            "input.md", "output.docx", config, converter.metrics
        )


def test_convert_file_html_to_markdown_operation_failure_wraps_error(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """_wrap_conversion_result's error branch (converter.py:199) is exercised
    when the underlying conversion operation itself reports failure."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    with patch(
        "quack_core.integrations.pandoc.operations.convert_html_to_markdown"
    ) as mock_convert:
        mock_convert.return_value = IntegrationResult.error_result(
            "Pandoc blew up mid-conversion"
        )

        result = converter.convert_file("input.html", "output.md", "markdown")

        assert not result.success
        assert result.error is not None
        assert "Pandoc blew up mid-conversion" in result.error


def test_convert_file_unsupported_format(mock_pypandoc: MagicMock) -> None:
    """Test conversion with unsupported format."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    # Mock file info to return unsupported format
    with patch(
        "quack_core.integrations.pandoc.converter.get_file_info"
    ) as mock_get_info:
        mock_get_info.return_value = FileInfo(
            path="file.txt", format="txt", size=100, modified=None, extra_args=[]
        )

        # Run conversion with unsupported format
        result = converter.convert_file("file.txt", "output.md", "markdown")

        # Verify
        assert not result.success
        assert result.error is not None
        assert "Unsupported conversion" in result.error


def test_convert_file_integration_error(mock_pypandoc: MagicMock) -> None:
    """Test handling of integration errors during conversion."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    # Mock conversion to raise error
    with patch(
        "quack_core.integrations.pandoc.converter.get_file_info"
    ) as mock_get_info:
        mock_get_info.side_effect = QuackIntegrationError("Test error", {})

        # Run conversion
        result = converter.convert_file("input.html", "output.md", "markdown")

        # Verify. convert_file's get_file_info error path returns str(e)
        # directly (converter.py: `except QuackIntegrationError as e: return
        # IntegrationResult.error_result(str(e))`) -- "Failed to convert" is
        # only emitted by convert_batch's own aggregate-failure message, a
        # different code path this test does not exercise.
        assert not result.success
        assert result.error is not None
        assert "Test error" in result.error


def test_convert_batch_all_success(mock_pypandoc: MagicMock) -> None:
    """Test batch conversion with all files succeeding."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    # Mock convert_file to always succeed
    with patch.object(converter, "convert_file") as mock_convert:
        mock_convert.return_value = IntegrationResult.success_result("output.md")

        # Create tasks
        tasks = [
            ConversionTask(
                source=FileInfo(
                    path="file1.html",
                    format="html",
                    size=100,
                    modified=None,
                    extra_args=[],
                ),
                target_format="markdown",
                output_path="output1.md",
            ),
            ConversionTask(
                source=FileInfo(
                    path="file2.html",
                    format="html",
                    size=100,
                    modified=None,
                    extra_args=[],
                ),
                target_format="markdown",
                output_path="output2.md",
            ),
        ]

        # Run batch conversion
        result = converter.convert_batch(tasks)

        # Verify
        assert result.success
        assert mock_convert.call_count == 2
        assert result.content is not None
        assert len(result.content) == 2


def test_convert_batch_partial_failure(mock_pypandoc: MagicMock) -> None:
    """Test batch conversion with some files failing."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    # Mock convert_file to succeed for first file but fail for second
    def mock_convert_side_effect(
        input_path: str, output_path: str, format_: str
    ) -> IntegrationResult:
        if "file2" in input_path:
            return IntegrationResult.error_result("Conversion failed")
        return IntegrationResult.success_result(output_path)

    with patch.object(converter, "convert_file") as mock_convert:
        mock_convert.side_effect = mock_convert_side_effect

        # Create tasks
        tasks = [
            ConversionTask(
                source=FileInfo(
                    path="file1.html",
                    format="html",
                    size=100,
                    modified=None,
                    extra_args=[],
                ),
                target_format="markdown",
                output_path="output1.md",
            ),
            ConversionTask(
                source=FileInfo(
                    path="file2.html",
                    format="html",
                    size=100,
                    modified=None,
                    extra_args=[],
                ),
                target_format="markdown",
                output_path="output2.md",
            ),
        ]

        # Run batch conversion
        result = converter.convert_batch(tasks)

        # Verify
        assert result.success  # Still success overall
        assert result.message is not None
        assert "Partially successful" in result.message
        assert result.content is not None
        assert len(result.content) == 1
        assert result.content[0] == "output1.md"


def test_convert_batch_all_failure(mock_pypandoc: MagicMock) -> None:
    """Test batch conversion with all files failing."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    # Mock convert_file to always fail
    with patch.object(converter, "convert_file") as mock_convert:
        mock_convert.return_value = IntegrationResult.error_result("Conversion failed")

        # Create tasks
        tasks = [
            ConversionTask(
                source=FileInfo(
                    path="file1.html",
                    format="html",
                    size=100,
                    modified=None,
                    extra_args=[],
                ),
                target_format="markdown",
                output_path="output1.md",
            ),
            ConversionTask(
                source=FileInfo(
                    path="file2.html",
                    format="html",
                    size=100,
                    modified=None,
                    extra_args=[],
                ),
                target_format="markdown",
                output_path="output2.md",
            ),
        ]

        # Run batch conversion
        result = converter.convert_batch(tasks)

        # Verify
        assert not result.success
        assert result.error is not None
        assert "failed" in result.error.lower()
        assert mock_convert.call_count == 2


def test_validate_conversion(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """Test document validation after conversion."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    # Test successful validation. validate_conversion returns a bool (True =
    # valid), not an error list -- fs_stub's own get_file_info/read_text
    # already report a real, non-empty markdown file, so a valid conversion
    # is expected to return True here.
    assert converter.validate_conversion("output.md", "input.html")

    # Test failure when output file doesn't exist
    fs_stub.get_file_info = lambda path: SimpleNamespace(
        success=True, exists="output" not in path, size=100, modified=time.time()
    )
    assert not converter.validate_conversion("output.md", "input.html")

    # Reset fs_stub
    fs_stub.get_file_info = lambda path: SimpleNamespace(
        success=True, exists=True, size=100, modified=time.time()
    )


# --- Additional coverage: _create_output_directory_for_file ---


def test_create_output_directory_for_file_dir_creation_fails(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """Directory creation reporting success=False surfaces as an error result."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    fs_stub.create_directory = lambda path, exist_ok=True: SimpleNamespace(
        success=False, error="Permission denied"
    )

    result = converter._create_output_directory_for_file("some/dir/output.md")

    assert result is not None
    assert not result.success
    assert result.error is not None
    assert "Failed to create output directory" in result.error
    assert result.error is not None
    assert "Permission denied" in result.error


def test_create_output_directory_for_file_raises(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """An exception raised by fs.create_directory is caught and wrapped."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    def _raise(path: str, exist_ok: bool = True) -> None:
        raise OSError("disk exploded")

    fs_stub.create_directory = _raise

    result = converter._create_output_directory_for_file("some/dir/output.md")

    assert result is not None
    assert not result.success
    assert result.error is not None
    assert "Failed to create output directory" in result.error
    assert result.error is not None
    assert "disk exploded" in result.error


def test_convert_file_output_dir_creation_failure_short_circuits(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """convert_file returns the directory error result without attempting
    the conversion dispatch (converter.py:224-226)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    fs_stub.create_directory = lambda path, exist_ok=True: SimpleNamespace(
        success=False, error="No space left on device"
    )

    with patch(
        "quack_core.integrations.pandoc.operations.convert_html_to_markdown"
    ) as mock_convert:
        result = converter.convert_file("input.html", "output.md", "markdown")

        assert not result.success
        assert result.error is not None
        assert "Failed to create output directory" in result.error
        assert not mock_convert.called


def test_convert_file_integration_error_from_format_dispatch(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """A QuackIntegrationError raised during format dispatch (rather than
    during get_file_info) is caught by convert_file's outer
    QuackIntegrationError handler (converter.py:233-235), distinct from the
    inner get_file_info-specific handler covered by
    test_convert_file_integration_error."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    with patch(
        "quack_core.integrations.pandoc.operations.convert_html_to_markdown"
    ) as mock_convert:
        mock_convert.side_effect = QuackIntegrationError("dispatch blew up", {})

        result = converter.convert_file("input.html", "output.md", "markdown")

        assert not result.success
        assert result.error is not None
        assert "dispatch blew up" in result.error


def test_convert_file_unexpected_exception(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """A non-QuackIntegrationError exception raised during dispatch is caught
    by convert_file's outer generic Exception handler (converter.py:236-238)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    with patch(
        "quack_core.integrations.pandoc.converter.get_file_info"
    ) as mock_get_info:
        mock_get_info.side_effect = RuntimeError("boom")

        result = converter.convert_file("input.html", "output.md", "markdown")

        assert not result.success
        assert result.error is not None
        assert "Conversion error" in result.error
        assert result.error is not None
        assert "boom" in result.error


# --- Additional coverage: _resolve_batch_output_path ---


def test_resolve_batch_output_path_uses_task_output_path(
    mock_pypandoc: MagicMock,
) -> None:
    """When the task already specifies an output_path it is returned as-is."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    task = ConversionTask(
        source=FileInfo(
            path="file1.html", format="html", size=100, modified=None, extra_args=[]
        ),
        target_format="markdown",
        output_path="explicit_output.md",
    )

    resolved = converter._resolve_batch_output_path(task, "batch_dir")
    assert resolved == "explicit_output.md"


def test_resolve_batch_output_path_derives_from_source_filename(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """When no explicit output_path is set, the filename is derived from
    fs.split_path and joined with the batch output dir, swapping the
    extension for the target format (converter.py:257-273)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    fs_stub.split_path = lambda path: SimpleNamespace(
        success=True, data=["some", "dir", "file1.html"]
    )

    task = ConversionTask(
        source=FileInfo(
            path="some/dir/file1.html",
            format="html",
            size=100,
            modified=None,
            extra_args=[],
        ),
        target_format="markdown",
        output_path=None,
    )

    resolved = converter._resolve_batch_output_path(task, "batch_dir")
    assert resolved == os.path.join("batch_dir", "file1.md")


def test_resolve_batch_output_path_derives_non_markdown_extension(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """Non-markdown target formats use the format name itself as the
    extension (converter.py:270-271, the non-".md" branch)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    fs_stub.split_path = lambda path: SimpleNamespace(
        success=True, data=["some", "dir", "file1.md"]
    )

    task = ConversionTask(
        source=FileInfo(
            path="some/dir/file1.md",
            format="markdown",
            size=100,
            modified=None,
            extra_args=[],
        ),
        target_format="docx",
        output_path=None,
    )

    resolved = converter._resolve_batch_output_path(task, "batch_dir")
    assert resolved == os.path.join("batch_dir", "file1.docx")


def test_resolve_batch_output_path_split_failure(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """A failing fs.split_path is logged and results in None (converter.py:261-263)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    fs_stub.split_path = lambda path: SimpleNamespace(
        success=False, error="Bad path"
    )

    task = ConversionTask(
        source=FileInfo(
            path="file1.html", format="html", size=100, modified=None, extra_args=[]
        ),
        target_format="markdown",
        output_path=None,
    )

    resolved = converter._resolve_batch_output_path(task, "batch_dir")
    assert resolved is None


def test_resolve_batch_output_path_raises(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """An exception while resolving the batch output path is caught and
    logged, returning None (converter.py:274-276)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    def _raise(path: str) -> None:
        raise ValueError("path explosion")

    fs_stub.split_path = _raise

    task = ConversionTask(
        source=FileInfo(
            path="file1.html", format="html", size=100, modified=None, extra_args=[]
        ),
        target_format="markdown",
        output_path=None,
    )

    resolved = converter._resolve_batch_output_path(task, "batch_dir")
    assert resolved is None


# --- Additional coverage: _process_batch_task ---


def test_process_batch_task_unresolved_output_path_marks_failure(
    mock_pypandoc: MagicMock,
) -> None:
    """When output path resolution fails, the task's source path is recorded
    as failed and convert_file is never invoked (converter.py:297-298)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    task = ConversionTask(
        source=FileInfo(
            path="file1.html", format="html", size=100, modified=None, extra_args=[]
        ),
        target_format="markdown",
        output_path=None,
    )

    successful_files: list[str] = []
    failed_files: list[str] = []

    with (
        patch.object(
            converter, "_resolve_batch_output_path", return_value=None
        ) as mock_resolve,
        patch.object(converter, "convert_file") as mock_convert,
    ):
        converter._process_batch_task(
            task, "batch_dir", successful_files, failed_files
        )

    assert mock_resolve.called
    assert not mock_convert.called
    assert failed_files == ["file1.html"]
    assert successful_files == []


def test_process_batch_task_raises_records_metrics_error(
    mock_pypandoc: MagicMock,
) -> None:
    """An unexpected exception during batch task processing is caught,
    recorded in metrics.errors, and marks the task as failed
    (converter.py:316-320)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    task = ConversionTask(
        source=FileInfo(
            path="file1.html", format="html", size=100, modified=None, extra_args=[]
        ),
        target_format="markdown",
        output_path="output.md",
    )

    successful_files: list[str] = []
    failed_files: list[str] = []

    with patch.object(converter, "convert_file") as mock_convert:
        mock_convert.side_effect = RuntimeError("catastrophic failure")

        converter._process_batch_task(
            task, "batch_dir", successful_files, failed_files
        )

    assert failed_files == ["file1.html"]
    assert successful_files == []
    assert converter.metrics.failed_conversions == 1
    assert "catastrophic failure" in converter.metrics.errors["file1.html"]


# --- Additional coverage: convert_batch output directory creation ---


def test_convert_batch_output_dir_creation_fails(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """convert_batch surfaces an error result when the shared output
    directory cannot be created (converter.py:346-349)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    fs_stub.create_directory = lambda path, exist_ok=True: SimpleNamespace(
        success=False, error="Read-only filesystem"
    )

    result = converter.convert_batch([], output_dir="batch_out")

    assert not result.success
    assert result.error is not None
    assert "Failed to create output directory" in result.error
    assert result.error is not None
    assert "Read-only filesystem" in result.error


def test_convert_batch_output_dir_creation_raises(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """An exception from fs.create_directory during convert_batch is caught
    and wrapped in an error result (converter.py:350-352)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    def _raise(path: str, exist_ok: bool = True) -> None:
        raise OSError("mount failure")

    fs_stub.create_directory = _raise

    result = converter.convert_batch([], output_dir="batch_out")

    assert not result.success
    assert result.error is not None
    assert "Failed to create output directory" in result.error
    assert result.error is not None
    assert "mount failure" in result.error


def test_convert_batch_all_failure_more_than_five_lists_overflow_count(
    mock_pypandoc: MagicMock,
) -> None:
    """When more than five files fail, the aggregate error message truncates
    the list and appends an '... and N more' summary (converter.py:382-384)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    tasks = [
        ConversionTask(
            source=FileInfo(
                path=f"file{i}.html",
                format="html",
                size=100,
                modified=None,
                extra_args=[],
            ),
            target_format="markdown",
            output_path=f"output{i}.md",
        )
        for i in range(7)
    ]

    with patch.object(converter, "convert_file") as mock_convert:
        mock_convert.return_value = IntegrationResult.error_result("Conversion failed")

        result = converter.convert_batch(tasks)

    assert not result.success
    assert result.error is not None
    assert "and 2 more" in result.error
    assert mock_convert.call_count == 7


# --- Additional coverage: validate_conversion branches ---


def test_validate_conversion_input_file_missing(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """When the input file does not exist, validation fails
    (converter.py:419-423)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    def _get_file_info(path: str) -> SimpleNamespace:
        if "input" in path:
            return SimpleNamespace(success=True, exists=False, size=0)
        return SimpleNamespace(success=True, exists=True, size=100)

    fs_stub.get_file_info = _get_file_info

    assert not converter.validate_conversion("output.md", "input.html")


def test_validate_conversion_get_extension_raises(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """An exception from fs.get_extension is caught and a fallback extension
    derived from the raw path is used instead (converter.py:446-448)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    def _raise(path: str) -> None:
        raise ValueError("extension explosion")

    fs_stub.get_extension = _raise
    fs_stub.read_text = lambda path, encoding=None: SimpleNamespace(
        success=True, content="# Some heading\n\ncontent"
    )

    # output.md -> fallback ext resolves to "md" -> markdown validation path
    assert converter.validate_conversion("output.md", "input.html")


def test_validate_conversion_read_text_fails(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """A failing fs.read_text on a markdown output file fails validation
    (converter.py:453-457)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    fs_stub.read_text = lambda path, encoding=None: SimpleNamespace(
        success=False, error="Cannot read file"
    )

    assert not converter.validate_conversion("output.md", "input.html")


def test_validate_conversion_markdown_read_text_raises(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """An exception raised by fs.read_text on a markdown output (rather than
    a success=False result) is caught by the inner try/except and fails
    validation (converter.py:459-461)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    def _raise(path: str, encoding: str = "utf-8") -> None:
        raise OSError("read blew up")

    fs_stub.read_text = _raise

    assert not converter.validate_conversion("output.md", "input.html")


def test_validate_conversion_docx_valid(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """DOCX outputs are validated via validate_docx_structure
    (converter.py:462-467)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    with patch(
        "quack_core.integrations.pandoc.converter.validate_docx_structure"
    ) as mock_validate_docx:
        mock_validate_docx.return_value = (True, [])

        assert converter.validate_conversion("output.docx", "input.md")
        assert mock_validate_docx.called


def test_validate_conversion_docx_structure_raises(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """An exception raised while validating DOCX structure is caught and
    fails validation (converter.py:468-470)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    with patch(
        "quack_core.integrations.pandoc.converter.validate_docx_structure"
    ) as mock_validate_docx:
        mock_validate_docx.side_effect = RuntimeError("corrupt docx")

        assert not converter.validate_conversion("output.docx", "input.md")


def test_validate_conversion_unknown_extension_checks_size(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """Unknown extensions fall back to a plain output-size check against the
    configured minimum (converter.py:471-473)."""
    config = PandocConfig()
    config.validation.min_file_size = 10
    converter = DocumentConverter(config)

    fs_stub.get_file_info = lambda path: SimpleNamespace(
        success=True, exists=True, size=100
    )

    assert converter.validate_conversion("output.xyz", "input.txt")

    config.validation.min_file_size = 1000
    assert not converter.validate_conversion("output.xyz", "input.txt")


def test_validate_conversion_outer_exception_returns_false(
    mock_pypandoc: MagicMock, fs_stub: SimpleNamespace
) -> None:
    """Any unexpected exception during validation is caught by the outermost
    handler and returns False rather than propagating (converter.py:475-477)."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    def _raise(path: str) -> None:
        raise RuntimeError("total validation meltdown")

    fs_stub.get_file_info = _raise

    assert not converter.validate_conversion("output.md", "input.html")
