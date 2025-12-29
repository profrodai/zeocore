# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/adapters/http/models.py
# module: quack_core.adapters.http.models
# role: models
# neighbors: __init__.py, app.py, service.py, config.py, auth.py, dependencies.py (+1 more)
# exports: JobRequest, JobResponse, JobStatus
# git_branch: refactor/toolkitWorkflow
# git_commit: 7e3e554
# === QV-LLM:END ===

"""
Request/Response models for the HTTP adapter.
"""

from typing import Any

from pydantic import BaseModel, HttpUrl


class JobRequest(BaseModel):
    """Request to create a new job."""

    op: str
    params: dict[str, Any]
    callback_url: HttpUrl | None = None
    idempotency_key: str | None = None


class JobResponse(BaseModel):
    """Response when creating a job."""

    job_id: str
    status: str = "queued"


class JobStatus(BaseModel):
    """Status of a job."""

    job_id: str
    status: str  # queued|running|done|error
    result: dict[str, Any] | None = None
    error: str | None = None
