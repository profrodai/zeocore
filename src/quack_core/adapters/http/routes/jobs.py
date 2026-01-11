# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/adapters/http/routes/jobs.py
# module: quack_core.adapters.http.routes.jobs
# role: adapters
# neighbors: __init__.py, operations.py, health.py
# exports: start_job, job_status
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===


"""
Job management routes with dependency injection.
"""

import hashlib
import json
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import ValidationError
from quack_core.adapters.http.dependencies import (
    get_job_runner,
    get_job_store,
    get_registry,
    require_auth,
)
from quack_core.adapters.http.models import JobRequest, JobResponse
from quack_core.adapters.http.models import JobStatus as JobStatusModel
from quack_core.core.jobs import JobData, JobRunner, JobStatus, JobStore
from quack_core.core.registry import OperationRegistry

router = APIRouter()


def _generate_job_id() -> str:
    """Generate a new job ID."""
    return str(uuid.uuid4())


def _compute_idempotency_hash(op: str, params: dict, key: str) -> str:
    """Compute idempotency hash."""
    data = {"op": op, "params": params, "key": key}
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()


@router.post("", response_model=JobResponse, dependencies=[Depends(require_auth)])
def start_job(
        req: JobRequest,
        registry: Annotated[OperationRegistry, Depends(get_registry)],
        store: Annotated[JobStore, Depends(get_job_store)],
        runner: Annotated[JobRunner, Depends(get_job_runner)],
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JobResponse:
    """
    Start a new job.

    Args:
        req: Job request
        registry: Operation registry (injected)
        store: Job store (injected)
        runner: Job runner (injected)
        idempotency_key: Optional idempotency key

    Returns:
        Job response with job ID

    Raises:
        HTTPException: If operation not found or validation fails
    """
    # Get operation
    op = registry.get(req.op)
    if op is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "OPERATION_NOT_FOUND",
                    "message": f"Operation not found: {req.op}",
                    "details": {"op_name": req.op},
                }
            },
        )

    # Validate params immediately (fail fast)
    try:
        validated_params = op.request_model(**req.params)
        # Store serialized params for consistent behavior
        serialized_params = validated_params.model_dump()
    except ValidationError as e:
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

    # Handle idempotency
    final_key = idempotency_key or req.idempotency_key
    idempotency_hash = None

    if final_key:
        idempotency_hash = _compute_idempotency_hash(req.op, serialized_params,
                                                     final_key)
        existing = store.find_by_idempotency_hash(idempotency_hash)
        if existing:
            return JobResponse(job_id=existing.job_id, status=existing.status.value)

    # Create new job
    job_id = _generate_job_id()
    job_data = JobData(
        job_id=job_id,
        op=req.op,
        params=serialized_params,
        status=JobStatus.QUEUED,
        created_at=time.time(),
        callback_url=str(req.callback_url) if req.callback_url else None,
        idempotency_hash=idempotency_hash,
    )

    store.create(job_data)

    # Submit to runner
    runner.submit(
        job_id=job_id,
        op_name=req.op,
        params=serialized_params,
        callback_url=str(req.callback_url) if req.callback_url else None,
    )

    return JobResponse(job_id=job_id, status=JobStatus.QUEUED.value)


@router.get("/{job_id}", response_model=JobStatusModel,
            dependencies=[Depends(require_auth)])
def job_status(
        job_id: str,
        store: Annotated[JobStore, Depends(get_job_store)],
) -> JobStatusModel:
    """
    Get job status.

    Args:
        job_id: Job identifier
        store: Job store (injected)

    Returns:
        Job status

    Raises:
        HTTPException: If job not found
    """
    job_data = store.get(job_id)
    if job_data is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "JOB_NOT_FOUND",
                    "message": f"Job not found: {job_id}",
                    "details": {"job_id": job_id},
                }
            },
        )

    return JobStatusModel(
        job_id=job_data.job_id,
        status=job_data.status.value,
        result=job_data.result,
        error=job_data.error,
    )
