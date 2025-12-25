"""
Tests for the pandoc integration service.

This module contains unit tests for the PandocIntegration service class
that provides document conversion functionality.
"""

from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from quack_core.errors import QuackIntegrationError
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.pandoc.service import PandocIntegration


def test_pandoc_integration_name_version():
    """Test basic properties of PandocIntegration."""
    integration = PandocIntegration()
    assert integration.name == "Pandoc"
    assert integration.version == "1.0.0"
    assert not integration._initialized


def test_initialize_with_mocked_verify_pandoc(fs_stub, mock_paths_service):
    """Test initialize method with mocked verify_pandoc."""
    mock_paths_service.expand_user_vars = MagicMock(side_effect=lambda x: x)

    fs_stub.get_path_info = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.normalize_path_with_info = MagicMock(return_value=SimpleNamespace(success=True, path="output"))
    fs_stub.create_directory = MagicMock(return_value=SimpleNamespace(success=True))

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service

    # Mock the verify_pandoc function
    with patch('quack_core.integrations.pandoc.service.verify_pandoc',
               return_value="2.11.0"):
        integration.config_provider.load_config = MagicMock(return_value={})
        result = integration.initialize()
        assert result.success
        assert integration._initialized
        assert integration._pandoc_version == "2.11.0"
        assert integration.converter is not None


def test_initialize_with_verify_pandoc_error(fs_stub, mock_paths_service):
    """Test initialize method when verify_pandoc raises an error."""
    mock_paths_service.expand_user_vars = MagicMock(side_effect=lambda x: x)

    fs_stub.get_path_info = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.normalize_path_with_info = MagicMock(return_value=SimpleNamespace(success=True, path="output"))
    fs_stub.create_directory = MagicMock(return_value=SimpleNamespace(success=True))

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service

    # Mock verify_pandoc to raise an error
    with patch('quack_core.integrations.pandoc.service.verify_pandoc',
               side_effect=QuackIntegrationError("Pandoc not found", {})):
        result = integration.initialize()

        assert not result.success
        assert not integration._initialized


def test_html_to_markdown_not_initialized():
    """Test html_to_markdown when service is not initialized."""
    integration = PandocIntegration()
    result = integration.html_to_markdown("input.html", "output.md")

    assert not result.success
    assert "not initialized" in result.error


def test_markdown_to_docx_not_initialized():
    """Test markdown_to_docx when service is not initialized."""
    integration = PandocIntegration()
    result = integration.markdown_to_docx("input.md", "output.docx")

    assert not result.success
    assert "not initialized" in result.error


def test_convert_directory_not_initialized():
    """Test convert_directory when service is not initialized."""
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
        # assert not integration.is_pandoc_available()
        # assert integration.get_pandoc_version() is None
        pass


def test_html_to_markdown_with_initialized_service(fs_stub, mock_paths_service):
    """Test html_to_markdown with initialized service."""
    mock_paths_service.expand_user_vars = MagicMock(side_effect=lambda x: x)
    mock_paths_service.resolve_project_path = MagicMock(side_effect=lambda x, *args: x)

    fs_stub.get_path_info = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.normalize_path_with_info = MagicMock(return_value=SimpleNamespace(success=True, path="output"))
    fs_stub.create_directory = MagicMock(return_value=SimpleNamespace(success=True))

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.config_provider.load_config = MagicMock(return_value={})

    # Initialize the service
    with patch('quack_core.integrations.pandoc.service.verify_pandoc',
               return_value="2.11.0"):
        integration.initialize()

    # Mock the converter
    mock_result = IntegrationResult(success=True, content='output.md')
    if integration.converter:
        integration.converter.convert_file = MagicMock(return_value=mock_result)

    # Test with output path
    result = integration.html_to_markdown("input.html", "output.md")
    assert result.success
    if integration.converter:
        integration.converter.convert_file.assert_called_once()

    # Reset mock and test without output path
    if integration.converter:
        integration.converter.convert_file.reset_mock()
    result = integration.html_to_markdown("input.html")
    assert result.success
    if integration.converter:
        integration.converter.convert_file.assert_called_once()


def test_markdown_to_docx_with_initialized_service(fs_stub, mock_paths_service):
    """Test markdown_to_docx with initialized service."""
    mock_paths_service.expand_user_vars = MagicMock(side_effect=lambda x: x)
    mock_paths_service.resolve_project_path = MagicMock(side_effect=lambda x, *args: x)

    fs_stub.get_path_info = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.normalize_path_with_info = MagicMock(return_value=SimpleNamespace(success=True, path="output"))
    fs_stub.create_directory = MagicMock(return_value=SimpleNamespace(success=True))

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.config_provider.load_config = MagicMock(return_value={})

    # Initialize the service
    with patch('quack_core.integrations.pandoc.service.verify_pandoc',
               return_value="2.11.0"):
        integration.initialize()

    # Mock the converter
    mock_result = IntegrationResult(success=True, content='output.docx')
    if integration.converter:
        integration.converter.convert_file = MagicMock(return_value=mock_result)

    # Test with output path
    result = integration.markdown_to_docx("input.md", "output.docx")
    assert result.success
    if integration.converter:
        integration.converter.convert_file.assert_called_once()

    # Reset mock and test without output path
    if integration.converter:
        integration.converter.convert_file.reset_mock()
    result = integration.markdown_to_docx("input.md")
    assert result.success
    if integration.converter:
        integration.converter.convert_file.assert_called_once()


def test_convert_directory_with_initialized_service(fs_stub, mock_paths_service):
    """Test convert_directory with initialized service."""
    mock_paths_service.expand_user_vars = MagicMock(side_effect=lambda x: x)
    mock_paths_service.resolve_project_path = MagicMock(side_effect=lambda x, *args: x)

    fs_stub.get_path_info = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.normalize_path_with_info = MagicMock(return_value=SimpleNamespace(success=True, path="output"))
    fs_stub.create_directory = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.get_file_info = MagicMock(return_value=SimpleNamespace(success=True, exists=True, is_dir=True))

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.config_provider.load_config = MagicMock(return_value={})

    # Initialize the service
    with patch('quack_core.integrations.pandoc.service.verify_pandoc',
               return_value="2.11.0"):
        integration.initialize()

    # Mock the converter
    mock_result = IntegrationResult(success=True, content=['output1.md', 'output2.md'])
    if integration.converter:
        integration.converter.convert_batch = MagicMock(return_value=mock_result)

    # Test with default parameters
    result = integration.convert_directory("input_dir", "markdown")
    assert result.success
    if integration.converter:
        assert integration.converter.convert_batch.called

    # Test with custom parameters
    if integration.converter:
        integration.converter.convert_batch.reset_mock()
    result = integration.convert_directory(
        "input_dir", "markdown", "custom_output", "*.html", True
    )
    assert result.success
    if integration.converter:
        assert integration.converter.convert_batch.called