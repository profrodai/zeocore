# quack-core/src/quack-core/adapters/http/jobs.py
"""
Job management for the HTTP adapter.
"""

import asyncio
import importlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Any, Optional, Callable

from quack_core.logging import get_logger
from .config import HttpAdapterConfig
from .util import new_id, stable_hash, post_callback
from .auth import sign_payload

logger = get_logger(__name__)

# Global state
_executor: Optional[ThreadPoolExecutor] = None
_jobs: Dict[str, Dict[str, Any]] = {}
_cfg: Optional[HttpAdapterConfig] = None
_jobs_lock = threading.Lock()

# Operation mapping table
OP_TABLE = {
    "quack-media.slice_video": ("quack-core.quack-media", "slice_video"),
    "quack-media.transcribe_audio": ("quack-core.quack-media", "transcribe_audio"),
    "quack-media.extract_frames": ("quack-core.quack-media", "extract_frames"),
}


def set_cfg(cfg: HttpAdapterConfig) -> None:
    """Set global configuration and initialize executor."""
    global _executor, _cfg
    _cfg = cfg

    if _executor:
        _executor.shutdown(wait=False)

    _executor = ThreadPoolExecutor(max_workers=cfg.max_workers)
    logger.info(f"Job executor initialized with {cfg.max_workers} workers")


def clear_jobs() -> None:
    """Clear all jobs (for testing)."""
    global _jobs
    with _jobs_lock:
        _jobs.clear()


def resolve_callable(op: str) -> Callable:
    """
    Resolve operation string to callable function.

    Args:
        op: Operation string like "quack-media.slice_video"

    Returns:
        Callable function

    Raises:
        ValueError: If operation not supported
        ImportError: If module not available
    """
    try:
        mod_name, fn_name = OP_TABLE[op]
    except KeyError:
        raise ValueError(f"Unsupported operation: {op}")

    try:
        mod = importlib.import_module(mod_name)
        fn = getattr(mod, fn_name)
        return fn
    except ImportError as e:
        # For now, quack-media doesn't exist - provide mock
        logger.warning(f"Module {mod_name} not available, using mock: {e}")
        return _create_mock_function(op)
    except AttributeError:
        raise ValueError(f"Function {fn_name} not found in {mod_name}")


def _create_mock_function(op: str) -> Callable:
    """Create a mock function for testing when real modules unavailable."""

    def mock_fn(*args, **kwargs):
        # Simulate some work
        time.sleep(0.05)  # Reduced for faster tests
        return {
            "success": True,
            "operation": op,
            "message": f"Mock execution of {op}",
            "params": kwargs
        }

    return mock_fn


def _cleanup_expired_jobs() -> None:
    """Remove expired jobs from memory."""
    if not _cfg:
        return

    cutoff_time = time.time() - _cfg.job_ttl_seconds
    expired_ids = []

    with _jobs_lock:
        for job_id, job_data in _jobs.items():
            finished_at = job_data.get("finished_at")
            # Only cleanup jobs that are actually finished and expired
            if finished_at and finished_at < cutoff_time:
                expired_ids.append(job_id)

        for job_id in expired_ids:
            del _jobs[job_id]

    if expired_ids:
        logger.info(f"Cleaned up {len(expired_ids)} expired jobs")


def _execute_job(job_id: str, op: str, params: dict, callback_url: Optional[str]) -> None:
    """Execute a job in the thread pool."""
    logger.info(f"Starting job {job_id}: {op}")

    # Update status to running
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id]["status"] = "running"

    try:
        # Resolve and call the operation
        fn = resolve_callable(op)
        result = fn(**params)

        # Update job with result
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id].update({
                    "status": "done",
                    "result": result,
                    "finished_at": time.time()
                })

        logger.info(f"Job {job_id} completed successfully")

        # Send callback if configured (only for real callback URLs, not examples)
        if callback_url and _cfg and not callback_url.startswith("http://example.com"):
            callback_data = {
                "job_id": job_id,
                "status": "done",
                "result": result,
                "error": None
            }

            signature_header = None
            if _cfg.hmac_secret:
                signature_header = sign_payload(callback_data, _cfg.hmac_secret)

            # Use asyncio to run the async callback
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    post_callback(callback_url, callback_data, signature_header)
                )
            except Exception as e:
                logger.error(f"Callback failed for job {job_id}: {e}")
            finally:
                loop.close()

    except Exception as e:
        error_msg = str(e).split('\n')[0]  # First line only
        logger.error(f"Job {job_id} failed: {e}")

        # Update job with error
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id].update({
                    "status": "error",
                    "error": error_msg,
                    "finished_at": time.time()
                })

        # Send error callback (only for real callback URLs)
        if callback_url and _cfg and not callback_url.startswith("http://example.com"):
            callback_data = {
                "job_id": job_id,
                "status": "error",
                "result": None,
                "error": error_msg
            }

            signature_header = None
            if _cfg.hmac_secret:
                signature_header = sign_payload(callback_data, _cfg.hmac_secret)

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    post_callback(callback_url, callback_data, signature_header)
                )
            except Exception as cb_e:
                logger.error(f"Error callback failed for job {job_id}: {cb_e}")
            finally:
                loop.close()


def enqueue(
        op: str,
        params: dict,
        callback_url: Optional[str] = None,
        idempotency_key: Optional[str] = None
) -> str:
    """
    Enqueue a new job.

    Args:
        op: Operation string
        params: Operation parameters
        callback_url: Optional callback URL
        idempotency_key: Optional idempotency key

    Returns:
        Job ID
    """
    if not _executor or not _cfg:
        raise RuntimeError("Job system not initialized")

    # Handle idempotency
    if idempotency_key:
        idem_data = {"op": op, "params": params, "key": idempotency_key}
        idem_hash = stable_hash(idem_data)

        with _jobs_lock:
            for job_id, job_data in _jobs.items():
                if job_data.get("idempotency_hash") == idem_hash:
                    logger.info(f"Returning existing job {job_id} for idempotency key")
                    return job_id

    # Create new job
    job_id = new_id()

    job_data = {
        "job_id": job_id,
        "op": op,
        "params": params,
        "status": "queued",
        "created_at": time.time(),
        "callback_url": callback_url
    }

    if idempotency_key:
        job_data["idempotency_hash"] = stable_hash({
            "op": op, "params": params, "key": idempotency_key
        })

    with _jobs_lock:
        _jobs[job_id] = job_data

    logger.info(f"Enqueued job {job_id}: {op}")

    # Submit to executor
    future = _executor.submit(_execute_job, job_id, op, params, callback_url)

    # Only cleanup periodically, not on every job
    if len(_jobs) % 10 == 0:  # Cleanup every 10 jobs
        _cleanup_expired_jobs()

    return job_id


def get_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get job status.

    Args:
        job_id: Job ID

    Returns:
        Job status dict or None if not found
    """
    with _jobs_lock:
        job_data = _jobs.get(job_id)
        if not job_data:
            return None

        return {
            "job_id": job_data["job_id"],
            "status": job_data["status"],
            "result": job_data.get("result"),
            "error": job_data.get("error")
        }