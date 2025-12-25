# quack-core/tests/test_prompt/test_enhancer.py
"""
Tests for the prompt enhancer functionality.
"""

from unittest.mock import MagicMock, patch

import pytest

from quack_core.prompt.enhancer import (
    _create_system_prompt,
    _create_user_prompt,
    _load_config,
    count_prompt_tokens,
    enhance_with_llm,
)


@pytest.fixture
def mock_llm_integration_class():
    """Create a mock LLM integration class for testing."""
    # Create a mock for the LLMIntegration class
    mock_class = MagicMock()

    # Create a mock instance
    mock_instance = MagicMock()
    mock_instance.initialize.return_value = MagicMock(success=True)
    mock_instance.chat.return_value = MagicMock(
        success=True, content="Enhanced prompt content"
    )
    mock_instance.count_tokens.return_value = MagicMock(success=True, content=150)

    # Configure the mock class to return the mock instance
    mock_class.return_value = mock_instance

    return mock_class, mock_instance


@pytest.fixture
def mock_config():
    """Mock the configuration loading."""
    with patch("quack_core.prompt.enhancer._load_config") as mock_load:
        mock_load.return_value = {
            "llm": {
                "temperature": 0.3,
                "max_tokens": 1200,
                "top_p": 0.95,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
            },
            "system_prompt": {
                "prompt_engineer": "You are a prompt engineer. Rewrite {strategy}."
            },
        }

        yield mock_load


def test_load_config():
    """Test loading configuration for the enhancer."""
    # Create test data for the mock
    custom_config = {
        "llm": {"temperature": 0.4, "max_tokens": 2000},
        "system_prompt": {"prompt_engineer": "Custom prompt template"},
    }

    # Mock the configuration system - create mocks that match exactly what's used in the function
    config_mock = MagicMock()
    config_mock.get_custom.return_value = {}  # Empty custom config

    standalone_mock = MagicMock()
    standalone_mock.read_yaml.return_value = MagicMock(success=True, data=custom_config)

    # Direct patch without modifying internal implementation
    with (
        patch("quack_core.prompt.enhancer.quack_config", config_mock),
        patch("quack_core.prompt.enhancer.standalone", standalone_mock),
        patch.dict(
            "quack_core.prompt.enhancer.DEFAULT_CONFIG",
            {
                "llm": {
                    "temperature": 0.3,
                    "max_tokens": 1200,
                    "top_p": 0.95,
                    "frequency_penalty": 0.0,
                    "presence_penalty": 0.0,
                },
                "system_prompt": {"prompt_engineer": "Default template"},
            },
            clear=True,
        ),
    ):
        # Load configuration
        config = _load_config()

        # Check the merged configuration
        assert config["llm"]["temperature"] == 0.4  # From custom config
        assert config["llm"]["max_tokens"] == 2000  # From custom config
        assert config["llm"]["top_p"] == 0.95  # From default config
        assert (
            config["system_prompt"]["prompt_engineer"] == "Custom prompt template"
        )  # From custom config

def test_enhance_with_llm(mock_llm_integration_class, mock_config):
    """Test enhancing a prompt with an LLM."""
    mock_class, mock_instance = mock_llm_integration_class

    # Create mocks for all imported classes
    chat_message_mock = MagicMock()
    llm_options_mock = MagicMock()
    role_type_mock = MagicMock()

    # Save the original import functions
    original_import = __import__

    def mock_import(name, *args, **kwargs):
        if name == "quack_core.integrations.llms.service":
            module = MagicMock()
            module.LLMIntegration = mock_class
            return module
        elif name == "quack_core.integrations.llms.models":
            module = MagicMock()
            module.ChatMessage = chat_message_mock
            module.LLMOptions = llm_options_mock
            module.RoleType = role_type_mock
            return module
        return original_import(name, *args, **kwargs)

    # Patch __import__ to control imports inside the function
    with patch("builtins.__import__", side_effect=mock_import):
        # Call the function
        result = enhance_with_llm(
            task_description="Write a story about AI",
            schema='{"title": "string", "content": "string"}',
            examples=["Example 1", "Example 2"],
            strategy_name="test-strategy",
            model="gpt-4",
            provider="openai",
        )

        # Check result
        assert result == "Enhanced prompt content"

        # Verify the LLM service was initialized and called correctly
        mock_instance.initialize.assert_called_once()
        mock_instance.chat.assert_called_once()


