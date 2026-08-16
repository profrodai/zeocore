# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_prompt/test_enhancer.py
# === QV-LLM:END ===

"""
Tests for quack_core.prompt._internal.enhancer.enhance_with_llm_safe.

enhance_with_llm_safe crosses a real external boundary (the LLM provider
integration -- network calls, API keys), so per RULING-235 we mock at that
boundary (quack_core.integrations.llms.service.LLMIntegration) rather than
mocking anything inside quack_core.prompt itself. We also exercise the real,
unmocked fallback path since this test environment has no LLM provider
credentials configured, so LLMIntegration.initialize() genuinely fails.
"""

from unittest.mock import MagicMock, patch

import pytest
from quack_core.prompt._internal.enhancer import enhance_with_llm_safe


def test_enhance_with_llm_safe_real_no_credentials_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Real, unmocked call: with no LLM provider API keys configured,
    initialize() fails and the original prompt is returned unchanged.
    Other tests (or leaked global state from the wider suite) may set
    provider credentials in os.environ, so explicitly clear the ones
    the LLM clients look for to make this deterministic.
    """
    for key in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENAI_ORGANIZATION",
    ):
        monkeypatch.delenv(key, raising=False)

    result = enhance_with_llm_safe("Original prompt text")
    assert result == "Original prompt text"


def test_enhance_with_llm_safe_init_failure_returns_original_prompt() -> None:
    mock_init_result = MagicMock(success=False, error="no api key")
    mock_service = MagicMock()
    mock_service.initialize.return_value = mock_init_result

    with patch(
        "quack_core.integrations.llms.service.LLMIntegration",
        return_value=mock_service,
    ):
        result = enhance_with_llm_safe("My prompt", model="gpt-x", provider="openai")

    assert result == "My prompt"
    mock_service.chat.assert_not_called()


def test_enhance_with_llm_safe_success_returns_stripped_content() -> None:
    mock_init_result = MagicMock(success=True)
    mock_chat_result = MagicMock(success=True, content="  Enhanced prompt.  ")
    mock_service = MagicMock()
    mock_service.initialize.return_value = mock_init_result
    mock_service.chat.return_value = mock_chat_result

    with patch(
        "quack_core.integrations.llms.service.LLMIntegration",
        return_value=mock_service,
    ):
        result = enhance_with_llm_safe("My prompt")

    assert result == "Enhanced prompt."
    mock_service.chat.assert_called_once()


def test_enhance_with_llm_safe_chat_failure_returns_original() -> None:
    mock_init_result = MagicMock(success=True)
    mock_chat_result = MagicMock(success=False, content=None)
    mock_service = MagicMock()
    mock_service.initialize.return_value = mock_init_result
    mock_service.chat.return_value = mock_chat_result

    with patch(
        "quack_core.integrations.llms.service.LLMIntegration",
        return_value=mock_service,
    ):
        result = enhance_with_llm_safe("My prompt")

    assert result == "My prompt"


def test_enhance_with_llm_safe_chat_success_empty_content_returns_original() -> None:
    mock_init_result = MagicMock(success=True)
    mock_chat_result = MagicMock(success=True, content="")
    mock_service = MagicMock()
    mock_service.initialize.return_value = mock_init_result
    mock_service.chat.return_value = mock_chat_result

    with patch(
        "quack_core.integrations.llms.service.LLMIntegration",
        return_value=mock_service,
    ):
        result = enhance_with_llm_safe("My prompt")

    assert result == "My prompt"


def test_enhance_with_llm_safe_unexpected_exception_returns_original() -> None:
    with patch(
        "quack_core.integrations.llms.service.LLMIntegration",
        side_effect=RuntimeError("boom"),
    ):
        result = enhance_with_llm_safe("My prompt")

    assert result == "My prompt"


def test_enhance_with_llm_safe_import_error_returns_original() -> None:
    """
    Simulates the ImportError branch by making the integrations.llms.service
    import fail, since we can't easily uninstall the real package.
    """
    import builtins
    from collections.abc import Mapping, Sequence
    from types import ModuleType

    real_import = builtins.__import__

    def fake_import(
        name: str,
        globals: Mapping[str, object] | None = None,  # noqa: A002 -- matches __import__'s real signature
        locals: Mapping[str, object] | None = None,  # noqa: A002 -- matches __import__'s real signature
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> ModuleType:
        if name == "quack_core.integrations.llms.service":
            raise ImportError("simulated missing dependency")
        return real_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=fake_import):
        result = enhance_with_llm_safe("My prompt")

    assert result == "My prompt"
