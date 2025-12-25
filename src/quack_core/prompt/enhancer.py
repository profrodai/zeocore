# quack-core/src/quack_core/prompt/enhancer.py
"""
Prompt enhancer module for the PromptBooster.

This module uses an LLM to rewrite and polish prompt templates
into production-ready prompts, leveraging the quack_core.integrations.llms
module for standardized LLM interactions.
"""

from collections.abc import Sequence

from quack_core.config import config as quack_config
from quack_core.fs.service import standalone
from quack_core.logging import get_logger

# Set up logger
logger = get_logger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "llm": {
        "temperature": 0.3,
        "max_tokens": 1200,
        "top_p": 0.95,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    },
    "system_prompt": {
        "prompt_engineer": "You are a world-class prompt engineer.\nYou will be given a task description and optionally a schema and examples.\nRewrite the prompt {strategy} so that it is production-ready.\nFormat the output clearly for use with GPT-4 or Claude.\n\nONLY output the final rewritten prompt."
    },
}


def _load_config() -> dict:
    """
    Load configuration for the enhancer module.

    This checks for configuration in the standard QuackCore locations
    and falls back to defaults if not found.

    Returns:
        Configuration dictionary with LLM options and system prompts
    """
    # Try to load from custom config
    enhancer_config = quack_config.get_custom("prompt.enhancer", {})

    if not enhancer_config:
        # Check if we have a local config file
        config_paths = ["config/prompt_enhancer.yaml", "prompt_enhancer.yaml"]

        for path in config_paths:
            result = standalone.read_yaml(path)
            if result.success:
                enhancer_config = result.data
                logger.debug(f"Loaded enhancer config from {path}")
                break

    # Merge with defaults
    config = DEFAULT_CONFIG.copy()

    # Update with any found configuration
    if enhancer_config:
        if "llm" in enhancer_config:
            config["llm"].update(enhancer_config.get("llm", {}))
        if "system_prompt" in enhancer_config:
            config["system_prompt"].update(enhancer_config.get("system_prompt", {}))

    return config


def enhance_with_llm(
    task_description: str,
    schema: str | None = None,
    examples: list[str] | str | None = None,
    strategy_name: str | None = None,
    model: str | None = None,
    provider: str | None = None,
) -> str:
    """
    Use an LLM to enhance a prompt based on the selected strategy.

    Args:
        task_description: The basic task description
        schema: Optional schema for structured output
        examples: Optional examples for few-shot learning
        strategy_name: Name of the strategy being used
        model: Optional specific model to use (e.g., "gpt-4o" or "claude-3-opus-20240229")
        provider: Optional specific provider to use (e.g., "openai" or "anthropic")

    Returns:
        A polished, production-ready prompt

    Raises:
        ImportError: If the LLM client is not properly configured
    """
    try:
        from quack_core.integrations.llms.models import ChatMessage, LLMOptions, RoleType
        from quack_core.integrations.llms.service import LLMIntegration
    except ImportError as e:
        logger.error("Failed to import LLM integration: %s", str(e))
        raise ImportError(
            "LLM integration is not properly configured. "
            "Please ensure quack_core.integrations.llms is available."
        ) from e

    # Load configuration
    config = _load_config()
    llm_config = config["llm"]

    try:
        # Initialize the LLM integration service
        llm_service = LLMIntegration(
            provider=provider, model=model, enable_fallback=True
        )
        init_result = llm_service.initialize()

        if not init_result.success:
            logger.error("Failed to initialize LLM service: %s", init_result.error)
            raise RuntimeError(f"Failed to initialize LLM service: {init_result.error}")

        # Create messages
        system_prompt = _create_system_prompt(strategy_name, config)
        user_prompt = _create_user_prompt(task_description, schema, examples)

        messages = [
            ChatMessage(role=RoleType.SYSTEM, content=system_prompt),
            ChatMessage(role=RoleType.USER, content=user_prompt),
        ]

        # Set options from config
        options = LLMOptions(
            temperature=llm_config.get("temperature", 0.3),
            max_tokens=llm_config.get("max_tokens", 1200),
            top_p=llm_config.get("top_p", 0.95),
            frequency_penalty=llm_config.get("frequency_penalty", 0.0),
            presence_penalty=llm_config.get("presence_penalty", 0.0),
        )

        # Send the chat request
        result = llm_service.chat(messages, options)

        if not result.success:
            logger.error("LLM request failed: %s", result.error)
            return task_description

        enhanced_prompt = result.content.strip()

        # Validate the response - ensure we got something useful
        if not enhanced_prompt or len(enhanced_prompt) < len(task_description):
            logger.warning(
                "LLM returned a shorter prompt than the original. Using original."
            )
            return task_description

        return enhanced_prompt

    except Exception as e:
        logger.error("Error during LLM prompt enhancement: %s", str(e))
        # Fallback to the original prompt if enhancement fails
        return task_description


