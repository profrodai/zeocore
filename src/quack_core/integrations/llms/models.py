# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/llms/models.py
# module: quack_core.integrations.llms.models
# role: models
# neighbors: __init__.py, protocols.py, config.py, registry.py, fallback.py
# exports: RoleType, ChatMessage, FunctionParameter, FunctionDefinition, ToolDefinition, FunctionCall, ToolCall, LLMOptions (+1 more)
# git_branch: refactor/newHeaders
# git_commit: bd13631
# === QV-LLM:END ===

"""
Data models for LLM integration.

This module provides Pydantic models for representing chat messages,
function calls, and configuration options for LLM requests.
"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class RoleType(str, Enum):
    """Enumeration of possible message roles in a chat conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """Model representing a chat message."""

    role: RoleType = Field(..., description="Role of the message sender")
    content: str | None = Field(None, description="Message content")
    name: str | None = Field(
        None, description="Name of the sender (for function calls)"
    )
    function_call: dict | None = Field(None, description="Function call data")
    tool_calls: list[dict] | None = Field(None, description="Tool call data")

    @classmethod
    def from_dict(cls, message_dict: dict) -> "ChatMessage":
        """
        Create a ChatMessage from a dictionary.

        Args:
            message_dict: Dictionary containing message data.

        Returns:
            ChatMessage: A new chat message instance.
        """
        role = message_dict.get("role", "user")
        return cls(
            role=role,
            content=message_dict.get("content"),
            name=message_dict.get("name"),
            function_call=message_dict.get("function_call"),
            tool_calls=message_dict.get("tool_calls"),
        )


class FunctionParameter(BaseModel):
    """Model representing a function parameter."""

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type")
    description: str | None = Field(None, description="Parameter description")
    required: bool = Field(False, description="Whether the parameter is required")


class FunctionDefinition(BaseModel):
    """Model representing a function definition."""

    name: str = Field(..., description="Function name")
    description: str | None = Field(None, description="Function description")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Function parameters"
    )


class ToolDefinition(BaseModel):
    """Model representing a tool definition."""

    type: str = Field("function", description="Tool type")
    function: FunctionDefinition = Field(..., description="Function definition")


class FunctionCall(BaseModel):
    """Model representing a function call."""

    name: str = Field(..., description="Function name")
    arguments: str = Field(..., description="Function arguments as a JSON string")


class ToolCall(BaseModel):
    """Model representing a tool call."""

    id: str = Field(..., description="Tool call ID")
    type: str = Field("function", description="Tool type")
    function: FunctionCall = Field(..., description="Function call")

    model_config = {"extra": "forbid"}


class LLMOptions(BaseModel):
    """Model for additional options for LLM requests."""

    temperature: float = Field(0.7, description="Temperature for sampling")
    max_tokens: int | None = Field(
        None, description="Maximum number of tokens to generate"
    )
    top_p: float = Field(1.0, description="Nucleus sampling parameter")
    frequency_penalty: float = Field(0.0, description="Frequency penalty")
    presence_penalty: float = Field(0.0, description="Presence penalty")
    stop: list[str] | None = Field(None, description="Stop sequences")
    functions: list[FunctionDefinition] | None = Field(
        None, description="Available functions"
    )
    tools: list[ToolDefinition] | None = Field(None, description="Available tools")
    model: str | None = Field(None, description="Override model name")
    response_format: dict | None = Field(
        None, description="Response format specification"
    )
    seed: int | None = Field(None, description="Random seed for deterministic results")
    stream: bool = Field(False, description="Whether to stream the response")
    timeout: int = Field(60, description="Request timeout in seconds")
    retry_count: int = Field(3, description="Number of retries for failed requests")
    initial_retry_delay: float = Field(
        1.0, description="Initial delay for exponential backoff"
    )
    max_retry_delay: float = Field(30.0, description="Maximum delay between retries")

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature to be between 0 and 2."""
        if v < 0 or v > 2:
            raise ValueError("Temperature must be between 0 and 2")
        return v

    @field_validator("top_p")
    @classmethod
    def validate_top_p(cls, v: float) -> float:
        """Validate top_p to be between 0 and 1."""
        if v < 0 or v > 1:
            raise ValueError("top_p must be between 0 and 1")
        return v

    @field_validator("retry_count")
    @classmethod
    def validate_retry_count(cls, v: int) -> int:
        """Validate retry_count to be non-negative."""
        if v < 0:
            raise ValueError("retry_count must be non-negative")
        return v

    def to_openai_params(self, model: str | None = None) -> dict[str, Any]:
        """
        Convert options to OpenAI API parameters, adjusting the token parameter name
        depending on the model type.

        Args:
            model: The model name to check for token parameter naming.

        Returns:
            dict: Parameters for the OpenAI API.
        """
        params = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
        }
        # Use 'max_completion_tokens' if the model belongs to the "o" family, otherwise 'max_tokens'
        token_param_name = "max_tokens"
        if model and model.lower().startswith("o"):
            token_param_name = "max_completion_tokens"
        if self.max_tokens is not None:
            params[token_param_name] = self.max_tokens
        if self.stop:
            params["stop"] = self.stop
        if self.functions:
            params["functions"] = [f.model_dump() for f in self.functions]
        if self.tools:
            params["tools"] = [t.model_dump() for t in self.tools]
        if self.response_format:
            params["response_format"] = self.response_format
        if self.seed is not None:
            params["seed"] = self.seed
        if self.stream:
            params["stream"] = self.stream

        return params


class LLMResult(BaseModel):
    """Model for LLM completion result."""

    content: str = Field(..., description="Completion content")
    role: Literal["assistant"] = Field("assistant", description="Message role")
    model: str = Field(..., description="Model used for completion")
    prompt_tokens: int | None = Field(None, description="Number of prompt tokens")
    completion_tokens: int | None = Field(
        None, description="Number of completion tokens"
    )
    total_tokens: int | None = Field(None, description="Total number of tokens")
    function_call: FunctionCall | None = Field(None, description="Function call data")
    tool_calls: list[ToolCall] | None = Field(None, description="Tool call data")