def test_enhance_with_llm_init_failure(mock_llm_integration_class, mock_config):
    """Test enhancing a prompt when LLM initialization fails."""
    mock_class, mock_instance = mock_llm_integration_class

    # Configure the mock to simulate initialization failure
    mock_instance.initialize.return_value = MagicMock(
        success=False, error="Initialization failed"
    )

    # Create mocks for all imported classes
    chat_message_mock = MagicMock()
    llm_options_mock = MagicMock()
    role_type_mock = MagicMock()

    # Generate a custom mock for the LLMIntegration
    llm_service_module = MagicMock()
    llm_service_module.LLMIntegration = mock_class

    llm_models_module = MagicMock()
    llm_models_module.ChatMessage = chat_message_mock
    llm_models_module.LLMOptions = llm_options_mock
    llm_models_module.RoleType = role_type_mock

    # Patch the specific imports used in the function
    with patch.dict(
        "sys.modules",
        {
            "quack_core.integrations.llms.service": llm_service_module,
            "quack_core.integrations.llms.models": llm_models_module,
        },
    ):
        # Call the function - it appears to return the original prompt
        # instead of raising an exception
        result = enhance_with_llm(task_description="Test prompt")

        # Verify the result is the original prompt
        assert result == "Test prompt"

        # Verify initialize was called
        mock_instance.initialize.assert_called_once()

        # Verify chat was not called
        mock_instance.chat.assert_not_called()


def test_enhance_with_llm_chat_failure(mock_llm_integration_class, mock_config):
    """Test enhancing a prompt when the LLM chat fails."""
    mock_class, mock_instance = mock_llm_integration_class

    # Configure the mock to simulate chat failure
    mock_instance.chat.return_value = MagicMock(success=False, error="Chat failed")

    # Create mocks for all imported classes
    chat_message_mock = MagicMock()
    llm_options_mock = MagicMock()
    role_type_mock = MagicMock()

    # Save the original import functions
    original_import = __import__

    def mock_import(name, *args, **kwargs):
        if name == "quack_core.integrations.llms.service":
            module = MagicMock()
            module.LLMIntegration = mock_class
            return module
        elif name == "quack_core.integrations.llms.models":
            module = MagicMock()
            module.ChatMessage = chat_message_mock
            module.LLMOptions = llm_options_mock
            module.RoleType = role_type_mock
            return module
        return original_import(name, *args, **kwargs)

    # Patch __import__ to control imports inside the function
    with patch("builtins.__import__", side_effect=mock_import):
        # Call the function
        result = enhance_with_llm(task_description="Test prompt")

        # Should return the original prompt on failure
        assert result == "Test prompt"


def test_enhance_with_llm_empty_response(mock_llm_integration_class, mock_config):
    """Test enhancing a prompt when the LLM returns an empty response."""
    mock_class, mock_instance = mock_llm_integration_class

    # Configure the mock to return an empty response
    mock_instance.chat.return_value = MagicMock(success=True, content="")

    # Create mocks for all imported classes
    chat_message_mock = MagicMock()
    llm_options_mock = MagicMock()
    role_type_mock = MagicMock()

    # Save the original import functions
    original_import = __import__

    def mock_import(name, *args, **kwargs):
        if name == "quack_core.integrations.llms.service":
            module = MagicMock()
            module.LLMIntegration = mock_class
            return module
        elif name == "quack_core.integrations.llms.models":
            module = MagicMock()
            module.ChatMessage = chat_message_mock
            module.LLMOptions = llm_options_mock
            module.RoleType = role_type_mock
            return module
        return original_import(name, *args, **kwargs)

    # Patch __import__ to control imports inside the function
    with patch("builtins.__import__", side_effect=mock_import):
        # Call the function
        result = enhance_with_llm(task_description="Original prompt")

        # Should return the original prompt if LLM returns empty
        assert result == "Original prompt"


def test_enhance_with_llm_import_error(mock_config):
    """Test enhancing a prompt when LLM modules can't be imported."""
    # Save the original import function
    original_import = __import__

    def mock_import(name, *args, **kwargs):
        if name == "quack_core.integrations.llms.models":
            raise ImportError("Test error")
        return original_import(name, *args, **kwargs)

    # Patch __import__ to simulate ImportError
    with (
        patch("builtins.__import__", side_effect=mock_import),
        pytest.raises(ImportError, match="LLM integration is not properly configured"),
    ):
        # Call the function - should raise ImportError
        enhance_with_llm(task_description="Test prompt")


