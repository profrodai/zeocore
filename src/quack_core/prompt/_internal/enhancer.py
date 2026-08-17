from typing import Any

from quack_core.core.logging import get_logger

logger = get_logger(__name__)


def enhance_with_llm_safe(
    prompt_text: str,
    model: str | None = None,
    provider: str | None = None,
    **kwargs: Any,  # noqa: ANN401 -- genuinely dynamic: forward-compat signature reservation, unused today, no fixed shape to constrain it to
) -> str:
    """
    Safely attempts to enhance a prompt using the LLM integration.
    Returns original prompt if LLM is unavailable or fails.
    """
    try:
        from quack_core.integrations.llms.models import (
            ChatMessage,
            LLMOptions,
            RoleType,
        )
        from quack_core.integrations.llms.service import LLMIntegration

        # Initialize service
        llm_service = LLMIntegration(
            provider=provider, model=model, enable_fallback=True
        )
        init_res = llm_service.initialize()
        if not init_res.success:
            logger.warning(f"LLM Enhancer unavailable: {init_res.error}")
            return prompt_text

        # Construct Meta-Prompt
        system_prompt = (
            "You are an expert prompt engineer. "
            "Rewrite the following task prompt to be production-ready, "
            "precise, and effective. "
            "ONLY output the rewritten prompt."
        )

        messages = [
            ChatMessage(role=RoleType.SYSTEM, content=system_prompt),
            ChatMessage(role=RoleType.USER, content=prompt_text),
        ]

        result = llm_service.chat(messages, LLMOptions(temperature=0.3))

        if result.success and result.content:
            return result.content.strip()

        return prompt_text

    except ImportError:
        logger.warning("quack_core.integrations.llms not found. Skipping enhancement.")
        return prompt_text
    except Exception as e:
        logger.error(f"Error during prompt enhancement: {e}")
        return prompt_text
