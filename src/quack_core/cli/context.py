# quack-core/src/quack-core/cli/context.py
"""
QuackCore CLI context management.

This module provides the context class for CLI applications, which serves
as a central hub for configuration, logging, and other runtime information.
"""

import logging
import os
from typing import Any

from pydantic import BaseModel, Field

from quack_core.config.models import QuackConfig


class QuackContext(BaseModel):
    """
    Runtime context for QuackCore CLI applications.

    This class encapsulates all the runtime information needed by CLI commands,
    including configuration, logging, file system directories as strings, and
    environment metadata. All paths (e.g. base directory, working directory) are stored as strings.
    """

    config: QuackConfig = Field(description="Loaded and normalized configuration.")

    logger: logging.Logger = Field(
        description="Configured logger for the CLI application."
    )

    base_dir: str = Field(
        description="Base directory for the application (as a string)."
    )

    environment: str = Field(
        description="Current environment (development, test, production)."
    )

    debug: bool = Field(default=False, description="Whether debug mode is enabled.")

    verbose: bool = Field(
        default=False, description="Whether verbose output is enabled."
    )

    working_dir: str = Field(
        default_factory=os.getcwd,
        description="Current working directory as a string.",
    )

    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context data that might be needed by specific commands.",
    )

    model_config = {
        "frozen": True,  # Immutable model instead of @dataclass(frozen=True)
        "arbitrary_types_allowed": True,  # Allow logging.Logger
    }

    def with_extra(self, **kwargs: object) -> "QuackContext":
        """
        Create a new context with additional extra data.

        This method allows for immutable updates to the context's extra data,
        returning a new context instance with the updated values.

        Args:
            **kwargs: Key-value pairs to add to the extra dictionary.

        Returns:
            A new QuackContext with the updated extra dictionary.
        """
        new_extra = self.extra.copy()
        new_extra.update(kwargs)
        return self.model_copy(update={"extra": new_extra})
