# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/plugin.py
# module: quack_core.prompt.plugin
# role: plugin
# neighbors: __init__.py, service.py, models.py
# exports: PromptPlugin, create_plugin
# git_branch: refactor/toolkitWorkflow
# git_commit: 5d876e8
# === QV-LLM:END ===

from quack_core.prompt.api.public.results import PromptRenderResult
from quack_core.prompt.service import PromptService


class PromptPlugin:
    """
    QuackCore plugin wrapping the PromptService.
    """
    def __init__(self):
        self.name = "prompt"
        self._service = PromptService(load_defaults=True)

    def render(self, raw_prompt: str, **kwargs) -> PromptRenderResult:
        """
        Render a prompt using the underlying PromptService.
        """
        return self._service.render(raw_prompt, **kwargs)

    def get_service(self) -> PromptService:
        """Access the underlying PromptService."""
        return self._service

def create_plugin() -> PromptPlugin:
    return PromptPlugin()
