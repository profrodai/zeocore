# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/adapters/http/routes/health.py
# module: quack_core.adapters.http.routes.health
# role: adapters
# neighbors: __init__.py, jobs.py, operations.py
# exports: health_live, health_ready
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
# === QV-LLM:END ===

"""
Health check routes.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/live")
def health_live():
    """Liveness check - no auth required."""
    return {"ok": True}


@router.get("/ready")
def health_ready():
    """Readiness check - no auth required."""
    return {"ok": True}
