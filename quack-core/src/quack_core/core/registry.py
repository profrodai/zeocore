# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/registry.py
# module: quack_core.core.registry
# role: module
# neighbors: __init__.py, jobs.py, mime.py, serialization.py
# exports: Operation, OperationRegistry, get_registry, reset_registry
# git_branch: feat/9-make-setup-work
# git_commit: f4879df3
# === QV-LLM:END ===



"""
Operation registry for QuackCore.

This module provides a centralized registry for operations that can be
invoked via different adapters (HTTP, CLI, MCP). Operations are registered
with their callable, request/response models, and metadata.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from quack_core.core.logging import get_logger

logger = get_logger(__name__)

TRequest = TypeVar("TRequest", bound=BaseModel)
TResponse = TypeVar("TResponse")


@dataclass
class Operation(Generic[TRequest, TResponse]):
    """
    Represents a registered operation.

    Attributes:
        name: Unique operation identifier (e.g., "quackmedia.slice_video")
        callable: The function to execute
        request_model: Pydantic model for request validation
        response_model: Pydantic model for response validation (optional)
        description: Human-readable description
        tags: Categorization tags
    """

    name: str
    callable: Callable[[TRequest], TResponse]
    request_model: type[TRequest]
    response_model: type[TResponse] | None = None
    description: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate operation definition."""
        if not self.name:
            raise ValueError("Operation name is required")
        if not callable(self.callable):
            raise ValueError(f"Operation {self.name} callable is not callable")


class OperationRegistry:
    """
    Central registry for QuackCore operations.

    Operations are registered with their metadata and can be looked up
    by name. This provides a single source of truth for what operations
    are available across all adapters.
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._operations: dict[str, Operation[Any, Any]] = {}
        logger.debug("OperationRegistry initialized")

    def register(
            self,
            name: str,
            callable: Callable[[TRequest], TResponse],
            request_model: type[TRequest],
            response_model: type[TResponse] | None = None,
            description: str = "",
            tags: list[str] | None = None,
    ) -> None:
        """
        Register an operation.

        Args:
            name: Unique operation identifier
            callable: Function to execute
            request_model: Pydantic model for request validation
            response_model: Pydantic model for response validation
            description: Human-readable description
            tags: Categorization tags

        Raises:
            ValueError: If operation already registered
        """
        if name in self._operations:
            raise ValueError(f"Operation {name} already registered")

        op = Operation(
            name=name,
            callable=callable,
            request_model=request_model,
            response_model=response_model,
            description=description,
            tags=tags or [],
        )

        self._operations[name] = op
        logger.info(f"Registered operation: {name}")

    def get(self, name: str) -> Operation[Any, Any] | None:
        """
        Get an operation by name.

        Args:
            name: Operation identifier

        Returns:
            Operation if found, None otherwise
        """
        return self._operations.get(name)

    def get_or_error(self, name: str) -> Operation[Any, Any]:
        """
        Get an operation by name or raise error.

        Args:
            name: Operation identifier

        Returns:
            Operation

        Raises:
            ValueError: If operation not found
        """
        op = self.get(name)
        if op is None:
            raise ValueError(f"Operation not found: {name}")
        return op

    def list_operations(self, tags: list[str] | None = None) -> list[str]:
        """
        List all registered operation names.

        Args:
            tags: Optional tags to filter by

        Returns:
            List of operation names
        """
        if tags is None:
            return list(self._operations.keys())

        return [
            name
            for name, op in self._operations.items()
            if any(tag in op.tags for tag in tags)
        ]

    def has_operation(self, name: str) -> bool:
        """
        Check if an operation is registered.

        Args:
            name: Operation identifier

        Returns:
            True if registered, False otherwise
        """
        return name in self._operations

    def unregister(self, name: str) -> bool:
        """
        Unregister an operation.

        Args:
            name: Operation identifier

        Returns:
            True if unregistered, False if not found
        """
        if name in self._operations:
            del self._operations[name]
            logger.info(f"Unregistered operation: {name}")
            return True
        return False

    def clear(self) -> None:
        """Clear all registered operations."""
        self._operations.clear()
        logger.info("Registry cleared")


# Global registry instance
_registry: OperationRegistry | None = None


def get_registry() -> OperationRegistry:
    """
    Get the global operation registry.

    Returns:
        Global registry instance
    """
    global _registry
    if _registry is None:
        _registry = OperationRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global registry (for testing)."""
    global _registry
    _registry = None


async def invoke_operation(op: Operation[Any, Any], params: dict[str, Any]) -> dict[
    str, Any]:
    """
    Invoke an operation with consistent semantics.

    This is the single source of truth for operation execution across
    routes, job runners, and other adapters.

    Args:
        op: Operation to invoke
        params: Parameters as a dictionary

    Returns:
        Result as a JSON-serializable dictionary

    Raises:
        ValidationError: If params don't match request model
        Exception: Any error from operation execution
    """
    import inspect
    import json

    # Validate params against request model
    validated_params = op.request_model(**params)

    # Execute operation (handles sync, async, partials, wrappers)
    result = op.callable(validated_params)
    if inspect.isawaitable(result):
        result = await result

    # Serialize via response model if provided
    if op.response_model and result is not None:
        if isinstance(result, dict):
            # Validate against response model
            response_obj = op.response_model(**result)
            result = response_obj.model_dump()
        else:
            # If result is not a dict, try to validate it directly
            response_obj = op.response_model(result) if not isinstance(result,
                                                                       op.response_model) else result
            result = response_obj.model_dump() if hasattr(response_obj,
                                                          'model_dump') else {
                "value": result}

    # Normalize return to dict
    if isinstance(result, dict):
        final_result = result
    else:
        final_result = {"value": result}

    # Ensure JSON serializable
    try:
        json.dumps(final_result)
    except (TypeError, ValueError) as e:
        raise ValueError(
            f"Operation {op.name} returned non-JSON-serializable result: {e}. "
            "Results must be JSON-serializable dicts."
        ) from e

    return final_result