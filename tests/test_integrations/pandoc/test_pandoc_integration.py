# quack-core/tests/test_integrations/pandoc/test_pandoc_integration.py
"""
Tests for the main Pandoc integration service.

This module contains unit and integration tests for the PandocIntegration
class that provides document conversion functionality.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from quack_core.errors import QuackIntegrationError
from quack_core.integrations.core.protocols import IntegrationProtocol
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.pandoc import (
    create_integration,
)
from quack_core.integrations.pandoc.service import PandocIntegration


# --- Tests for PandocIntegration ---

def test_pandoc_integration_initialization():
    """Test initialization of PandocIntegration."""
    integration = PandocIntegration()

    assert integration.name == "Pandoc"
    assert integration.version == "1.0.0"
    assert integration._initialized is False
    assert integration.converter is None


@patch('quack_core.integrations.pandoc.service.verify_pandoc')
def test_pandoc_integration_initialize_success(mock_verify_pandoc, fs_stub,
                                               mock_paths_service):
    """Test successful initialization of PandocIntegration."""
    # Setup mocks
    mock_paths_service.expand_user_vars = MagicMock(side_effect=lambda x: x)

    fs_stub.get_path_info = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.normalize_path_with_info = MagicMock(
        return_value=SimpleNamespace(success=True, path="output"))
    fs_stub.create_directory = MagicMock(return_value=SimpleNamespace(success=True))

    # Set up the mock to return a version string
    mock_verify_pandoc.return_value = "2.11.0"

    integration = PandocIntegration()
    # Explicitly inject the mock to avoid SimpleNamespace issues from fixtures
    integration.paths_service = mock_paths_service

    result = integration.initialize()

    # Verify
    assert result.success
    assert integration._initialized is True
    assert integration._pandoc_version == "2.11.0"
    assert integration.converter is not None


@patch('quack_core.integrations.pandoc.service.verify_pandoc')
def test_pandoc_integration_initialize_failure(mock_verify_pandoc, mock_pypandoc):
    """Test failed initialization of PandocIntegration."""
    # Set up the mock to raise an exception
    mock_verify_pandoc.side_effect = QuackIntegrationError("Pandoc not available", {})

    integration = PandocIntegration()
    result = integration.initialize()

    # Verify
    assert not result.success
    assert integration._initialized is False


def test_pandoc_integration_html_to_markdown(mock_pypandoc, fs_stub,
                                             mock_paths_service):
    """Test HTML to Markdown conversion in PandocIntegration."""
    # Setup mocks
    mock_paths_service.expand_user_vars = MagicMock(side_effect=lambda x: x)
    mock_paths_service.resolve_project_path = MagicMock(side_effect=lambda x, *args: x)

    fs_stub.get_path_info = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.normalize_path_with_info = MagicMock(
        return_value=SimpleNamespace(success=True, path="output"))
    fs_stub.create_directory = MagicMock(return_value=SimpleNamespace(success=True))

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.config_provider.load_config = MagicMock(return_value={})

    # Initialize with mocked verify_pandoc
    with patch('quack_core.integrations.pandoc.service.verify_pandoc',
               return_value="2.11.0"):
        integration.initialize()

    # Mock converter
    mock_conv_result = IntegrationResult(success=True, content='output.md')

    if integration.converter:
        integration.converter.convert_file = MagicMock(return_value=mock_conv_result)

    # Run conversion
    result = integration.html_to_markdown("input.html")

    # Verify
    assert result.success
    if integration.converter:
        assert integration.converter.convert_file.called


def test_pandoc_integration_markdown_to_docx(mock_pypandoc, fs_stub,
                                             mock_paths_service):
    """Test Markdown to DOCX conversion in PandocIntegration."""
    # Setup mocks
    mock_paths_service.expand_user_vars = MagicMock(side_effect=lambda x: x)
    mock_paths_service.resolve_project_path = MagicMock(side_effect=lambda x, *args: x)

    fs_stub.get_path_info = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.normalize_path_with_info = MagicMock(
        return_value=SimpleNamespace(success=True, path="output"))
    fs_stub.create_directory = MagicMock(return_value=SimpleNamespace(success=True))

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.config_provider.load_config = MagicMock(return_value={})

    # Initialize with mocked verify_pandoc
    with patch('quack_core.integrations.pandoc.service.verify_pandoc',
               return_value="2.11.0"):
        integration.initialize()

    # Mock converter
    mock_conv_result = IntegrationResult(success=True, content='output.docx')
    if integration.converter:
        integration.converter.convert_file = MagicMock(return_value=mock_conv_result)

    # Run conversion
    result = integration.markdown_to_docx("input.md")

    # Verify
    assert result.success
    if integration.converter:
        assert integration.converter.convert_file.called


def test_pandoc_integration_convert_directory(mock_pypandoc, fs_stub,
                                              mock_paths_service):
    """Test directory conversion in PandocIntegration."""
    # Setup mocks
    mock_paths_service.expand_user_vars = MagicMock(side_effect=lambda x: x)
    mock_paths_service.resolve_project_path = MagicMock(side_effect=lambda x, *args: x)

    fs_stub.get_path_info = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.normalize_path_with_info = MagicMock(
        return_value=SimpleNamespace(success=True, path="output"))
    fs_stub.create_directory = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=True))

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.config_provider.load_config = MagicMock(return_value={})

    # Initialize with mocked verify_pandoc
    with patch('quack_core.integrations.pandoc.service.verify_pandoc',
               return_value="2.11.0"):
        integration.initialize()

    # Mock converter
    mock_conv_result = IntegrationResult(success=True,
                                         content=['output1.md', 'output2.md'])
    if integration.converter:
        integration.converter.convert_batch = MagicMock(return_value=mock_conv_result)

    # Run conversion
    result = integration.convert_directory("input_dir", "markdown")

    # Verify
    assert result.success
    if integration.converter:
        assert integration.converter.convert_batch.called
    assert len(result.content) == 2


def test_pandoc_integration_not_initialized():
    """Test operations when integration is not initialized."""
    integration = PandocIntegration()

    # Try operations without initialization
    html_result = integration.html_to_markdown("input.html")
    md_result = integration.markdown_to_docx("input.md")
    dir_result = integration.convert_directory("input_dir", "markdown")

    # Verify all fail with appropriate error
    assert not html_result.success
    assert not md_result.success
    assert not dir_result.success
    assert "not initialized" in html_result.error
    assert "not initialized" in md_result.error
    assert "not initialized" in dir_result.error


def test_pandoc_integration_is_available():
    """Test checking if pandoc is available."""
    integration = PandocIntegration()

    # Mock verify_pandoc to succeed
    with patch('quack_core.integrations.pandoc.service.verify_pandoc',
               return_value="2.11.0"):
        assert integration.is_pandoc_available()
        assert integration.get_pandoc_version() == "2.11.0"

    # Clear any cached version before testing the failure case
    integration._pandoc_version = None

    # Mock verify_pandoc to fail
    with patch('quack_core.integrations.pandoc.service.verify_pandoc',
               side_effect=QuackIntegrationError("Pandoc not available", {})):
        assert not integration.is_pandoc_available()
        assert integration.get_pandoc_version() is None


def test_create_integration():
    """Test the factory function for creating the integration."""
    with patch('quack_core.integrations.pandoc.PandocIntegration') as mock_class:
        mock_class.return_value = MagicMock(spec=IntegrationProtocol)

        # Call factory function
        integration = create_integration()

        # Verify
        assert mock_class.called
        assert isinstance(integration, MagicMock)


# --- Integration tests ---

def test_end_to_end_html_to_markdown_conversion(mock_pypandoc, fs_stub,
                                                mock_paths_service):
    """Test complete HTML to Markdown conversion flow."""
    # Setup mocks
    mock_paths_service.expand_user_vars = MagicMock(side_effect=lambda x: x)
    mock_paths_service.resolve_project_path = MagicMock(side_effect=lambda x, *args: x)

    fs_stub.get_path_info = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.normalize_path_with_info = MagicMock(
        return_value=SimpleNamespace(success=True, path="output"))
    fs_stub.create_directory = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=False, size=100))

    # Create integration
    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.config_provider.load_config = MagicMock(return_value={})

    # Initialize integration with mocked verify_pandoc
    with patch('quack_core.integrations.pandoc.service.verify_pandoc',
               return_value="2.11.0"):
        init_result = integration.initialize()
        assert init_result.success

    # Mock convert_html_to_markdown to return success
    with patch(
            'quack_core.integrations.pandoc.operations.html_to_md.convert_html_to_markdown') as mock_convert:
        mock_convert.return_value = IntegrationResult.success_result(
            ("output.md", MagicMock()),
            message="Success"
        )

        # Run conversion
        result = integration.html_to_markdown("input.html", "output.md")

        # Verify
        assert result.success
        assert mock_convert.called


def test_end_to_end_markdown_to_docx_conversion(mock_pypandoc, fs_stub,
                                                mock_paths_service):
    """Test complete Markdown to DOCX conversion flow."""
    # Setup mocks
    mock_paths_service.expand_user_vars = MagicMock(side_effect=lambda x: x)
    mock_paths_service.resolve_project_path = MagicMock(side_effect=lambda x, *args: x)

    fs_stub.get_path_info = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.normalize_path_with_info = MagicMock(
        return_value=SimpleNamespace(success=True, path="output"))
    fs_stub.create_directory = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=False, size=100))

    # Create integration
    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.config_provider.load_config = MagicMock(return_value={})

    # Initialize integration with mocked verify_pandoc
    with patch('quack_core.integrations.pandoc.service.verify_pandoc',
               return_value="2.11.0"):
        init_result = integration.initialize()
        assert init_result.success

    # Mock convert_markdown_to_docx to return success
    with patch(
            'quack_core.integrations.pandoc.operations.md_to_docx.convert_markdown_to_docx') as mock_convert:
        mock_convert.return_value = IntegrationResult.success_result(
            ("output.docx", MagicMock()),
            message="Success"
        )

        # Run conversion
        result = integration.markdown_to_docx("input.md", "output.docx")

        # Verify
        assert result.success
        assert mock_convert.called


def test_end_to_end_directory_conversion(mock_pypandoc, fs_stub, mock_paths_service):
    """Test complete directory conversion flow."""
    # Setup mocks
    mock_paths_service.expand_user_vars = MagicMock(side_effect=lambda x: x)
    mock_paths_service.resolve_project_path = MagicMock(side_effect=lambda x, *args: x)

    fs_stub.get_path_info = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.normalize_path_with_info = MagicMock(
        return_value=SimpleNamespace(success=True, path="output"))
    fs_stub.create_directory = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=True))

    # Create integration
    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.config_provider.load_config = MagicMock(return_value={})

    # Initialize integration with mocked verify_pandoc
    with patch('quack_core.integrations.pandoc.service.verify_pandoc',
               return_value="2.11.0"):
        init_result = integration.initialize()
        assert init_result.success

    # Run conversion with mocked file system
    if integration.converter:
        with patch.object(integration.converter, 'convert_batch',
                          return_value=IntegrationResult.success_result(
                              ["out1.md", "out2.md"])):
            result = integration.convert_directory("input_dir", "markdown")

            # Verify
            assert result.success
            assert isinstance(result.content, list)