import logging
import os
from collections.abc import Callable
from typing import Any

from zeo_core.core.errors import ZeoApiError, ZeoIntegrationError
from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.llms.clients.base import LLMClient
from zeo_core.integrations.llms.models import (
    ChatMessage,
    LLMOptions,
    RoleType,
    ToolDefinition,
)


class AnthropicClient(LLMClient):
    """Anthropic LLM client implementation."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
        timeout: int = 60,
        retry_count: int = 3,
        initial_retry_delay: float = 1.0,
        max_retry_delay: float = 30.0,
        log_level: int = logging.INFO,
        **kwargs: Any,  # noqa: ANN401 -- provider-specific kwargs passed through to the anthropic SDK constructor
    ) -> None:
        """
        Initialize the Anthropic client.

        Args:
            model: Model name to use
            api_key: Anthropic API key
            api_base: Anthropic API base URL
            timeout: Request timeout in seconds
            retry_count: Number of retries for failed requests
            initial_retry_delay: Initial delay for exponential backoff
            max_retry_delay: Maximum delay between retries
            log_level: Logging level
            **kwargs: Additional Anthropic-specific arguments
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
        self._client: Any = None

        self._check_anthropic_package()

    def _check_anthropic_package(self) -> None:
        """
        Check if the Anthropic package is installed and available.

        Raises:
            ZeoIntegrationError: If Anthropic package is not installed
        """
        try:
            # Import directly instead of using find_spec to avoid issues with mocks
            import anthropic  # noqa: F401 -- presence check only, ImportError is the signal

            self.logger.debug("Anthropic package is available")
        except ImportError:
            self.logger.error("Anthropic package not installed")
            raise ZeoIntegrationError(
                "Anthropic package not installed. "
                "Please install it with: pip install anthropic"
            ) from None

    def _get_client(self) -> Any:  # noqa: ANN401 -- returns the third-party anthropic.Anthropic SDK object; no local protocol exists for it
        """
        Get the Anthropic client instance.

        Returns:
            Any: Anthropic client instance

        Raises:
            ZeoIntegrationError: If Anthropic package is not installed
        """
        if self._client is None:
            try:
                # Try to import the Anthropic module
                try:
                    from anthropic import Anthropic
                except ImportError as e:
                    self.logger.error(f"Failed to import Anthropic package: {e}")
                    raise ZeoIntegrationError(
                        "Anthropic package not installed. "
                        "Please install it with: pip install anthropic",
                        original_error=e,
                    ) from e

                # Get API key from environment variable if not provided
                api_key = self._api_key or self._get_api_key_from_env()

                # dict[str, Any], not the empty-literal-inferred narrower
                # type mypy would otherwise assign -- Anthropic's own
                # constructor has no local protocol (matches _get_client's
                # own `-> Any` / noqa: ANN401 reasoning above), so a
                # precisely-typed **kwargs splat against it is not
                # achievable without vendoring the SDK's own signature.
                kwargs: dict[str, Any] = {}
                if self._api_base:
                    kwargs["base_url"] = self._api_base

                self._client = Anthropic(api_key=api_key, **kwargs)
            except Exception as e:
                self.logger.error(f"Error initializing Anthropic client: {e}")
                raise ZeoIntegrationError(
                    f"Failed to initialize Anthropic client: {e}",
                    original_error=e,
                ) from e

        return self._client

    def _get_api_key_from_env(self) -> str:
        """
        Get the Anthropic API key from environment variables.

        Returns:
            str: Anthropic API key

        Raises:
            ZeoIntegrationError: If API key is not provided or available in
                environment
        """
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            self.logger.error("Anthropic API key not provided in environment")
            raise ZeoIntegrationError(
                "Anthropic API key not provided. Please provide it as an "
                "argument or set the ANTHROPIC_API_KEY environment variable."
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
            # Set default model if not specified. claude-3-opus-20240229 was
            # retired 2026-01-05 (zeocore-integrations-gap-SOW-01 s3 finding
            # 1). claude-sonnet-5 is the current, non-retired, balanced-cost
            # default -- same role gpt-4o plays for OpenAIClient.model and
            # llama3 plays for OllamaClient.model, not the priciest tier.
            self._model = "claude-sonnet-5"
        return self._model

    def _convert_message_to_anthropic(self, message: ChatMessage) -> dict:
        """
        Convert a ChatMessage to the format expected by Anthropic.

        Args:
            message: ChatMessage to convert

        Returns:
            dict: Message in Anthropic format
        """
        role = "user" if message.role == RoleType.USER else "assistant"
        return {
            "role": role,
            "content": message.content or "",
        }

    def _convert_tools_to_anthropic(
        self, tools: list[ToolDefinition]
    ) -> list[dict[str, Any]]:
        """
        Convert the shared, OpenAI-function-shaped ToolDefinition models
        (LLMOptions.tools) into Anthropic's native tool-use request shape.

        The shared model layer stores each tool as
        {"type": "function", "function": {"name", "description",
        "parameters"}} (see ToolDefinition/FunctionDefinition in
        llms/models.py) because that shape passes through unchanged for
        OpenAI (LLMOptions.to_openai_params() just calls t.model_dump()).
        Anthropic's Messages API takes a flat {"name", "description",
        "input_schema"} shape instead -- no "type"/"function" wrapper, and
        the JSON-schema field is named "input_schema", not "parameters".
        This method does that field remap; it does not change what the
        caller writes in LLMOptions.tools.

        Args:
            tools: Tool definitions from LLMOptions.tools.

        Returns:
            list[dict]: Tool definitions in Anthropic's native request shape.
        """
        anthropic_tools = []
        for tool in tools:
            function = tool.function
            anthropic_tools.append(
                {
                    "name": function.name,
                    "description": function.description or "",
                    "input_schema": function.parameters
                    or {"type": "object", "properties": {}},
                }
            )
        return anthropic_tools

    def _prepare_request_params(self, options: LLMOptions) -> dict[str, Any]:
        """
        Build the Anthropic-specific request params derived from LLMOptions.

        Split out of _chat_with_provider to keep that method's cyclomatic
        complexity under the ruff C901 gate (max 10) -- adding tools/
        cache_control wiring pushed the inline version to 12.

        Args:
            options: Options for the completion request.

        Returns:
            dict[str, Any]: Params to splat into client.messages.create /
                client.messages.stream, alongside model/messages/system/
                max_tokens/temperature.
        """
        # dict[str, Any], not the float-literal-inferred narrower type mypy
        # would otherwise assign -- splatted into the third-party
        # client.messages.create(**params) call, same no-local-protocol
        # reasoning as the constructor kwargs in _get_client.
        params: dict[str, Any] = {
            "top_p": options.top_p,
        }

        if options.stop:
            params["stop_sequences"] = options.stop

        # Tool-use passthrough. LLMOptions.tools exists in the shared model
        # layer and is already read by LLMOptions.to_openai_params() for
        # the OpenAI path (models.py, to_openai_params) but was never read
        # here -- zeocore-integrations-gap-SOW-01 s3 finding 2. Converted
        # to Anthropic's native {"name", "description", "input_schema"}
        # tool shape; see _convert_tools_to_anthropic for why a conversion
        # is needed rather than a raw model_dump() (unlike the OpenAI path,
        # whose wire shape already matches ToolDefinition).
        if options.tools:
            params["tools"] = self._convert_tools_to_anthropic(options.tools)

        return params

    def _build_system_param(
        self, system_message: str | None, options: LLMOptions
    ) -> str | list[dict[str, Any]] | None:
        """
        Build the `system` param, applying prompt-caching if requested.

        Prompt caching: LLMOptions.cache_system_prompt marks the system
        prompt as cacheable via Anthropic's cache_control breakpoint
        mechanism -- zeocore-integrations-gap-SOW-01 s3 finding 3 (no
        cache_control/prompt-caching wiring existed at all). Per the
        Anthropic API, cache_control attaches to a content block, not a
        bare string, so a cacheable system prompt is sent as a one-block
        content list rather than plain text.

        Args:
            system_message: The system message content, if any.
            options: Options for the completion request.

        Returns:
            The system param as Anthropic expects it -- a bare string, a
            cache_control-annotated content-block list, or None.
        """
        if options.cache_system_prompt and system_message:
            return [
                {
                    "type": "text",
                    "text": system_message,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        return system_message

    def _handle_streaming(
        self,
        client: Any,  # noqa: ANN401 -- the third-party anthropic.Anthropic SDK client object; no local protocol exists for it
        model: str,
        system: str | list[dict[str, Any]] | None,
        messages: list[dict],
        params: dict,
        callback: Callable[[str], None] | None,
    ) -> str:
        """
        Handle streaming responses from the Anthropic API.

        Args:
            client: Anthropic client instance
            model: Model name
            system: System message
            messages: List of messages in Anthropic format
            params: Anthropic API parameters
            callback: Callback function for streaming responses

        Returns:
            str: Complete response text

        Raises:
            ZeoApiError: If there's an error with the Anthropic API
        """
        collected_content = []

        try:
            # Create stream object
            stream = client.messages.stream(
                model=model, messages=messages, system=system, stream=True, **params
            )

            # Use the stream context manager if available (real API client)
            # or iterate through it directly if it's a mock
            try:
                with stream as context_stream:
                    for chunk in context_stream:
                        if (
                            hasattr(chunk, "type")
                            and chunk.type == "content_block_delta"
                            and hasattr(chunk, "delta")
                            and hasattr(chunk.delta, "text")
                        ):
                            collected_content.append(chunk.delta.text)
                            if callback:
                                callback(chunk.delta.text)
            except (AttributeError, TypeError):
                # If context manager protocol isn't supported (e.g., in tests),
                # try to use the stream directly as an iterator
                for chunk in stream:
                    if (
                        hasattr(chunk, "type")
                        and chunk.type == "content_block_delta"
                        and hasattr(chunk, "delta")
                        and hasattr(chunk.delta, "text")
                    ):
                        collected_content.append(chunk.delta.text)
                        if callback:
                            callback(chunk.delta.text)

            return "".join(collected_content)
        except Exception as e:
            # Convert Anthropic errors to ZeoApiError
            raise self._convert_error(e) from e

    def _convert_error(self, error: Exception) -> ZeoApiError:
        """
        Convert Anthropic errors to ZeoApiError.

        Args:
            error: Original error

        Returns:
            ZeoApiError: Converted error
        """
        error_str = str(error)

        # Check for specific error types
        if "rate" in error_str.lower() and "limit" in error_str.lower():
            return ZeoApiError(
                f"Anthropic rate limit exceeded: {error}",
                service="Anthropic",
                api_method="messages.create",
                original_error=error,
            )
        elif (
            (
                "api_key" in error_str.lower()
                and ("invalid" in error_str.lower() or "incorrect" in error_str.lower())
            )
            or ("invalid api key" in error_str.lower())
            or ("authentication" in error_str.lower())
        ):
            return ZeoApiError(
                f"Invalid Anthropic API key: {error}",
                service="Anthropic",
                api_method="messages.create",
                original_error=error,
            )
        elif "quota" in error_str.lower():
            return ZeoApiError(
                f"Insufficient Anthropic quota: {error}",
                service="Anthropic",
                api_method="messages.create",
                original_error=error,
            )
        else:
            return ZeoApiError(
                f"Anthropic API error: {error}",
                service="Anthropic",
                api_method="messages.create",
                original_error=error,
            )

    def _chat_with_provider(
        self,
        messages: list[ChatMessage],
        options: LLMOptions,
        callback: Callable[[str], None] | None = None,
    ) -> IntegrationResult[str]:
        """
        Send a chat completion request to the Anthropic API.

        Args:
            messages: List of messages for the conversation
            options: Additional options for the completion request
            callback: Optional callback function for streaming responses

        Returns:
            IntegrationResult[str]: Result of the chat completion request

        Raises:
            ZeoIntegrationError: If Anthropic package is not installed
            ZeoApiError: If there's an error with the Anthropic API
        """
        # First check if we can import Anthropic
        # This ensures we raise ZeoIntegrationError for import issues
        # before entering the try block where we'd convert to ZeoApiError
        try:
            from anthropic import (
                Anthropic as _,  # noqa: F401 -- Just checking import, not using
            )
        except ImportError as e:
            self.logger.error(f"Failed to import Anthropic package: {e}")
            raise ZeoIntegrationError(
                f"Failed to import Anthropic package: {e}. "
                "Please install it with: pip install anthropic",
                original_error=e,
            ) from e

        try:
            client = self._get_client()

            # Convert messages to the format expected by Anthropic.
            system_message: str | None = None
            anthropic_messages = []

            for msg in messages:
                if msg.role == RoleType.SYSTEM:
                    system_message = msg.content
                else:
                    anthropic_messages.append(self._convert_message_to_anthropic(msg))

            params = self._prepare_request_params(options)
            system_param = self._build_system_param(system_message, options)

            # Override model if specified in options
            model = options.model or self.model

            # Handle streaming if callback is provided
            if callback and not options.stream:
                options.stream = True
                params["stream"] = True

            if options.stream:
                response_text = self._handle_streaming(
                    client, model, system_param, anthropic_messages, params, callback
                )
                return IntegrationResult.success_result(response_text)
            else:
                # Make the API call
                response = client.messages.create(
                    model=model,
                    messages=anthropic_messages,
                    system=system_param,
                    max_tokens=options.max_tokens or 1024,
                    temperature=options.temperature,
                    **params,
                )

                # Process the response
                if (
                    hasattr(response, "content")
                    and len(response.content) > 0
                    and hasattr(response.content[0], "text")
                ):
                    result = response.content[0].text
                elif hasattr(response, "text"):
                    result = response.text
                else:
                    # Fallback for mocks or unexpected response formats
                    result = str(response)

                return IntegrationResult.success_result(result)

        except Exception as e:
            # Convert Anthropic errors to ZeoApiError
            raise self._convert_error(e) from e

    def _count_tokens_with_provider(
        self, messages: list[ChatMessage]
    ) -> IntegrationResult[int]:
        """
        Count the number of tokens in the messages using Anthropic's tokenizer.

        Args:
            messages: List of messages to count tokens for

        Returns:
            IntegrationResult[int]: Result containing the token count
        """
        try:
            # Separate system message from other messages
            system_message = None
            anthropic_messages = []

            for msg in messages:
                if msg.role == RoleType.SYSTEM:
                    system_message = msg.content
                else:
                    anthropic_messages.append(self._convert_message_to_anthropic(msg))

            try:
                # Get the client (which imports the anthropic module)
                client = self._get_client()

                # Use Anthropic's tokenizer API
                count_result = client.count_tokens(
                    model=self.model, messages=anthropic_messages, system=system_message
                )

                # Handle different response formats (API vs mock)
                if hasattr(count_result, "input_tokens"):
                    token_count = count_result.input_tokens
                elif isinstance(count_result, int):
                    token_count = count_result
                else:
                    # Try to extract token count from response
                    token_count = getattr(
                        count_result, "input_tokens", getattr(count_result, "tokens", 0)
                    )

                return IntegrationResult.success_result(token_count)

            except (ImportError, AttributeError) as e:
                # Fall back to a simple estimation if anthropic package doesn't
                # support token counting
                self.logger.warning(
                    f"Anthropic token counting API not available: {e}. "
                    "Using simple token estimation."
                )

                # Simple estimation based on words (very rough approximation)
                total_text = ""
                for message in messages:
                    if message.content:
                        total_text += message.content + " "

                # Rough approximation: 1 token ≈ 4 characters
                estimated_tokens = len(total_text) // 4

                return IntegrationResult.success_result(
                    estimated_tokens,
                    message="Token count is an estimation. Actual count may vary.",
                )

        except Exception as e:
            self.logger.error(f"Error counting tokens: {e}")
            return IntegrationResult.error_result(f"Error counting tokens: {e}")
