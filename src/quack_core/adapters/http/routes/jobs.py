# quack-core/src/quack_core/adapters/http/routes/jobs.py
"""
Job management routes.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from typing import Optional

from ..models import JobRequest, JobResponse, JobStatus
from ..auth import require_bearer
from ..jobs import enqueue, get_status
from ..config import HttpAdapterConfig

router = APIRouter()

# Global config reference
_cfg: Optional[HttpAdapterConfig] = None


def set_config(cfg: HttpAdapterConfig) -> None:
    """Set the global config reference."""
    global _cfg
    _cfg = cfg


def get_cfg() -> HttpAdapterConfig:
    """Get the current configuration."""
    if not _cfg:
        raise HTTPException(500, "HTTP adapter not properly initialized")
    return _cfg


@router.post("", response_model=JobResponse)
def start_job(
        req: JobRequest,
        request: Request,
        cfg: HttpAdapterConfig = Depends(get_cfg),
        idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    """Start a new job."""
    require_bearer(request, cfg)

    job_id = enqueue(
        op=req.op,
        params=req.params,
        callback_url=str(req.callback_url) if req.callback_url else None,
        idempotency_key=idempotency_key or req.idempotency_key,
    )

    return JobResponse(job_id=job_id).model_dump()


@router.get("/{job_id}", response_model=JobStatus)
def job_status(
        job_id: str,
        request: Request,
        cfg: HttpAdapterConfig = Depends(get_cfg)
):
    """Get job status."""
    require_bearer(request, cfg)

    status = get_status(job_id)
    if not status:
        raise HTTPException(404, "Job not found")

    return JobStatus(**status).model_dump()