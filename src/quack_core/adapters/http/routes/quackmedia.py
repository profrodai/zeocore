# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/adapters/http/routes/quackmedia.py
# module: quack_core.adapters.http.routes.quackmedia
# role: adapters
# neighbors: __init__.py, health.py, jobs.py
# exports: set_config, get_cfg, slice_video, transcribe_audio, extract_frames
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

"""
QuackMedia convenience routes (synchronous).
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Dict, Any

from ..auth import require_bearer
from ..config import HttpAdapterConfig
from ..jobs import resolve_callable

router = APIRouter()

# Global config reference
_cfg = None


def set_config(cfg):
    global _cfg
    _cfg = cfg


def get_cfg():
    if not _cfg:
        raise HTTPException(500, "HTTP adapter not properly initialized")
    return _cfg


@router.post("/slice")
def slice_video(
        params: Dict[str, Any],
        request: Request,
        cfg=Depends(get_cfg)
):
    """Slice video synchronously."""
    require_bearer(request, cfg)

    try:
        fn = resolve_callable("quack-media.slice_video")
        result = fn(**params)
        return result
    except Exception as e:
        raise HTTPException(500, f"Operation failed: {str(e)}")


@router.post("/transcribe")
def transcribe_audio(
        params: Dict[str, Any],
        request: Request,
        cfg=Depends(get_cfg)
):
    """Transcribe audio synchronously."""
    require_bearer(request, cfg)

    try:
        fn = resolve_callable("quack-media.transcribe_audio")
        result = fn(**params)
        return result
    except Exception as e:
        raise HTTPException(500, f"Operation failed: {str(e)}")


@router.post("/frames")
def extract_frames(
        params: Dict[str, Any],
        request: Request,
        cfg=Depends(get_cfg)
):
    """Extract frames synchronously."""
    require_bearer(request, cfg)

    try:
        fn = resolve_callable("quack-media.extract_frames")
        result = fn(**params)
        return result
    except Exception as e:
        raise HTTPException(500, f"Operation failed: {str(e)}")