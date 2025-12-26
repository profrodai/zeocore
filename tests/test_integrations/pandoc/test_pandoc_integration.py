# quack-core/tests/test_integrations/pandoc/test_pandoc_integration.py
"""
Tests for the main Pandoc integration service.

This module contains unit and integration tests for the PandocIntegration
class that provides document conversion functionality.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from quack_core.errors import QuackIntegrationError
from quack_core.integrations.core.protocols import IntegrationProtocol
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.pandoc import create_integration
from quack_core.integrations.pandoc.service import PandocIntegration
from quack_core.integrations.pandoc.models import FileInfo


# --- Shared Test Fixtures ---

@pytest.fixture
def setup_integration_mocks(fs_stub, mock_paths_service):
    """Shared setup for integration tests."""
    # Path service mocks
    if not isinstance(mock_paths_service, MagicMock):
        mock_paths_service = MagicMock()

    mock_paths_service.expand_user_vars = MagicMock(side_effect=lambda x: x)
    mock_paths_service.resolve_project_path = MagicMock(
        side_effect=lambda x: SimpleNamespace(success=True, path=x)
    )

    # Define return values for methods used in initialize() and operations
    fs_stub.get_path_info = MagicMock(
        return_value=SimpleNamespace(success=True)
    )
    fs_stub.normalize_path_with_info = MagicMock(
        return_value=SimpleNamespace(success=True, path="output")
    )
    fs_stub.create_directory = MagicMock(
        return_value=SimpleNamespace(success=True)
    )
    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=False, size=100)
    )
    fs_stub.expand_user_vars = MagicMock(
        side_effect=lambda x: SimpleNamespace(success=True, data=x)
    )
    fs_stub.find_files = MagicMock(
        return_value=SimpleNamespace(success=True, files=[])
    )

    return fs_stub, mock_paths_service


# --- Tests for PandocIntegration ---

def test_pandoc_integration_initialization():
    """Test initialization of PandocIntegration."""
    integration = PandocIntegration()

    assert integration.name == "Pandoc"
    assert integration.version == "1.0.0"
    assert integration._initialized is False
    assert integration.converter is None


@patch('quack_core.fs.service.standalone.expand_user_vars')
@patch('quack_core.integrations.pandoc.service.verify_pandoc')
def test_pandoc_integration_initialize_success(mock_verify_pandoc,
                                               mock_expand_user_vars,
                                               setup_integration_mocks):
    """Test successful initialization of PandocIntegration."""
    fs_stub, mock_paths_service = setup_integration_mocks

    # Set up the mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub
    integration.config_provider.load_config = MagicMock(
        return_value=IntegrationResult(success=True, content={})
    )

    result = integration.initialize()

    # Verify
    assert result.success
    assert integration._initialized is True
    assert integration._pandoc_version == "2.11.0"
    assert integration.converter is not None


@patch('quack_core.integrations.pandoc.service.verify_pandoc')
def test_pandoc_integration_initialize_failure(mock_verify_pandoc):
    """Test failed initialization of PandocIntegration."""
    # Set up the mock to raise an exception
    mock_verify_pandoc.side_effect = QuackIntegrationError("Pandoc not available", {})

    integration = PandocIntegration()
    result = integration.initialize()

    # Verify
    assert not result.success
    assert integration._initialized is False


@patch('quack_core.fs.service.standalone.expand_user_vars')
@patch('quack_core.integrations.pandoc.service.verify_pandoc')
def test_pandoc_integration_html_to_markdown(mock_verify_pandoc,
                                             mock_expand_user_vars,
                                             setup_integration_mocks):
    """Test HTML to Markdown conversion in PandocIntegration."""
    fs_stub, mock_paths_service = setup_integration_mocks

    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub
    integration.config_provider.load_config = MagicMock(
        return_value=IntegrationResult(success=True, content={})
    )

    # Initialize
    integration.initialize()

    # Mock converter
    mock_conv_result = IntegrationResult(success=True, content='output.md')
    mock_convert_file = MagicMock(return_value=mock_conv_result)

    assert integration.converter is not None
    integration.converter.convert_file = mock_convert_file

    # Run conversion
    result = integration.html_to_markdown("input.html")

    # Verify
    assert result.success
    mock_convert_file.assert_called()


@patch('quack_core.fs.service.standalone.expand_user_vars')
@patch('quack_core.integrations.pandoc.service.verify_pandoc')
def test_pandoc_integration_markdown_to_docx(mock_verify_pandoc,
                                             mock_expand_user_vars,
                                             setup_integration_mocks):
    """Test Markdown to DOCX conversion in PandocIntegration."""
    fs_stub, mock_paths_service = setup_integration_mocks

    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub
    integration.config_provider.load_config = MagicMock(
        return_value=IntegrationResult(success=True, content={})
    )

    # Initialize
    integration.initialize()

    # Mock converter
    mock_conv_result = IntegrationResult(success=True, content='output.docx')
    mock_convert_file = MagicMock(return_value=mock_conv_result)

    assert integration.converter is not None
    integration.converter.convert_file = mock_convert_file

    # Run conversion
    result = integration.markdown_to_docx("input.md")

    # Verify
    assert result.success
    mock_convert_file.assert_called()


@patch('quack_core.fs.service.standalone.expand_user_vars')
@patch('quack_core.integrations.pandoc.service.verify_pandoc')
def test_pandoc_integration_convert_directory(mock_verify_pandoc,
                                              mock_expand_user_vars,
                                              setup_integration_mocks):
    """Test directory conversion in PandocIntegration."""
    fs_stub, mock_paths_service = setup_integration_mocks

    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    # Add directory-specific mocks
    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=True)
    )
    fs_stub.find_files = MagicMock(
        return_value=SimpleNamespace(success=True, files=["file1.html", "file2.html"])
    )

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub
    integration.config_provider.load_config = MagicMock(
        return_value=IntegrationResult(success=True, content={})
    )

    # Initialize
    integration.initialize()

    # Mock converter
    mock_conv_result = IntegrationResult(
        success=True,
        content=['output1.md', 'output2.md']
    )
    mock_convert_batch = MagicMock(return_value=mock_conv_result)

    assert integration.converter is not None
    integration.converter.convert_batch = mock_convert_batch

    # Run conversion
    result = integration.convert_directory("input_dir", "markdown")

    # Verify
    assert result.success
    mock_convert_batch.assert_called()
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
        mock_class.assert_called()
        assert isinstance(integration, MagicMock)


# --- Integration tests ---

# We need to mock get_file_info from operations.utils because that's what the Converter uses
# to validate input files. It bypasses the fs_service we inject into the Integration.
@patch('quack_core.integrations.pandoc.operations.utils.get_file_info')
@patch('quack_core.fs.service.standalone.expand_user_vars')
@patch('quack_core.integrations.pandoc.service.verify_pandoc')
def test_end_to_end_html_to_markdown_conversion(mock_verify_pandoc,
                                                mock_expand_user_vars,
                                                mock_get_file_info,
                                                setup_integration_mocks):
    """Test complete HTML to Markdown conversion flow."""
    fs_stub, mock_paths_service = setup_integration_mocks

    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    # Mock get_file_info to return a valid FileInfo object
    mock_get_file_info.return_value = FileInfo(
        path="input.html",
        format="html",
        size=1024,
        modified=123456789.0
    )

    # Create integration
    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub
    integration.config_provider.load_config = MagicMock(
        return_value=IntegrationResult(success=True, content={})
    )

    # Initialize integration
    init_result = integration.initialize()
    assert init_result.success

    # Mock convert_html_to_markdown to return success
    with patch(
            'quack_core.integrations.pandoc.operations.html_to_md.convert_html_to_markdown'
    ) as mock_convert:
        mock_convert.return_value = IntegrationResult.success_result(
            ("output.md", MagicMock()),
            message="Success"
        )

        # Run conversion
        result = integration.html_to_markdown("input.html", "output.md")

        # Verify
        assert result.success
        mock_convert.assert_called()


@patch('quack_core.integrations.pandoc.operations.utils.get_file_info')
@patch('quack_core.fs.service.standalone.expand_user_vars')
@patch('quack_core.integrations.pandoc.service.verify_pandoc')
def test_end_to_end_markdown_to_docx_conversion(mock_verify_pandoc,
                                                mock_expand_user_vars,
                                                mock_get_file_info,
                                                setup_integration_mocks):
    """Test complete Markdown to DOCX conversion flow."""
    fs_stub, mock_paths_service = setup_integration_mocks

    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    # Mock get_file_info to return a valid FileInfo object
    mock_get_file_info.return_value = FileInfo(
        path="input.md",
        format="markdown",
        size=1024,
        modified=123456789.0
    )

    # Create integration
    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub
    integration.config_provider.load_config = MagicMock(
        return_value=IntegrationResult(success=True, content={})
    )

    # Initialize integration
    init_result = integration.initialize()
    assert init_result.success

    # Mock convert_markdown_to_docx to return success
    with patch(
            'quack_core.integrations.pandoc.operations.md_to_docx.convert_markdown_to_docx'
    ) as mock_convert:
        mock_convert.return_value = IntegrationResult.success_result(
            ("output.docx", MagicMock()),
            message="Success"
        )

        # Run conversion
        result = integration.markdown_to_docx("input.md", "output.docx")

        # Verify
        assert result.success
        mock_convert.assert_called()


@patch('quack_core.integrations.pandoc.operations.utils.get_file_info')
@patch('quack_core.fs.service.standalone.expand_user_vars')
@patch('quack_core.integrations.pandoc.service.verify_pandoc')
def test_end_to_end_directory_conversion(mock_verify_pandoc,
                                         mock_expand_user_vars,
                                         mock_get_file_info,
                                         setup_integration_mocks):
    """Test complete directory conversion flow."""
    fs_stub, mock_paths_service = setup_integration_mocks

    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    # Override with directory-specific mocks for the integration FS service
    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=True)
    )
    fs_stub.find_files = MagicMock(
        return_value=SimpleNamespace(success=True, files=["file1.html", "file2.html"])
    )

    # Mock operations.utils.get_file_info used by the Converter
    mock_get_file_info.side_effect = lambda path: FileInfo(
        path=path, format="html", size=100
    )

    # Create integration
    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub
    integration.config_provider.load_config = MagicMock(
        return_value=IntegrationResult(success=True, content={})
    )

    # Initialize integration
    init_result = integration.initialize()
    assert init_result.success

    # Mock converter batch operation
    mock_convert_batch = MagicMock(
        return_value=IntegrationResult.success_result(["out1.md", "out2.md"])
    )

    assert integration.converter is not None
    integration.converter.convert_batch = mock_convert_batch

    result = integration.convert_directory("input_dir", "markdown")

    # Verify
    assert result.success
    assert isinstance(result.content, list)
    mock_convert_batch.assert_called()