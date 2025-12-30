# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/adapters/http/routes/operations.py
# module: quack_core.adapters.http.routes.operations
# role: operations
# neighbors: __init__.py, health.py, jobs.py
# exports: list_operations
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===


"""
Operations routes for listing and invoking operations directly.

This replaces the old "quackmedia" routes with a generic operations
interface that works with the registry.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from quack_core.adapters.http.dependencies import (
    get_registry,
    require_auth,
)
from quack_core.lib.registry import OperationRegistry, invoke_operation

router = APIRouter()


@router.get("", dependencies=[Depends(require_auth)])
def list_operations(
        registry: Annotated[OperationRegistry, Depends(get_registry)],
        tags: list[str] | None = None,
) -> dict[str, Any]:
    """
    List all registered operations.

    Args:
        registry: Operation registry (injected)
        tags: Optional tags to filter by

    Returns:
        List of operation names and metadata
    """
    op_names = registry.list_operations(tags=tags)

    operations = []
    for name in op_names:
        op = registry.get(name)
        if op:
            operations.append({
                "name": op.name,
                "description": op.description,
                "tags": op.tags,
            })

    return {"operations": operations}


@router.post("/{op_name}", dependencies=[Depends(require_auth)])
async def invoke_operation_route(
        op_name: str,
        params: dict[str, Any],
        registry: Annotated[OperationRegistry, Depends(get_registry)],
) -> dict[str, Any]:
    """
    Invoke an operation synchronously or asynchronously.

    Args:
        op_name: Operation name
        params: Operation parameters
        registry: Operation registry (injected)

    Returns:
        Operation result with stable schema

    Raises:
        HTTPException: With structured error response
    """
    # Get operation
    op = registry.get(op_name)
    if op is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "OPERATION_NOT_FOUND",
                    "message": f"Operation not found: {op_name}",
                    "details": {"op_name": op_name},
                }
            },
        )

    try:
        # Use shared invoker
        result = await invoke_operation(op, params)
        return {"success": True, "data": result}

    except ValidationError as e:
        # Pydantic validation errors
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": e.errors(),
                }
            },
        )

    except Exception as e:
        # All other errors
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "OPERATION_FAILED",
                    "message": f"Operation execution failed: {str(e)}",
                    "details": {
                        "op_name": op_name,
                        "error_type": type(e).__name__,
                    },
                }
            },
        )
