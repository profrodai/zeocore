# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/pandoc/test_service.py
# role: tests
# neighbors: __init__.py, conftest.py, mocks.py, test-pandoc-integration-full.py, test_config.py, test_converter.py (+4 more)
# exports: setup_mocks, test_pandoc_integration_name_version, test_initialize_with_mocked_verify_pandoc, test_initialize_with_verify_pandoc_error, test_html_to_markdown_not_initialized, test_markdown_to_docx_not_initialized, test_convert_directory_not_initialized, test_is_pandoc_available (+3 more)
# git_branch: refactor/newHeaders
# git_commit: bd13631
# === QV-LLM:END ===

"""
Tests for the pandoc integration service.

This module contains unit tests for the PandocIntegration service class
that provides document conversion functionality.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from quack_core.lib.errors import QuackIntegrationError
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.pandoc.service import PandocIntegration


@pytest.fixture
def setup_mocks(fs_stub, mock_paths_service):
    """Shared setup for service tests."""
    if not isinstance(mock_paths_service, MagicMock):
        mock_paths_service = MagicMock()

    mock_paths_service.expand_user_vars = MagicMock(side_effect=lambda x: x)
    mock_paths_service.resolve_project_path = MagicMock(
        side_effect=lambda x: SimpleNamespace(success=True, path=x)
    )

    # Setup fs_stub methods
    fs_stub.get_path_info = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.normalize_path_with_info = MagicMock(
        return_value=SimpleNamespace(success=True, path="output")
    )
    fs_stub.create_directory = MagicMock(return_value=SimpleNamespace(success=True))
    # Fix for expand_user_vars missing
    fs_stub.expand_user_vars = MagicMock(
        side_effect=lambda x: SimpleNamespace(success=True, data=x)
    )
    # Ensure find_files exists
    fs_stub.find_files = MagicMock(
        return_value=SimpleNamespace(success=True, files=[])
    )
    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=False, size=100)
    )

    return fs_stub, mock_paths_service


def test_pandoc_integration_name_version():
    """Test basic properties of PandocIntegration."""
    integration = PandocIntegration()
    assert integration.name == "Pandoc"
    assert integration.version == "1.0.0"
    assert not integration._initialized


@patch('quack_core.lib.fs.service.standalone.expand_user_vars')
@patch('quack_core.integrations.pandoc.service.verify_pandoc')
def test_initialize_with_mocked_verify_pandoc(mock_verify_pandoc, mock_expand_user_vars, setup_mocks):
    """Test initialize method with mocked verify_pandoc."""
    fs_stub, mock_paths_service = setup_mocks

    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub
    integration.config_provider.load_config = MagicMock(
        return_value=IntegrationResult(success=True, content={})
    )

    result = integration.initialize()

    assert result.success
    assert integration._initialized
    assert integration._pandoc_version == "2.11.0"
    assert integration.converter is not None


@patch('quack_core.integrations.pandoc.service.verify_pandoc')
def test_initialize_with_verify_pandoc_error(mock_verify_pandoc, setup_mocks):
    """Test initialize method when verify_pandoc raises an error."""
    fs_stub, mock_paths_service = setup_mocks

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    # We must assign fs_service for initialization cleanup/logic even if it fails early
    integration.fs_service = fs_stub

    # Mock verify_pandoc to raise an error
    mock_verify_pandoc.side_effect = QuackIntegrationError("Pandoc not found", {})

    result = integration.initialize()

    assert not result.success
    assert not integration._initialized


def test_html_to_markdown_not_initialized():
    """Test HTML to Markdown conversion when service is not initialized."""
    integration = PandocIntegration()
    result = integration.html_to_markdown("input.html", "output.md")

    assert not result.success
    assert "not initialized" in result.error


def test_markdown_to_docx_not_initialized():
    """Test Markdown to DOCX conversion when service is not initialized."""
    integration = PandocIntegration()
    result = integration.markdown_to_docx("input.md", "output.docx")

    assert not result.success
    assert "not initialized" in result.error


def test_convert_directory_not_initialized():
    """Test directory conversion when service is not initialized."""
    integration = PandocIntegration()
    result = integration.convert_directory("input_dir", "markdown")

    assert not result.success
    assert "not initialized" in result.error


def test_is_pandoc_available():
    """Test is_pandoc_available method."""
    integration = PandocIntegration()

    # Mock verify_pandoc to succeed
    with patch('quack_core.integrations.pandoc.service.verify_pandoc',
               return_value="2.11.0"):
        assert integration.is_pandoc_available()
        assert integration.get_pandoc_version() == "2.11.0"

    # Mock verify_pandoc to fail
    with patch('quack_core.integrations.pandoc.service.verify_pandoc',
               side_effect=QuackIntegrationError("Pandoc not found", {})):
        assert not integration.is_pandoc_available()


@patch('quack_core.lib.fs.service.standalone.expand_user_vars')
@patch('quack_core.integrations.pandoc.service.verify_pandoc')
def test_html_to_markdown_with_initialized_service(mock_verify_pandoc, mock_expand_user_vars, setup_mocks):
    """Test HTML to Markdown conversion with initialized service."""
    fs_stub, mock_paths_service = setup_mocks

    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub
    integration.config_provider.load_config = MagicMock(
        return_value=IntegrationResult(success=True, content={})
    )

    # Initialize the service
    integration.initialize()

    # Mock the converter
    mock_result = IntegrationResult(success=True, content='output.md')
    mock_convert_file = MagicMock(return_value=mock_result)

    assert integration.converter is not None
    integration.converter.convert_file = mock_convert_file

    # Test with output path
    result = integration.html_to_markdown("input.html", "output.md")
    assert result.success
    assert mock_convert_file.call_count == 1

    # Test without output path
    result = integration.html_to_markdown("input.html")
    assert result.success
    assert mock_convert_file.call_count == 2


@patch('quack_core.lib.fs.service.standalone.expand_user_vars')
@patch('quack_core.integrations.pandoc.service.verify_pandoc')
def test_markdown_to_docx_with_initialized_service(mock_verify_pandoc, mock_expand_user_vars, setup_mocks):
    """Test Markdown to DOCX conversion with initialized service."""
    fs_stub, mock_paths_service = setup_mocks

    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub
    integration.config_provider.load_config = MagicMock(
        return_value=IntegrationResult(success=True, content={})
    )

    # Initialize the service
    integration.initialize()

    # Mock the converter
    mock_result = IntegrationResult(success=True, content='output.docx')
    mock_convert_file = MagicMock(return_value=mock_result)

    assert integration.converter is not None
    integration.converter.convert_file = mock_convert_file

    # Test with output path
    result = integration.markdown_to_docx("input.md", "output.docx")
    assert result.success
    assert mock_convert_file.call_count == 1

    # Test without output path
    result = integration.markdown_to_docx("input.md")
    assert result.success
    assert mock_convert_file.call_count == 2


@patch('quack_core.lib.fs.service.standalone.expand_user_vars')
@patch('quack_core.integrations.pandoc.service.verify_pandoc')
def test_convert_directory_with_initialized_service(mock_verify_pandoc, mock_expand_user_vars, setup_mocks):
    """Test directory conversion with initialized service."""
    fs_stub, mock_paths_service = setup_mocks

    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub
    integration.config_provider.load_config = MagicMock(
        return_value=IntegrationResult(success=True, content={})
    )

    # Add directory-specific mocks to fs_service
    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=True)
    )
    fs_stub.find_files = MagicMock(
        return_value=SimpleNamespace(success=True, files=["file1.html", "file2.html"])
    )

    # Initialize the service
    integration.initialize()

    # Mock the converter
    mock_result = IntegrationResult(success=True, content=['output1.md', 'output2.md'])
    mock_convert_batch = MagicMock(return_value=mock_result)

    assert integration.converter is not None
    integration.converter.convert_batch = mock_convert_batch

    # Test with default parameters
    result = integration.convert_directory("input_dir", "markdown")
    assert result.success
    assert mock_convert_batch.call_count == 1

    # Test with custom parameters
    result = integration.convert_directory(
        "input_dir", "markdown", "custom_output", "*.html"
    )
    assert result.success
    assert mock_convert_batch.call_count == 2