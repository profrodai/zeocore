# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/llms/clients/openai.py
# module: quack_core.integrations.llms.clients.openai
# role: module
# neighbors: __init__.py, anthropic.py, base.py, mock.py, ollama.py
# exports: OpenAIClient
# git_branch: refactor/toolkitWorkflow
# git_commit: 0f9247b
# === QV-LLM:END ===

"""
OpenAI LLM client implementation.

This module provides a client for the OpenAI API, supporting chat completions
and token counting with proper error handling and retry logic.
"""

import logging
import os
from collections.abc import Callable
from typing import Any

from quack_core.lib.errors import QuackApiError, QuackIntegrationError
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.llms.clients.base import LLMClient
from quack_core.integrations.llms.models import ChatMessage, LLMOptions


class OpenAIClient(LLMClient):
    """OpenAI LLM client implementation."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
        organization: str | None = None,
        timeout: int = 60,
        retry_count: int = 3,
        initial_retry_delay: float = 1.0,
        max_retry_delay: float = 30.0,
        log_level: int = logging.INFO,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the OpenAI client.
        """
        super().__init__(
            model=model,
            api_key=api_key,
            timeout=timeout,
            retry_count=retry_count,
            initial_retry_delay=initial_retry_delay,
            max_retry_delay=max_retry_delay,
            log_level=log_level,
            **kwargs,
        )
        self._api_base = api_base
        self._organization = organization
        self._client = None

        # If API key is provided, set it in environment so the OpenAI SDK can find it
        if api_key and not os.environ.get("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = api_key
            self.logger.debug(
                "Set OPENAI_API_KEY in environment from provided argument"
            )

        # Set organization in environment if provided
        if organization and not os.environ.get("OPENAI_ORGANIZATION"):
            os.environ["OPENAI_ORGANIZATION"] = organization
            self.logger.debug(
                "Set OPENAI_ORGANIZATION in environment from provided argument"
            )

    def _get_client(self) -> Any:
        """
        Get the OpenAI client instance.
        Returns:
            Any: OpenAI client instance
        Raises:
            QuackIntegrationError: If OpenAI package is not installed
        """
        if self._client is None:
            try:
                # More robust way to check if openai module is available
                try:
                    import openai
                    from openai import OpenAI
                except ImportError as e:
                    raise QuackIntegrationError(
                        f"OpenAI package not installed or cannot be imported: {e}. "
                        "Please install it with: pip install openai",
                        original_error=e,
                    )

                # Get API key from provided value or from environment variable
                if not self._api_key:
                    self._api_key = self._get_api_key_from_env()

                kwargs = {"api_key": self._api_key, "timeout": self._timeout}

                if self._api_base:
                    kwargs["base_url"] = self._api_base
                if self._organization:
                    kwargs["organization"] = self._organization

                # Ensure the API key is also set in the environment
                # This helps with certain OpenAI SDK versions/implementations
                import os

                if self._api_key and "OPENAI_API_KEY" not in os.environ:
                    os.environ["OPENAI_API_KEY"] = self._api_key
                    self.logger.debug("Set OPENAI_API_KEY in environment")

                self._client = OpenAI(**kwargs)
                self.logger.debug(
                    f"Successfully created OpenAI client with model: {self.model}"
                )
            except ImportError as e:
                raise QuackIntegrationError(
                    f"Failed to import OpenAI package: {e}. "
                    "Please install it with: pip install openai",
                    original_error=e,
                ) from e
            except Exception as e:
                raise QuackIntegrationError(
                    f"Failed to initialize OpenAI client: {e}",
                    original_error=e,
                ) from e

        return self._client

    def _get_api_key_from_env(self) -> str:
        """
        Get the OpenAI API key from environment variables.
        Returns:
            str: OpenAI API key
        Raises:
            QuackIntegrationError: If API key is not provided or available in environment
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise QuackIntegrationError(
                "OpenAI API key not provided. "
                "Please provide it as an argument or set the OPENAI_API_KEY environment variable."
            )
        return api_key

    @property
    def model(self) -> str:
        """
        Get the model name.
        Returns:
            str: Model name to use for requests
        """
        if not self._model:
            # Set default model if not specified
            self._model = "gpt-4o"
        return self._model

    def _chat_with_provider(
        self,
        messages: list[ChatMessage],
        options: LLMOptions,
        callback: Callable[[str], None] | None = None,
    ) -> IntegrationResult[str]:
        try:
            client = self._get_client()

            # Convert messages to the format expected by OpenAI
            openai_messages = [self._convert_message_to_openai(msg) for msg in messages]

            # Override model if specified in options
            model = options.model or self.model

            # Pass the model to the options to decide on the token parameter name
            params = options.to_openai_params(model=model)

            # Handle streaming if callback is provided
            if callback and not options.stream:
                options.stream = True
                params["stream"] = True

            if options.stream:
                response_text = self._handle_streaming(
                    client, model, openai_messages, params, callback
                )
                return IntegrationResult.success_result(response_text)
            else:
                try:
                    completions_create = client.chat.completions.create
                except AttributeError:
                    completions_create = client.chat_completions_create

                response = completions_create(
                    model=model, messages=openai_messages, **params
                )

                # Process the response
                result = self._process_response(response)
                return IntegrationResult.success_result(result)

        except ImportError as e:
            raise QuackIntegrationError(
                f"Failed to import OpenAI package: {e}",
                original_error=e,
            ) from e
        except Exception as e:
            raise self._convert_error(e)

    def _handle_streaming(
        self,
        client: Any,
        model: str,
        messages: list[dict],
        params: dict,
        callback: Callable[[str], None] | None,
    ) -> str:
        """
        Handle streaming responses from the OpenAI API.
        """
        collected_content = []

        try:
            # Remove stream parameter if it exists in params to avoid duplication
            params_copy = params.copy()
            if "stream" in params_copy:
                del params_copy["stream"]

            stream = client.chat.completions.create(
                model=model, messages=messages, stream=True, **params_copy
            )

            for chunk in stream:
                # Support both dict and object formats for chunks
                if isinstance(chunk, dict):
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue

                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                else:
                    if not hasattr(chunk, "choices") or not chunk.choices:
                        continue

                    delta = (
                        chunk.choices[0].delta
                        if hasattr(chunk.choices[0], "delta")
                        else {}
                    )
                    content = delta.content if hasattr(delta, "content") else None

                if content:
                    collected_content.append(content)
                    if callback:
                        callback(content)

            return "".join(collected_content)
        except Exception as e:
            # Convert OpenAI errors to QuackApiError
            raise self._convert_error(e)

    def _convert_message_to_openai(self, message: ChatMessage) -> dict:
        """
        Convert a ChatMessage to the format expected by OpenAI.
        """
        openai_message = {"role": message.role.value}

        if message.content is not None:
            openai_message["content"] = message.content

        if message.name:
            openai_message["name"] = message.name

        if message.function_call:
            openai_message["function_call"] = message.function_call

        if message.tool_calls:
            openai_message["tool_calls"] = message.tool_calls

        return openai_message

    def _process_response(self, response: Any) -> str:
        """
        Process a response from the OpenAI API.
        Supports both dict and object responses.
        """
        # Get choices whether response is a dict or an object
        if isinstance(response, dict):
            choices = response.get("choices", [])
        else:
            choices = getattr(response, "choices", [])
        if not choices:
            return ""

        # Get the first choice's message
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message", None)
        else:
            message = getattr(first_choice, "message", None)
        if not message:
            return ""

        # Get the content of the message
        if isinstance(message, dict):
            content = message.get("content", None)
        else:
            content = getattr(message, "content", None)
        return content if content is not None else ""

    def _convert_error(self, error: Exception) -> QuackApiError:
        """
        Convert OpenAI errors to QuackApiError.
        """
        error_str = str(error)

        if "rate limit" in error_str.lower():
            return QuackApiError(
                f"OpenAI rate limit exceeded: {error}",
                service="OpenAI",
                api_method="chat.completions.create",
                original_error=error,
            )
        elif "invalid api key" in error_str.lower():
            return QuackApiError(
                f"Invalid OpenAI API key: {error}",
                service="OpenAI",
                api_method="chat.completions.create",
                original_error=error,
            )
        elif "insufficient quota" in error_str.lower():
            return QuackApiError(
                f"Insufficient OpenAI quota: {error}",
                service="OpenAI",
                api_method="chat.completions.create",
                original_error=error,
            )
        else:
            return QuackApiError(
                f"OpenAI API error: {error}",
                service="OpenAI",
                api_method="chat.completions.create",
                original_error=error,
            )

    def _count_tokens_with_provider(
        self, messages: list[ChatMessage]
    ) -> IntegrationResult[int]:
        """
        Count the number of tokens in the messages using OpenAI's tokenizer.
        """
        try:
            try:
                import tiktoken

                model = self.model
                encoding_name = "cl100k_base"
                try:
                    encoding = tiktoken.encoding_for_model(model)
                except KeyError:
                    encoding = tiktoken.get_encoding(encoding_name)

                token_count = 0
                openai_messages = [
                    self._convert_message_to_openai(msg) for msg in messages
                ]

                tokens_per_message = 3  # This already accounts for role tokens.
                tokens_per_name = 1  # Extra token for name if present.

                for message in openai_messages:
                    token_count += tokens_per_message

                    for key, value in message.items():
                        # Skip the role since it's already counted in tokens_per_message.
                        if key == "role":
                            continue
                        if isinstance(value, str):
                            token_count += len(encoding.encode(value))
                        elif isinstance(value, dict):
                            json_str = str(value)
                            token_count += len(encoding.encode(json_str))
                        if key == "name" and value:
                            token_count += tokens_per_name

                # Add 3 tokens for the assistant's reply.
                token_count += 3

                return IntegrationResult.success_result(token_count)

            except ImportError:
                self.logger.warning(
                    "tiktoken not installed. Using simple token estimation. "
                    "Install tiktoken for more accurate counts: pip install tiktoken"
                )
                total_text = ""
                for message in messages:
                    if message.content:
                        total_text += message.content + " "
                estimated_tokens = len(total_text) // 4
                return IntegrationResult.success_result(
                    estimated_tokens,
                    message="Using simple token estimation. Install tiktoken for accuracy.",
                )

        except Exception as e:
            self.logger.error(f"Error counting tokens: {e}")
            return IntegrationResult.error_result(f"Error counting tokens: {e}")
