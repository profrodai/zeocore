# quack-core/src/quack_core/prompt/booster.py
"""
Main PromptBooster module for quack_core.

This module provides the PromptBooster class, which is the main entry point
for enhancing prompts using various strategies.
"""

from typing import Any

from quack_core.fs.service import standalone
from quack_core.logging import get_logger

from .registry import find_strategies_by_tags, get_all_strategies, get_strategy_by_id
from .strategy_base import PromptStrategy

# Set up logger
logger = get_logger(__name__)


class PromptBooster:
    """
    A class that takes a basic user prompt and upgrades it using codified strategies.

    PromptBooster serves as the standard mechanism for QuackTools to:
      - Define their prompt needs declaratively
      - Get strategy-aligned prompts
      - Introspect, audit, and optimize prompt generation
      - Apply LLM-enhanced polishing when needed

    Attributes:
        raw_prompt: The original user-defined prompt.
        schema: Optional schema for structured output.
        examples: Optional examples for few-shot learning.
        tags: Optional tags to help select an appropriate strategy.
        strategy_id: Optional specific strategy ID to use.
        strategy: The selected PromptStrategy.
        optimized_prompt: The rendered, optimized prompt.
    """

    def __init__(
        self,
        raw_prompt: str,
        schema: str | None = None,
        examples: list[str] | str | None = None,
        tags: list[str] | None = None,
        strategy_id: str | None = None,
    ):
        """
        Initialize a new PromptBooster.

        Args:
            raw_prompt: The original user-defined prompt.
            schema: Optional schema for structured output.
            examples: Optional examples for few-shot learning.
            tags: Optional tags to help select an appropriate strategy.
            strategy_id: Optional specific strategy ID to use.
        """
        self.raw_prompt = raw_prompt
        self.schema = schema
        self.examples = examples
        self.tags = tags or []
        self.strategy_id = strategy_id
        self.strategy: PromptStrategy | None = None
        self.optimized_prompt: str | None = None

        # If strategy_id is provided, select it immediately.
        if self.strategy_id:
            try:
                self.select_strategy(self.strategy_id)
            except KeyError:
                logger.warning(
                    "Strategy with ID '%s' not found. Will select strategy during render.",
                    strategy_id,
                )

    def select_strategy(self, strategy_id: str | None = None) -> PromptStrategy:
        """
        Select a prompt strategy to use for rendering.

        Args:
            strategy_id: Optional specific strategy ID to use.

        Returns:
            The selected PromptStrategy.

        Raises:
            KeyError: If the specified strategy ID is not found.
            ValueError: If no suitable strategy could be found.
        """
        if strategy_id:
            # Use the specified strategy if provided.
            self.strategy = get_strategy_by_id(strategy_id)
            self.strategy_id = strategy_id
            return self.strategy

        # Try to select based on the provided tags.
        if self.tags:
            strategies = find_strategies_by_tags(self.tags)
            if strategies:
                # Select the first matching strategy (most relevant should be first).
                self.strategy = strategies[0]
                self.strategy_id = self.strategy.id
                return self.strategy

        # Check if we have schema and examples to help select a strategy.
        if self.schema:
            if isinstance(self.examples, list) and len(self.examples) > 1:
                try:
                    self.strategy = get_strategy_by_id("multi-shot-structured")
                    self.strategy_id = "multi-shot-structured"
                    return self.strategy
                except KeyError:
                    pass
            elif self.examples:
                try:
                    self.strategy = get_strategy_by_id("single-shot-structured")
                    self.strategy_id = "single-shot-structured"
                    return self.strategy
                except KeyError:
                    pass

        # Default to the first available strategy if we couldn't find a match.
        strategies = get_all_strategies()
        if not strategies:
            raise ValueError("No prompt strategies are registered")

        self.strategy = strategies[0]
        self.strategy_id = self.strategy.id
        return self.strategy

    def render(
        self,
        use_llm: bool = False,
        model: str | None = None,
        provider: str | None = None,
    ) -> str:
        """
        Render the prompt using the selected strategy.

        Args:
            use_llm: Whether to use an LLM to enhance the prompt.
            model: Optional specific model to use for enhancement (e.g., "gpt-4o").
            provider: Optional specific provider to use (e.g., "openai" or "anthropic").

        Returns:
            The rendered prompt.
        """
        if not self.strategy:
            self.select_strategy()

        inputs = self._prepare_inputs()

        # Render using the strategy's render function.
        used_inputs = {k: v for k, v in inputs.items() if k in self.strategy.input_vars}
        self.optimized_prompt = self.strategy.render_fn(**used_inputs)

        # Optionally enhance with LLM.
        if use_llm:
            try:
                from .enhancer import enhance_with_llm

                enhanced_prompt = enhance_with_llm(
                    task_description=self.raw_prompt,
                    schema=self.schema,
                    examples=self.examples,
                    strategy_name=self.strategy.id,
                    model=model,
                    provider=provider,
                )
                self.optimized_prompt = enhanced_prompt
            except (ImportError, RuntimeError) as e:
                logger.warning(
                    "LLM enhancement failed: %s. Using strategy-based prompt instead.",
                    str(e),
                )

        return self.optimized_prompt

    def _prepare_inputs(self) -> dict[str, Any]:
        """Prepare the inputs for the strategy render function."""
        return {
            "task_description": self.raw_prompt,
            "schema": self.schema,
            "examples": self.examples,
            # Include other common inputs that might be needed by strategies.
            "example": self.examples[0]
            if isinstance(self.examples, list) and self.examples
            else self.examples,
            "final_instruction": None,  # Needed for some strategies.
            "tools": None,  # Needed for some strategies.
        }

    def metadata(self) -> dict[str, Any]:
        """
        Get metadata about the current prompt.

        Returns:
            A dictionary containing metadata about the prompt and strategy.
        """
        meta = {
            "raw_prompt": self.raw_prompt,
            "has_schema": bool(self.schema),
            "has_examples": bool(self.examples),
            "tags": self.tags,
        }

        if self.strategy:
            meta["strategy"] = {
                "id": self.strategy.id,
                "label": self.strategy.label,
                "description": self.strategy.description,
                "tags": self.strategy.tags,
                "origin": self.strategy.origin,
            }

        if self.optimized_prompt:
            meta["optimized_prompt_length"] = len(self.optimized_prompt)

        # Try to estimate token count.
        token_count = self.estimate_token_count()
        if token_count is not None:
            meta["estimated_token_count"] = token_count

        return meta

    def estimate_token_count(self) -> int | None:
        """
        Estimate the token count for the current prompt.

        This method uses the token counting capability from the LLM integration
        to estimate how many tokens the prompt will use.

        Returns:
            Estimated token count if successful, None otherwise.
        """
        try:
            from .enhancer import count_prompt_tokens

            token_count = count_prompt_tokens(
                task_description=self.raw_prompt,
                schema=self.schema,
                examples=self.examples,
                strategy_name=self.strategy.id if self.strategy else None,
            )

            return token_count
        except (ImportError, Exception) as e:
            logger.debug("Failed to estimate token count: %s", str(e))
            return None

    def explain(self) -> str:
        """
        Get an explanation of the selected strategy.

        Returns:
            A string explaining the strategy that was selected.
        """
        if not self.strategy:
            return "No strategy selected."

        s = self.strategy
        origin_info = f"Origin: {s.origin}" if s.origin else "Origin: unknown"

        return f"""{s.label}: {s.description}
Tags: {", ".join(s.tags)}
{origin_info}"""

    def export(self, path: str) -> None:
        """
        Export the prompt and metadata to a file.

        Args:
            path: Path (as a string) to save the export file.

        Raises:
            OSError: If the file cannot be written.
        """
        export_data = {
            "prompt": self.optimized_prompt or self.raw_prompt,
            "metadata": self.metadata(),
            "explanation": self.explain() if self.strategy else "No strategy selected.",
        }

        try:
            # Ensure parent directory exists using quack_core.standalone.
            # Convert path to string if it's a Path object
            path_str = str(path)

            # Get the parent directory
            split_result = standalone.split_path(path_str)
            if split_result.success and split_result.data:
                path_parts = split_result.data[:-1]  # All parts except the last
                parent_dir_result = standalone.join_path(*path_parts)
                if parent_dir_result.success:
                    parent_dir = parent_dir_result.data
                    standalone.create_directory(parent_dir, exist_ok=True)

            # Determine output format based on file extension.
            if path_str.lower().endswith(".json"):
                result = standalone.write_json(path_str, export_data, indent=2)
                if not result.success:
                    raise OSError(f"Failed to export prompt: {result.error}")
            else:
                # Format each section.
                content = f"# Prompt\n\n{export_data['prompt']}\n\n"
                content += "# Metadata\n\n"

                try:
                    import tempfile

                    with tempfile.NamedTemporaryFile(
                            mode="w+", delete=False
                    ) as temp_file:
                        temp_path = temp_file.name

                    json_result = standalone.write_json(
                        temp_path, export_data["metadata"], indent=2
                    )
                    if json_result.success:
                        read_result = standalone.read_text(temp_path)
                        if read_result.success:
                            content += f"{read_result.content}\n\n"
                            standalone.delete(temp_path, missing_ok=True)
                        else:
                            raise ValueError("Failed to read temporary JSON file")
                    else:
                        raise ValueError("Failed to write temporary JSON file")
                except Exception as e:
                    logger.debug("Using fallback JSON formatting: %s", str(e))
                    import json

                    content += f"{json.dumps(export_data['metadata'], indent=2)}\n\n"

                content += f"# Explanation\n\n{export_data['explanation']}\n"

                result = standalone.write_text(path_str, content)
                if not result.success:
                    raise OSError(f"Failed to export prompt: {result.error}")

            logger.info("Exported prompt to %s", path_str)

        except Exception as e:
            logger.error("Failed to export prompt: %s", str(e))
            raise OSError(f"Failed to export prompt: {str(e)}") from e
