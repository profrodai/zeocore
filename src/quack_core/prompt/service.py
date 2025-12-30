# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/prompt/service.py
# module: quack_core.prompt.service
# role: service
# neighbors: __init__.py, models.py, plugin.py
# exports: PromptService
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===


from quack_core.lib.logging import get_logger
from quack_core.prompt._internal.enhancer import enhance_with_llm_safe
from quack_core.prompt._internal.registry import StrategyRegistry
from quack_core.prompt._internal.selector import select_best_strategy
from quack_core.prompt.api.public.results import (
    GetStrategyResult,
    LoadPackResult,
    PromptRenderResult,
    RegisterStrategyResult,
    StrategyListResult,
)
from quack_core.prompt.models import PromptStrategy, StrategyInfo


class PromptService:
    """
    Core service for managing and rendering prompts.
    Does not use global state. Owns its own registry.
    """

    def __init__(self, load_defaults: bool = True) -> None:
        self.logger = get_logger(__name__)
        self._registry = StrategyRegistry()

        if load_defaults:
            self.load_pack("internal")

    def load_pack(self, pack_name: str) -> LoadPackResult:
        """
        Explicitly load a strategy pack.
        """
        try:
            if pack_name == "internal":
                from quack_core.prompt.packs.internal import load as load_internal
                count = load_internal(self._registry)
                return LoadPackResult(success=True, loaded_count=count)

            return LoadPackResult(success=False, error=f"Unknown pack: {pack_name}")

        except Exception as e:
            self.logger.error(f"Failed to load pack {pack_name}: {e}")
            return LoadPackResult(success=False, error=str(e))

    def register_strategy(self, strategy: PromptStrategy) -> RegisterStrategyResult:
        """Register a new strategy."""
        try:
            self._registry.register(strategy)
            return RegisterStrategyResult(success=True, strategy_id=strategy.id)
        except ValueError as e:
            return RegisterStrategyResult(success=False, error=str(e))
        except Exception as e:
            self.logger.error(f"Register strategy failed: {e}")
            return RegisterStrategyResult(success=False, error=str(e))

    def get_strategy(self, strategy_id: str) -> GetStrategyResult:
        """Get a specific strategy."""
        strat = self._registry.get(strategy_id)
        if not strat:
            return GetStrategyResult(success=False,
                                     error=f"Strategy '{strategy_id}' not found")
        return GetStrategyResult(success=True, strategy=strat)

    def list_strategies(self) -> StrategyListResult:
        """List all available strategies as safe Info objects."""
        safe_list = [StrategyInfo.from_strategy(s) for s in self._registry.list_all()]
        return StrategyListResult(success=True, strategies=safe_list)

    def render(
            self,
            raw_prompt: str,
            *,
            schema: str | None = None,
            examples: list[str] | str | None = None,
            tags: list[str] | None = None,
            strategy_id: str | None = None,
            use_llm: bool = False,
            llm_model: str | None = None,
            llm_provider: str | None = None,
            **kwargs
    ) -> PromptRenderResult:
        """
        Render a prompt using a selected strategy.
        """
        try:
            # 1. Select Strategy
            strategy = None
            if strategy_id:
                strategy = self._registry.get(strategy_id)
                if not strategy:
                    return PromptRenderResult(
                        success=False,
                        error=f"Strategy '{strategy_id}' not found"
                    )
            else:
                # Pass kwargs so selector knows if 'data' or other keys exist
                strategy = select_best_strategy(self._registry, tags, schema, examples,
                                                extra_inputs=kwargs)

            if not strategy:
                return PromptRenderResult(
                    success=False,
                    error="No suitable strategy found and no defaults available."
                )

            # 2. Prepare Inputs
            # Strict aliases only for "Task Description" synonyms.
            inputs = {
                # Standard args
                "task_description": raw_prompt,
                "schema": schema,
                "examples": examples,

                # Computed/Derived
                "example": examples[0] if isinstance(examples,
                                                     list) and examples else examples,

                # Strict Aliases (ONLY semantically equivalent to "Task Description")
                "prompt_text": raw_prompt,
                "task_goal": raw_prompt,
                "main_task": raw_prompt,
                "strategy": raw_prompt,  # Input for System Prompt Engineer
            }

            # Merge explicit kwargs (allows passing 'data', 'tools', 'source_code', etc.)
            inputs.update(kwargs)

            # 3. Validation
            render_kwargs = {}
            missing_fields = []

            for var in strategy.input_vars:
                if var in inputs and inputs[var] is not None:
                    render_kwargs[var] = inputs[var]
                else:
                    missing_fields.append(var)

            if missing_fields:
                return PromptRenderResult(
                    success=False,
                    error=f"Missing required inputs for strategy '{strategy.id}': {', '.join(missing_fields)}"
                )

            # 4. Render
            rendered_prompt = strategy.render_fn(**render_kwargs)

            metadata = {
                "strategy_id": strategy.id,
                "strategy_origin": strategy.origin,
                "input_vars": list(render_kwargs.keys())
            }

            # 5. Optional Enhancement
            if use_llm:
                rendered_prompt = enhance_with_llm_safe(
                    rendered_prompt,
                    model=llm_model,
                    provider=llm_provider
                )
                metadata["enhanced_by_llm"] = True

            # 6. Metrics
            estimated_words = len(rendered_prompt.split()) if rendered_prompt else 0

            return PromptRenderResult(
                success=True,
                prompt=rendered_prompt,
                strategy_id=strategy.id,
                strategy_label=strategy.label,
                metadata=metadata,
                estimated_words=estimated_words
            )

        except Exception as e:
            self.logger.error(f"Render failed: {e}")
            return PromptRenderResult(success=False, error=str(e))
