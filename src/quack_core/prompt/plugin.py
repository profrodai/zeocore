from typing import Any

from quack_core.prompt.api.public.results import PromptRenderResult
from quack_core.prompt.service import PromptService


class PromptPlugin:
    """
    QuackCore plugin wrapping the PromptService.
    """

    def __init__(self) -> None:
        self.name = "prompt"
        self._service = PromptService(load_defaults=True)

    def render(
        self,
        raw_prompt: str,
        **kwargs: Any,  # noqa: ANN401 -- genuinely dynamic: arbitrary prompt-strategy input variables, forwarded verbatim to PromptService.render
    ) -> PromptRenderResult:
        """
        Render a prompt using the underlying PromptService.
        """
        return self._service.render(raw_prompt, **kwargs)

    def get_service(self) -> PromptService:
        """Access the underlying PromptService."""
        return self._service


def create_plugin() -> PromptPlugin:
    return PromptPlugin()
