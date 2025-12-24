# quack-core/src/quack_core/adapters/http/routes/health.py
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