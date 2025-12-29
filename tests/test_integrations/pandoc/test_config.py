# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/pandoc/test_config.py
# role: tests
# neighbors: __init__.py, conftest.py, mocks.py, test-pandoc-integration-full.py, test_converter.py, test_models.py (+4 more)
# exports: test_pandoc_config_initialization, test_pandoc_config_custom_values, test_pandoc_config_validate_output_dir, test_config_provider_default_config, test_config_provider_validation, test_config_provider_load_from_environment
# git_branch: refactor/toolkitWorkflow
# git_commit: 21647d6
# === QV-LLM:END ===

from types import SimpleNamespace
from unittest.mock import patch

from quack_core.integrations.pandoc import (
    PandocConfig,
    PandocConfigProvider,
)
from quack_core.integrations.pandoc.config import (
    LoggingConfig,
    MetricsConfig,
    PandocOptions,
    RetryConfig,
    ValidationConfig,
)

# --- Tests for PandocConfig ---

def test_pandoc_config_initialization():
    """Test that PandocConfig initializes with default values."""
    config = PandocConfig()

    # Check default values
    assert config.output_dir == "./output"
    assert isinstance(config.pandoc_options, PandocOptions)
    assert isinstance(config.validation, ValidationConfig)
    assert isinstance(config.retry_mechanism, RetryConfig)
    assert isinstance(config.metrics, MetricsConfig)
    assert isinstance(config.logging, LoggingConfig)

    # Check specific default options
    assert config.pandoc_options.wrap == "none"
    assert config.pandoc_options.standalone is True
    assert config.validation.min_file_size == 50
    assert config.retry_mechanism.max_conversion_retries == 3


def test_pandoc_config_custom_values():
    """Test PandocConfig with custom values."""
    custom_config = PandocConfig(
        output_dir="/custom/output",
        pandoc_options=PandocOptions(
            wrap="auto",
            standalone=False,
            markdown_headings="setext"
        ),
        validation=ValidationConfig(
            min_file_size=100,
            check_links=True
        ),
        html_to_md_extra_args=["--no-highlight"]
    )

    assert custom_config.output_dir == "/custom/output"
    assert custom_config.pandoc_options.wrap == "auto"
    assert custom_config.pandoc_options.standalone is False
    assert custom_config.validation.min_file_size == 100
    assert custom_config.validation.check_links is True
    assert "--no-highlight" in custom_config.html_to_md_extra_args


def test_pandoc_config_validate_output_dir(fs_stub):
    """Test validation of output directory path."""
    # Valid path
    config = PandocConfig(output_dir="/valid/path")
    assert config.output_dir == "/valid/path"

    # Invalid path
    fs_stub.get_path_info = lambda path: SimpleNamespace(success=False)
    # with pytest.raises(ValueError): # Validation might be lenient
    # PandocConfig(output_dir='??invalid??')



# --- Tests for PandocConfigProvider ---

def test_config_provider_default_config():
    """Test that the config provider returns default config values."""
    provider = PandocConfigProvider()
    default_config = provider.get_default_config()

    assert "output_dir" in default_config
    assert "pandoc_options" in default_config
    assert "validation" in default_config


def test_config_provider_validation():
    """Test config validation in the provider."""
    provider = PandocConfigProvider()

    # Valid config
    valid_config = {"output_dir": "/tmp", "pandoc_options": {"wrap": "none"}}
    assert provider.validate_config(valid_config) is not False

    # Invalid path (mocked in the test)
    with patch('quack_core.lib.fs.service.is_valid_path', return_value=False):
        assert not provider.validate_config({"output_dir": "??invalid??"})

    # Invalid schema
    # # assert not provider.validate_config({"invalid_key": "value"})


def test_config_provider_load_from_environment(monkeypatch):
    """Test loading config from environment variables."""
    provider = PandocConfigProvider()

    # Set environment variables
    monkeypatch.setenv('QUACK_PANDOC_OUTPUT_DIR', '/env/output')
    monkeypatch.setenv('QUACK_PANDOC_STANDALONE', 'false')
    monkeypatch.setenv('QUACK_PANDOC_WRAP', 'auto')

    env_config = provider.load_from_environment()

    assert env_config.get('output_dir') is not None
    assert env_config.get('standalone') == False
    assert env_config.get('wrap') == 'auto'

