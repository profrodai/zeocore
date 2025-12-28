# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/pandoc/test_converter.py
# role: tests
# neighbors: __init__.py, conftest.py, mocks.py, test-pandoc-integration-full.py, test_config.py, test_models.py (+4 more)
# exports: test_document_converter_initialization, test_convert_file_html_to_markdown_success, test_convert_file_markdown_to_docx_success, test_convert_file_unsupported_format, test_convert_file_integration_error, test_convert_batch_all_success, test_convert_batch_partial_failure, test_convert_batch_all_failure (+1 more)
# git_branch: refactor/newHeaders
# git_commit: 98b2a5c
# === QV-LLM:END ===

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from quack_core.lib.errors import QuackIntegrationError
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.pandoc import (
    ConversionMetrics,
    ConversionTask,
    DocumentConverter,
    FileInfo,
    PandocConfig,
)

# --- Tests for DocumentConverter ---

def test_document_converter_initialization(mock_pypandoc):
    """Test DocumentConverter initialization."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    assert converter.config == config
    assert isinstance(converter.metrics, ConversionMetrics)
    assert converter.pandoc_version == "2.11.0"


def test_convert_file_html_to_markdown_success(mock_pypandoc, fs_stub):
    """Test successful HTML to Markdown conversion."""
    # Setup
    config = PandocConfig()
    converter = DocumentConverter(config)

    # Mock the conversion operation
    with patch(
            'quack_core.integrations.pandoc.operations.convert_html_to_markdown') as mock_convert:
        mock_convert.return_value = IntegrationResult.success_result(
            ("output.md", MagicMock()),
            message="Success"
        )

        # Run conversion
        result = converter.convert_file("input.html", "output.md", "markdown")

        # Verify
        assert result.success
        assert mock_convert.called
        mock_convert.assert_called_once_with(
            "input.html", "output.md", config, converter.metrics
        )


def test_convert_file_markdown_to_docx_success(mock_pypandoc, fs_stub):
    """Test successful Markdown to DOCX conversion."""
    # Setup
    config = PandocConfig()
    converter = DocumentConverter(config)

    # Mock the conversion operation
    with patch(
            'quack_core.integrations.pandoc.operations.convert_markdown_to_docx') as mock_convert:
        mock_convert.return_value = IntegrationResult.success_result(
            ("output.docx", MagicMock()),
            message="Success"
        )

        # Run conversion
        result = converter.convert_file("input.md", "output.docx", "docx")

        # Verify
        assert result.success
        assert mock_convert.called
        mock_convert.assert_called_once_with(
            "input.md", "output.docx", config, converter.metrics
        )


def test_convert_file_unsupported_format(mock_pypandoc):
    """Test conversion with unsupported format."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    # Mock file info to return unsupported format
    with patch(
            'quack_core.integrations.pandoc.operations.utils.get_file_info') as mock_get_info:
        mock_get_info.return_value = FileInfo(
            path="file.txt", format="txt", size=100, modified=None, extra_args=[]
        )

        # Run conversion with unsupported format
        result = converter.convert_file("file.txt", "output.md", "markdown")

        # Verify
        assert not result.success
        assert "Unsupported conversion" in result.error


def test_convert_file_integration_error(mock_pypandoc):
    """Test handling of integration errors during conversion."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    # Mock conversion to raise error
    with patch(
            'quack_core.integrations.pandoc.operations.utils.get_file_info') as mock_get_info:
        mock_get_info.side_effect = QuackIntegrationError("Test error", {})

        # Run conversion
        result = converter.convert_file("input.html", "output.md", "markdown")

        # Verify
        assert not result.success
        assert "Failed to convert" in result.error


def test_convert_batch_all_success(mock_pypandoc):
    """Test batch conversion with all files succeeding."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    # Mock convert_file to always succeed
    with patch.object(converter, 'convert_file') as mock_convert:
        mock_convert.return_value = IntegrationResult.success_result("output.md")

        # Create tasks
        tasks = [
            ConversionTask(
                source=FileInfo(path="file1.html", format="html", size=100,
                                modified=None, extra_args=[]),
                target_format="markdown",
                output_path="output1.md"
            ),
            ConversionTask(
                source=FileInfo(path="file2.html", format="html", size=100,
                                modified=None, extra_args=[]),
                target_format="markdown",
                output_path="output2.md"
            )
        ]

        # Run batch conversion
        result = converter.convert_batch(tasks)

        # Verify
        assert result.success
        assert mock_convert.call_count == 2
        assert len(result.content) == 2


def test_convert_batch_partial_failure(mock_pypandoc):
    """Test batch conversion with some files failing."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    # Mock convert_file to succeed for first file but fail for second
    def mock_convert_side_effect(input_path, output_path, format_):
        if "file2" in input_path:
            return IntegrationResult.error_result("Conversion failed")
        return IntegrationResult.success_result(output_path)

    with patch.object(converter, 'convert_file') as mock_convert:
        mock_convert.side_effect = mock_convert_side_effect

        # Create tasks
        tasks = [
            ConversionTask(
                source=FileInfo(path="file1.html", format="html", size=100,
                                modified=None, extra_args=[]),
                target_format="markdown",
                output_path="output1.md"
            ),
            ConversionTask(
                source=FileInfo(path="file2.html", format="html", size=100,
                                modified=None, extra_args=[]),
                target_format="markdown",
                output_path="output2.md"
            )
        ]

        # Run batch conversion
        result = converter.convert_batch(tasks)

        # Verify
        assert result.success  # Still success overall
        assert "Partially successful" in result.message
        assert len(result.content) == 1
        assert result.content[0] == "output1.md"


def test_convert_batch_all_failure(mock_pypandoc):
    """Test batch conversion with all files failing."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    # Mock convert_file to always fail
    with patch.object(converter, 'convert_file') as mock_convert:
        mock_convert.return_value = IntegrationResult.error_result("Conversion failed")

        # Create tasks
        tasks = [
            ConversionTask(
                source=FileInfo(path="file1.html", format="html", size=100,
                                modified=None, extra_args=[]),
                target_format="markdown",
                output_path="output1.md"
            ),
            ConversionTask(
                source=FileInfo(path="file2.html", format="html", size=100,
                                modified=None, extra_args=[]),
                target_format="markdown",
                output_path="output2.md"
            )
        ]

        # Run batch conversion
        result = converter.convert_batch(tasks)

        # Verify
        assert not result.success
        assert "failed" in result.error.lower()
        assert mock_convert.call_count == 2


def test_validate_conversion(mock_pypandoc, fs_stub):
    """Test document validation after conversion."""
    config = PandocConfig()
    converter = DocumentConverter(config)

    # Test successful validation
    with patch('quack_core.lib.fs.service.standalone.get_file_info', return_value=SimpleNamespace(success=True, exists=True, size=100)):
            assert not converter.validate_conversion("output.md", "input.html") # Expect no errors

    # Test failure when output file doesn't exist
    fs_stub.get_file_info = lambda path: SimpleNamespace(
        success=True, exists="output" not in path, size=100, modified=time.time()
    )
    assert not converter.validate_conversion("output.md", "input.html")

    # Reset fs_stub
    fs_stub.get_file_info = lambda path: SimpleNamespace(
        success=True, exists=True, size=100, modified=time.time()
    )