def _create_system_prompt(strategy_name: str | None, config: dict) -> str:
    """
    Create the system prompt for the LLM enhancer based on configuration.

    Instead of hardcoding, this uses the configured system prompt template
    or falls back to a reasonable default.

    Args:
        strategy_name: Optional name of the strategy being used
        config: Configuration dictionary

    Returns:
        A system prompt for the LLM
    """
    # Get the prompt template from config
    prompt_template = config.get("system_prompt", {}).get(
        "prompt_engineer", DEFAULT_CONFIG["system_prompt"]["prompt_engineer"]
    )

    # Format strategy information
    strategy_info = f"using the '{strategy_name}' strategy" if strategy_name else ""

    # Format and return the prompt
    return prompt_template.format(strategy=strategy_info).strip()


def _create_user_prompt(
    task_description: str, schema: str | None, examples: list[str] | str | None
) -> str:
    """
    Create the user prompt for the LLM enhancer.

    Args:
        task_description: The basic task description
        schema: Optional schema for structured output
        examples: Optional examples for few-shot learning

    Returns:
        A formatted user prompt
    """
    user_prompt_parts = [f"TASK:\n{task_description}"]

    if schema:
        user_prompt_parts.append(f"SCHEMA:\n{schema}")

    if examples:
        if isinstance(examples, Sequence) and not isinstance(examples, str):
            examples_str = "\n\n".join(examples)
        else:
            examples_str = examples
        user_prompt_parts.append(f"EXAMPLES:\n{examples_str}")

    return "\n\n".join(user_prompt_parts)


def count_prompt_tokens(
    task_description: str,
    schema: str | None = None,
    examples: list[str] | str | None = None,
    strategy_name: str | None = None,
) -> int | None:
    """
    Count the tokens in a prompt that would be sent to the LLM.

    This is useful for estimating costs and ensuring the prompt fits
    within the model's context window.

    Args:
        task_description: The basic task description
        schema: Optional schema for structured output
        examples: Optional examples for few-shot learning
        strategy_name: Name of the strategy being used

    Returns:
        Token count if successful, None if token counting failed
    """
    try:
        from quack_core.integrations.llms.models import ChatMessage, RoleType
        from quack_core.integrations.llms.service import LLMIntegration

        # Load configuration
        config = _load_config()

        # Initialize the LLM integration service
        llm_service = LLMIntegration(enable_fallback=True)
        init_result = llm_service.initialize()

        if not init_result.success:
            logger.error("Failed to initialize LLM service: %s", init_result.error)
            return None

        # Create messages
        system_prompt = _create_system_prompt(strategy_name, config)
        user_prompt = _create_user_prompt(task_description, schema, examples)

        messages = [
            ChatMessage(role=RoleType.SYSTEM, content=system_prompt),
            ChatMessage(role=RoleType.USER, content=user_prompt),
        ]

        # Count tokens
        result = llm_service.count_tokens(messages)

        if result.success:
            return result.content
        else:
            logger.error("Failed to count tokens: %s", result.error)
            return None

    except Exception as e:
        logger.error("Error counting tokens: %s", str(e))
        return None
