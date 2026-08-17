"""
Health check routes.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/live")
def health_live() -> dict[str, bool]:
    """Liveness check - no auth required."""
    return {"ok": True}


@router.get("/ready")
def health_ready() -> dict[str, bool]:
    """Readiness check - no auth required."""
    return {"ok": True}
