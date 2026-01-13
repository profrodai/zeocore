# QuackCore LLM Integration Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [Overview of `quack_core.integrations.llms`](#overview-of-quackcoreintegrationsllms)
3. [Getting Started](#getting-started)
   - [Installation](#installation)
   - [Basic Usage](#basic-usage)
4. [LLM Integration Service](#llm-integration-service)
   - [Initializing the Service](#initializing-the-service)
   - [Working with Different Providers](#working-with-different-providers)
   - [Handling Fallbacks](#handling-fallbacks)
5. [LLM Clients](#llm-clients)
   - [OpenAI Client](#openai-client)
   - [Anthropic Client](#anthropic-client)
   - [Ollama Client](#ollama-client)
   - [Mock Client](#mock-client)
6. [Chat Messages and Configuration](#chat-messages-and-configuration)
   - [Creating Chat Messages](#creating-chat-messages)
   - [LLM Options](#llm-options)
7. [Configuration](#configuration)
   - [Configuration Files](#configuration-files)
   - [Environment Variables](#environment-variables)
8. [Advanced Features](#advanced-features)
   - [Token Counting](#token-counting)
   - [Streaming Responses](#streaming-responses)
   - [Using Function and Tool Calls](#using-function-and-tool-calls)
   - [Provider Registry](#provider-registry)
   - [Fallback Strategies](#fallback-strategies)
9. [Error Handling](#error-handling)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)
12. [API Reference](#api-reference)

## Introduction

The `quack_core.integrations.llms` module provides a standardized interface for interacting with various Large Language Model (LLM) providers. It's designed to be easy to use while offering advanced capabilities like provider fallbacks, streaming responses, and token counting.

This module is an essential component for QuackTool developers who need to incorporate LLM capabilities into their applications. It abstracts away the complexities of dealing with different LLM APIs, allowing you to focus on building your tools rather than wrestling with integration details.

## Overview of `quack_core.integrations.llms`

The module consists of several key components:

- **Integration Service**: The main entry point for using LLMs
- **LLM Clients**: Provider-specific implementations (OpenAI, Anthropic, Ollama)
- **Models**: Data structures for messages, options, and responses
- **Configuration**: Tools for loading and managing configuration
- **Fallback Mechanism**: Graceful degradation when primary providers fail

The design follows a clean hierarchical structure, with common functionality abstracted into base classes and provider-specific implementations encapsulated in their own classes.

## Getting Started

### Installation

The `quack_core.integrations.llms` module is part of the QuackCore library. You should have it already installed if you're developing a QuackTool. If not, you can install it via pip:

```bash
pip install quack-core
```

To use specific LLM providers, you'll need to install their Python clients:

```bash
# For OpenAI
pip install openai

# For Anthropic
pip install anthropic

# For Ollama (requires the requests package)
pip install requests
```

### Basic Usage

Here's a simple example to get started with the LLM integration:

```python
from quack_core.integrations.llms import LLMIntegration, ChatMessage, RoleType, LLMOptions

# Initialize the LLM integration service
llm_service = LLMIntegration()
init_result = llm_service.initialize()

if not init_result.success:
    print(f"Failed to initialize LLM service: {init_result.error}")
    exit(1)

# Create a list of messages for the conversation
messages = [
    ChatMessage(role=RoleType.SYSTEM, content="You are a helpful assistant."),
    ChatMessage(role=RoleType.USER, content="What is the capital of France?")
]

# Send the chat request
result = llm_service.chat(messages)

if result.success:
    print(f"AI response: {result.content}")
else:
    print(f"Error: {result.error}")
```

This example initializes the LLM service with default settings, creates a conversation with system and user messages, and sends a chat request.

## LLM Integration Service

The `LLMIntegration` class is the main entry point for using LLMs in your QuackTools. It manages provider selection, configuration loading, and interaction with the underlying LLM clients.

### Initializing the Service

You can initialize the service with default settings or customize it:

```python
from quack_core.integrations.llms import LLMIntegration
from quack_core.core.logging import LogLevel

# Default initialization
llm_service = LLMIntegration()
llm_service.initialize()

# Customized initialization
custom_service = LLMIntegration(
    provider="anthropic",  # Specify preferred provider
    model="claude-3-opus-20240229",  # Specify model
    api_key="your-api-key",  # Provide API key directly
    config_path="./my_config.yaml",  # Custom config path
    log_level=LogLevel.DEBUG,  # Set logging level
    enable_fallback=True  # Enable fallback to other providers
)
custom_service.initialize()
```

The initialization process:
1. Loads configuration from files or environment variables
2. Checks for available LLM providers
3. Initializes the appropriate LLM client
4. Sets up fallback behavior if enabled

### Working with Different Providers

The `LLMIntegration` service can work with multiple LLM providers:

- **OpenAI**: The default provider, supporting models like GPT-4o
- **Anthropic**: Supporting Claude models
- **Ollama**: For local deployment of open-source models
- **Mock**: For testing purposes

You can specify your preferred provider during initialization:

```python
# Use OpenAI (default)
openai_service = LLMIntegration(provider="openai")

# Use Anthropic
anthropic_service = LLMIntegration(provider="anthropic")

# Use Ollama
ollama_service = LLMIntegration(provider="ollama")

# Each needs to be initialized
openai_service.initialize()
anthropic_service.initialize()
ollama_service.initialize()
```

### Handling Fallbacks

The integration service can automatically fall back to alternative providers if the primary one fails:

```python
# Enable fallback with default order (OpenAI → Anthropic → Mock)
llm_service = LLMIntegration(enable_fallback=True)
llm_service.initialize()

# Check status of providers after some _ops
provider_status = llm_service.get_provider_status()
if provider_status:
    for status in provider_status:
        print(f"Provider: {status['provider']}")
        print(f"  Available: {status['available']}")
        print(f"  Success count: {status['success_count']}")
        print(f"  Fail count: {status['fail_count']}")

# Reset provider status if needed
llm_service.reset_provider_status()
```

Fallback happens automatically when:
- A provider is unavailable (e.g., API key issue)
- A request fails repeatedly
- The service is configured to use multiple providers

## LLM Clients

The module provides specific clients for different LLM providers. These handle the communication details for each API.

### OpenAI Client

The `OpenAIClient` integrates with OpenAI's API:

```python
from quack_core.integrations.llms.clients import OpenAIClient
from quack_core.integrations.llms import ChatMessage, RoleType

# Create the client directly
openai_client = OpenAIClient(
    model="gpt-4o",
    api_key="your-openai-api-key",      # Optional if set in environment
    organization="your-org-id"          # Optional
)

# Create messages
messages = [
    ChatMessage(role=RoleType.USER, content="Explain quantum computing in simple terms")
]

# Get a response
result = openai_client.chat(messages)
if result.success:
    print(result.content)
```

### Anthropic Client

The `AnthropicClient` integrates with Anthropic's API:

```python
from quack_core.integrations.llms.clients import AnthropicClient
from quack_core.integrations.llms import ChatMessage, RoleType, LLMOptions

# Create the client directly
anthropic_client = AnthropicClient(
    model="claude-3-opus-20240229",
    api_key="your-anthropic-api-key"    # Optional if set in environment
)

# System and user messages
messages = [
    ChatMessage(role=RoleType.SYSTEM, content="You are a helpful assistant specialized in biology."),
    ChatMessage(role=RoleType.USER, content="Explain DNA replication")
]

# Options
options = LLMOptions(
    temperature=0.3,
    max_tokens=1000
)

# Get a response
result = anthropic_client.chat(messages, options)
if result.success:
    print(result.content)
```

### Ollama Client

The `OllamaClient` integrates with locally running Ollama server:

```python
from quack_core.integrations.llms.clients import OllamaClient
from quack_core.integrations.llms import ChatMessage, RoleType

# Create the client for a local Ollama server
ollama_client = OllamaClient(
    model="llama3",
    api_base="http://localhost:11434"   # Default Ollama address
)

# Create messages
messages = [
    ChatMessage(role=RoleType.USER, content="Write a haiku about programming")
]

# Get a response
result = ollama_client.chat(messages)
if result.success:
    print(result.content)
```

### Mock Client

The `MockLLMClient` is useful for testing without actual API calls:

```python
from quack_core.integrations.llms.clients import MockLLMClient
from quack_core.integrations.llms import ChatMessage, RoleType

# Create a mock client with predefined responses
mock_client = MockLLMClient(
    script=["This is a mock response", "Here's another mock response"]
)

# Each chat call will return the next response in the script
result1 = mock_client.chat([ChatMessage(role=RoleType.USER, content="First question")])
result2 = mock_client.chat([ChatMessage(role=RoleType.USER, content="Second question")])

print(result1.content)  # "This is a mock response"
print(result2.content)  # "Here's another mock response"

# You can also update the script
mock_client.set_responses(["New response 1", "New response 2"])
```

## Chat Messages and Configuration

### Creating Chat Messages

Chat messages are the building blocks of conversations with LLMs:

```python
from quack_core.integrations.llms import ChatMessage, RoleType

# Different types of messages
system_message = ChatMessage(
    role=RoleType.SYSTEM,
    content="You are a helpful assistant specialized in Python programming."
)

user_message = ChatMessage(
    role=RoleType.USER,
    content="How do I read a file in Python?"
)

assistant_message = ChatMessage(
    role=RoleType.ASSISTANT,
    content="You can read a file in Python using the built-in `open()` function."
)

# You can also create a message from a dictionary
from_dict = ChatMessage.from_dict({
    "role": "user",
    "content": "What's the weather like today?"
})

# Full conversation
conversation = [
    system_message,
    user_message,
    assistant_message,
    from_dict
]
```

### LLM Options

`LLMOptions` allows you to customize LLM requests:

```python
from quack_core.integrations.llms import LLMOptions

# Create options with default values
default_options = LLMOptions()

# Create customized options
custom_options = LLMOptions(
    temperature=0.7,             # Controls randomness (0.0 to 1.0)
    max_tokens=500,              # Maximum length of the response
    top_p=0.9,                   # Nucleus sampling parameter
    frequency_penalty=0.5,       # Penalize repeated tokens
    presence_penalty=0.5,        # Penalize repeated topics
    stop=["###", "END"],         # Stop sequences
    model="gpt-4o",              # Override default model
    stream=True,                 # Enable streaming response
    timeout=30                   # Request timeout in seconds
)
```

## Configuration

### Configuration Files

The LLM integration can load configuration from YAML files:

```yaml
# Example llm_config.yaml
llm:
  default_provider: openai
  timeout: 60
  retry_count: 3
  
  openai:
    api_key: ${OPENAI_API_KEY}  # Uses environment variable
    default_model: gpt-4o
    
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    default_model: claude-3-opus-20240229
    
  ollama:
    api_base: http://localhost:11434
    default_model: llama3
    
  fallback:
    providers:
      - openai
      - anthropic
      - ollama
      - mock
    max_attempts_per_provider: 2
    fail_fast_on_auth_errors: true
```

Configuration is loaded from these locations in order:
1. `./config/llm_config.yaml`
2. `./config/quack_config.yaml`
3. `./quack_config.yaml`
4. `~/.quack/llm_config.yaml`

Or you can specify a custom path:

```python
llm_service = LLMIntegration(config_path="./my_custom_config.yaml")
```

### Environment Variables

You can set API keys and other configuration through environment variables:

```bash
# Set API keys
export OPENAI_API_KEY="sk-your-openai-key"
export ANTHROPIC_API_KEY="sk-ant-your-anthropic-key"
export OPENAI_ORG_ID="org-your-organization-id"

# You can also use the QUACK_LLM_ prefix for environment variables
export QUACK_LLM_DEFAULT_PROVIDER="anthropic"
```

## Advanced Features

### Token Counting

You can count tokens to estimate costs and stay within model limits:

```python
from quack_core.integrations.llms import LLMIntegration, ChatMessage, RoleType

# Initialize the service
llm_service = LLMIntegration()
llm_service.initialize()

# Create messages
messages = [
    ChatMessage(role=RoleType.SYSTEM, content="You are a helpful assistant."),
    ChatMessage(role=RoleType.USER, content="Explain the theory of relativity.")
]

# Count tokens
result = llm_service.count_tokens(messages)
if result.success:
    print(f"Token count: {result.content}")
    
    # Estimate whether we'll stay within limits
    max_tokens = 4096
    if result.content + 1000 < max_tokens:  # 1000 estimated for response
        print("Safe to proceed with request")
    else:
        print("Request may exceed token limits")
```

### Streaming Responses

You can receive responses in chunks for a better user experience:

```python
from quack_core.integrations.llms import LLMIntegration, ChatMessage, RoleType, LLMOptions
import sys

# Initialize the service
llm_service = LLMIntegration()
llm_service.initialize()

# Create messages
messages = [
    ChatMessage(role=RoleType.USER, content="Write a poem about coding")
]

# Create options with streaming enabled
options = LLMOptions(stream=True)

# Define a callback function to process chunks
def process_chunk(chunk: str):
    sys.stdout.write(chunk)
    sys.stdout.flush()

# Send request with streaming
print("AI is composing a poem...\n")
result = llm_service.chat(messages, options, callback=process_chunk)
print("\n\nStreaming complete!")
```

### Using Function and Tool Calls

You can define functions for the LLM to call:

```python
from quack_core.integrations.llms import (
    LLMIntegration, ChatMessage, RoleType, LLMOptions,
    FunctionDefinition, ToolDefinition
)
import json

# Define a weather function
weather_function = FunctionDefinition(
    name="get_weather",
    description="Get the current weather in a location",
    parameters={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city and state, e.g., San Francisco, CA"
            },
            "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "The temperature unit"
            }
        },
        "required": ["location"]
    }
)

# Create a tool with this function
weather_tool = ToolDefinition(
    type="function",
    function=weather_function
)

# Initialize the service
llm_service = LLMIntegration(provider="openai")  # OpenAI supports function calling
llm_service.initialize()

# Create messages
messages = [
    ChatMessage(role=RoleType.USER, content="What's the weather like in New York?")
]

# Create options with tools
options = LLMOptions(tools=[weather_tool])

# Send request
result = llm_service.chat(messages, options)

if result.success:
    # Process potential tool calls in the response
    # Note: This part would require parsing the response based on the provider's format
    response = result.content
    if "tool_calls" in response or "function_call" in response:
        print("The LLM wants to call a function")
        # Further processing would depend on the specific structure
```

### Provider Registry

You can register custom LLM clients:

```python
from quack_core.integrations.llms import register_llm_client
from quack_core.integrations.llms.clients.base import LLMClient

# Create a custom LLM client
class MyCustomLLMClient(LLMClient):
    def _chat_with_provider(self, messages, options, callback=None):
        # Implementation details
        pass
    
    def _count_tokens_with_provider(self, messages):
        # Implementation details
        pass

# Register the custom client
register_llm_client("my_custom", MyCustomLLMClient)

# Now you can use it with the integration service
from quack_core.integrations.llms import LLMIntegration
custom_service = LLMIntegration(provider="my_custom")
custom_service.initialize()
```

### Fallback Strategies

You can configure custom fallback behavior:

```python
from quack_core.integrations.llms import FallbackConfig, LLMIntegration

# Define custom fallback configuration
fallback_config = FallbackConfig(
    providers=["openai", "anthropic", "ollama"],
    max_attempts_per_provider=2,
    delay_between_providers=0.5,
    fail_fast_on_auth_errors=True,
    stop_on_successful_provider=True
)

# Use in configuration file or directly with a FallbackLLMClient
# For LLMIntegration, this would be part of your config file
llm_service = LLMIntegration(enable_fallback=True)  # Uses config from file
llm_service.initialize()
```

## Error Handling

The module provides consistent error handling with specialized error types:

```python
from quack_core.integrations.llms import LLMIntegration, ChatMessage, RoleType
from quack_core.core.errors import QuackApiError, QuackIntegrationError

# Initialize the service
llm_service = LLMIntegration()
llm_service.initialize()

# Create messages
messages = [
   ChatMessage(role=RoleType.USER, content="Tell me a joke")
]

try:
   # Try to get a response
   result = llm_service.chat(messages)

   if result.success:
      print(f"AI response: {result.content}")
   else:
      print(f"Error in result: {result.error}")

      # Check for specific error cases
      if "rate limit" in result.error.lower():
         print("Hit rate limits, try again later")
      elif "api key" in result.error.lower():
         print("API key issue, check your configuration")

except QuackApiError as e:
   # Handle API-specific errors (rate limits, authentication, etc.)
   print(f"API Error: {e}")
   print(f"Service: {e.service}")
   print(f"Method: {e.api_method}")

except QuackIntegrationError as e:
   # Handle integration-specific errors (configuration, setup, etc.)
   print(f"Integration Error: {e}")
   if hasattr(e, 'context') and e.context:
      print(f"Context: {e.context}")

except Exception as e:
   # Handle other unexpected errors
   print(f"Unexpected error: {e}")
```

## Best Practices

1. **Initialize Once, Reuse**: Initialize the LLM service once and reuse it for multiple requests to avoid overhead.

```python
# Good practice
llm_service = LLMIntegration()
llm_service.initialize()

# Multiple requests with the same service
result1 = llm_service.chat(messages1)
result2 = llm_service.chat(messages2)
```

2. **Use System Messages**: Include a system message to set the context and behavior of the assistant.

```python
messages = [
    ChatMessage(role=RoleType.SYSTEM, content="You are a helpful assistant specialized in Python programming."),
    ChatMessage(role=RoleType.USER, content="How do I use async/await?")
]
```

3. **Check Token Counts**: Count tokens before making expensive requests to stay within limits.

```python
# Check token count first
token_result = llm_service.count_tokens(messages)
if token_result.success and token_result.content > 4000:
    # Reduce context or split message
    pass
```

4. **Enable Fallbacks in Production**: For robust applications, always enable fallbacks.

```python
llm_service = LLMIntegration(enable_fallback=True)
```

5. **Use Streaming for Long Responses**: Improve user experience by showing progress for long responses.

```python
def stream_handler(chunk):
    # Update UI with chunk
    pass

options = LLMOptions(stream=True)
llm_service.chat(messages, options, callback=stream_handler)
```

## Troubleshooting

### Common Issues and Solutions

**Issue**: "No LLM providers available" error

**Solution**: Install the required packages
```bash
pip install openai anthropic requests
```

**Issue**: Authentication errors

**Solution**: Check your API keys in environment variables or config files
```bash
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"
```

**Issue**: Response is cut off or too short

**Solution**: Increase max_tokens in options
```python
options = LLMOptions(max_tokens=2000)
```

**Issue**: High latency

**Solution**: Enable fallbacks or switch to a faster model
```python
llm_service = LLMIntegration(enable_fallback=True)
# or
options = LLMOptions(model="gpt-3.5-turbo")  # Faster than GPT-4
```

**Issue**: Errors with Ollama integration

**Solution**: Verify Ollama is running locally
```bash
curl http://localhost:11434/api/version
```

## API Reference

### Core Classes

#### `LLMIntegration`

The main service class for using LLMs.

```python
LLMIntegration(
    provider: str | None = None,        # Provider name (openai, anthropic, ollama)
    model: str | None = None,           # Model name
    api_key: str | None = None,         # API key
    config_path: str | None = None,     # Path to config file
    log_level: int = LOG_LEVELS[LogLevel.INFO],  # Logging level
    enable_fallback: bool = True        # Enable fallback to other providers
)
```

**Methods**:
- `initialize() -> IntegrationResult`: Initialize the service
- `chat(messages, options=None, callback=None) -> IntegrationResult[str]`: Send chat request
- `count_tokens(messages) -> IntegrationResult[int]`: Count tokens in messages
- `get_provider_status() -> list[dict] | None`: Get status of all providers
- `reset_provider_status() -> bool`: Reset provider status
- `get_client() -> LLMClient`: Get the underlying client

#### `ChatMessage`

Represents a message in a conversation.

```python
ChatMessage(
    role: RoleType,                    # Role (system, user, assistant)
    content: str | None = None,        # Message content
    name: str | None = None,           # Name (for function calls)
    function_call: dict | None = None, # Function call data
    tool_calls: list[dict] | None = None  # Tool call data
)
```

#### `LLMOptions`

Options for customizing LLM requests.

```python
LLMOptions(
    temperature: float = 0.7,           # Temperature (0.0 to 2.0)
    max_tokens: int | None = None,      # Maximum tokens in response
    top_p: float = 1.0,                 # Nucleus sampling parameter
    frequency_penalty: float = 0.0,     # Frequency penalty
    presence_penalty: float = 0.0,      # Presence penalty
    stop: list[str] | None = None,      # Stop sequences
    functions: list[FunctionDefinition] | None = None,  # Available functions
    tools: list[ToolDefinition] | None = None,          # Available tools
    model: str | None = None,           # Override model
    response_format: dict | None = None, # Response format
    seed: int | None = None,            # Random seed
    stream: bool = False,               # Enable streaming
    timeout: int = 60,                  # Request timeout
    retry_count: int = 3,               # Retry count
    initial_retry_delay: float = 1.0,   # Initial retry delay
    max_retry_delay: float = 30.0       # Maximum retry delay
)
```

### Provider Clients

- `OpenAIClient`: Client for OpenAI API
- `AnthropicClient`: Client for Anthropic API
- `OllamaClient`: Client for Ollama API
- `MockLLMClient`: Mock client for testing
- `FallbackLLMClient`: Client with fallback capabilities

Each follows the `LLMClient` base class interface.

### Utility Functions

- `get_llm_client(provider, model=None, api_key=None, **kwargs) -> LLMClient`: Get a client for a specific provider
- `register_llm_client(name, client_class)`: Register a custom LLM client
- `get_mock_llm(script=None) -> MockLLMClient`: Create a mock LLM client