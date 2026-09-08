"""Managed environments never substitute a provider or fabricate live success."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.environment import integration_backend
from zeo_core.integrations.llms.registry import get_llm_client

if TYPE_CHECKING:
    from . import LLMIntegration as PublicLLMIntegration
    from .integration import LLMIntegration


def initialize_managed(
    self: LLMIntegration | PublicLLMIntegration, config: dict[str, Any]
) -> IntegrationResult:
    provider = self.provider or config.get("default_provider", "openai")
    fixture = integration_backend() == "fixture"
    if (fixture and provider != "mock") or (not fixture and provider == "mock"):
        self._initialized = False
        return IntegrationResult.error_result(
            "Select mock explicitly for fixture runs and a real provider for live runs"
        )
    if provider not in {"openai", "anthropic", "ollama", "mock"}:
        self._initialized = False
        return IntegrationResult.error_result("Unsupported managed LLM provider")
    settings = config.get(provider, {})
    key = (
        self.api_key
        or settings.get("api_key")
        or os.environ.get(f"{provider.upper()}_API_KEY")
    )
    if provider in {"openai", "anthropic"} and not key:
        self._initialized = False
        return IntegrationResult.error_result(
            "The selected environment has no API key for this LLM provider"
        )
    args: dict[str, Any] = {
        "model": self.model or settings.get("default_model"),
        "api_key": key,
        "timeout": config.get("timeout", 60),
        "retry_count": config.get("retry_count", 0),
        "log_level": self.log_level,
    }
    if provider in {"openai", "anthropic", "ollama"}:
        args["api_base"] = settings.get("api_base")
    if provider == "openai":
        args["organization"] = settings.get("organization") or os.environ.get(
            "OPENAI_ORG_ID"
        )
    try:
        self.client = get_llm_client(provider=provider, **args)
    except Exception:
        self.client = None
        self._initialized = False
        return IntegrationResult.error_result(
            "The selected LLM provider could not initialize; no fallback was used"
        )
    self._using_mock = provider == "mock"
    self._fallback_client = None
    self._initialized = True
    return IntegrationResult.success_result(
        message=f"Initialized managed LLM provider: {provider}"
    )