def test_count_prompt_tokens(mock_llm_integration_class):
    """Test counting tokens in a prompt."""
    mock_class, mock_instance = mock_llm_integration_class

    # Create mocks for all imported classes
    chat_message_mock = MagicMock()
    role_type_mock = MagicMock()

    # Save the original import functions
    original_import = __import__

    def mock_import(name, *args, **kwargs):
        if name == "quack_core.integrations.llms.service":
            module = MagicMock()
            module.LLMIntegration = mock_class
            return module
        elif name == "quack_core.integrations.llms.models":
            module = MagicMock()
            module.ChatMessage = chat_message_mock
            module.RoleType = role_type_mock
            return module
        return original_import(name, *args, **kwargs)

    # Patch __import__ to control imports inside the function
    with (
        patch("builtins.__import__", side_effect=mock_import),
        patch("quack_core.prompt.enhancer._load_config") as mock_load_config,
    ):
        # Configure mocks
        mock_load_config.return_value = {
            "llm": {},
            "system_prompt": {
                "prompt_engineer": "You are a prompt engineer. Rewrite {strategy}."
            },
        }

        # Call the function
        count = count_prompt_tokens(
            task_description="Test prompt",
            schema='{"test": "schema"}',
            examples=["Example"],
            strategy_name="test-strategy",
        )

        # Check result
        assert count == 150

        # Verify the LLM service was initialized and called correctly
        mock_instance.initialize.assert_called_once()
        mock_instance.count_tokens.assert_called_once()


def test_count_prompt_tokens_failure(mock_llm_integration_class):
    """Test counting tokens when the LLM service fails."""
    mock_class, mock_instance = mock_llm_integration_class

    # Configure the mock to fail
    mock_instance.count_tokens.return_value = MagicMock(
        success=False, error="Count failed"
    )

    # Create mocks for all imported classes
    chat_message_mock = MagicMock()
    role_type_mock = MagicMock()

    # Save the original import functions
    original_import = __import__

    def mock_import(name, *args, **kwargs):
        if name == "quack_core.integrations.llms.service":
            module = MagicMock()
            module.LLMIntegration = mock_class
            return module
        elif name == "quack_core.integrations.llms.models":
            module = MagicMock()
            module.ChatMessage = chat_message_mock
            module.RoleType = role_type_mock
            return module
        return original_import(name, *args, **kwargs)

    # Patch __import__ to control imports inside the function
    with (
        patch("builtins.__import__", side_effect=mock_import),
        patch("quack_core.prompt.enhancer._load_config") as mock_load_config,
    ):
        # Configure mocks
        mock_load_config.return_value = {"llm": {}, "system_prompt": {}}

        # Call the function
        count = count_prompt_tokens(task_description="Test prompt")

        # Should return None on failure
        assert count is None


def test_create_system_prompt():
    """Test creating a system prompt from configuration."""
    # Create a test config
    config = {
        "system_prompt": {
            "prompt_engineer": "You are a prompt engineer. Fix {strategy}."
        }
    }

    # Create a system prompt without strategy name
    prompt1 = _create_system_prompt(None, config)
    assert prompt1 == "You are a prompt engineer. Fix ."

    # Create a system prompt with strategy name
    prompt2 = _create_system_prompt("test-strategy", config)
    assert (
        prompt2 == "You are a prompt engineer. Fix using the 'test-strategy' strategy."
    )


def test_create_user_prompt():
    """Test creating a user prompt from inputs."""
    # Test with just a task description
    prompt1 = _create_user_prompt("Do a task", None, None)
    assert prompt1 == "TASK:\nDo a task"

    # Test with schema
    prompt2 = _create_user_prompt("Do a task", '{"field": "type"}', None)
    assert prompt2 == 'TASK:\nDo a task\n\nSCHEMA:\n{"field": "type"}'

    # Test with examples as a list
    prompt3 = _create_user_prompt("Do a task", None, ["Example 1", "Example 2"])
    assert prompt3 == "TASK:\nDo a task\n\nEXAMPLES:\nExample 1\n\nExample 2"

    # Test with examples as a string
    prompt4 = _create_user_prompt("Do a task", None, "Single example")
    assert prompt4 == "TASK:\nDo a task\n\nEXAMPLES:\nSingle example"

    # Test with all components
    prompt5 = _create_user_prompt(
        "Do a task", '{"field": "type"}', ["Example 1", "Example 2"]
    )
    assert (
        prompt5
        == 'TASK:\nDo a task\n\nSCHEMA:\n{"field": "type"}\n\nEXAMPLES:\nExample 1\n\nExample 2'
    )
