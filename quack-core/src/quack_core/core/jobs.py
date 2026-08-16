# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/jobs.py
# === QV-LLM:END ===


"""
Job execution interfaces and implementations for QuackCore.

This module provides abstractions for job storage and execution, allowing
different implementations (in-memory, Redis, PostgreSQL, etc.) without
changing adapter code.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Any

from quack_core.core.logging import get_logger
from quack_core.core.registry import OperationRegistry

logger = get_logger(__name__)


class JobStatus(str, Enum):
    """Job execution status."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class JobData:
    """
    Job data structure.

    Attributes:
        job_id: Unique job identifier
        op: Operation name
        params: Operation parameters
        status: Current status
        result: Operation result (when done)
        error: Error message (when error)
        created_at: Creation timestamp
        finished_at: Completion timestamp
        callback_url: Optional callback URL
        idempotency_hash: Optional hash for idempotency
    """

    job_id: str
    op: str
    params: dict[str, Any]
    status: JobStatus
    created_at: float
    result: dict[str, Any] | None = None
    error: str | None = None
    finished_at: float | None = None
    callback_url: str | None = None
    idempotency_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "op": self.op,
            "params": self.params,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "callback_url": self.callback_url,
        }


class JobStore(ABC):
    """
    Abstract interface for job storage.

    Implementations can use different backends (memory, Redis, PostgreSQL, etc.)
    while maintaining the same interface for adapters.
    """

    @abstractmethod
    def create(self, job_data: JobData) -> None:
        """
        Store a new job.

        Args:
            job_data: Job data to store
        """
        pass

    @abstractmethod
    def get(self, job_id: str) -> JobData | None:
        """
        Retrieve a job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job data if found, None otherwise
        """
        pass

    @abstractmethod
    def update(self, job_data: JobData) -> None:
        """
        Update existing job.

        Args:
            job_data: Updated job data
        """
        pass

    @abstractmethod
    def find_by_idempotency_hash(self, hash_value: str) -> JobData | None:
        """
        Find a job by idempotency hash.

        Args:
            hash_value: Idempotency hash

        Returns:
            Job data if found, None otherwise
        """
        pass

    @abstractmethod
    def cleanup_expired(self, ttl_seconds: int) -> int:
        """
        Remove expired jobs.

        Args:
            ttl_seconds: Time to live in seconds

        Returns:
            Number of jobs removed
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all jobs (for testing)."""
        pass


class JobRunner(ABC):
    """
    Abstract interface for job execution.

    Implementations can use different execution models (threads, processes,
    async, external queue, etc.) while maintaining the same interface.
    """

    @abstractmethod
    def submit(
        self,
        job_id: str,
        op_name: str,
        params: dict[str, Any],
        callback_url: str | None,
    ) -> None:
        """
        Submit a job for execution.

        Args:
            job_id: Job identifier
            op_name: Operation name
            params: Operation parameters
            callback_url: Optional callback URL
        """
        pass

    @abstractmethod
    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the runner.

        Args:
            wait: Whether to wait for pending jobs
        """
        pass


class InMemoryJobStore(JobStore):
    """
    In-memory job store implementation.

    This is suitable for development and single-instance deployments.
    For production with multiple instances, use a Redis or database-backed store.
    """

    def __init__(self) -> None:
        """Initialize empty store."""
        self._jobs: dict[str, JobData] = {}
        self._lock = Lock()
        logger.debug("InMemoryJobStore initialized")

    def create(self, job_data: JobData) -> None:
        """Store a new job."""
        with self._lock:
            self._jobs[job_data.job_id] = job_data

    def get(self, job_id: str) -> JobData | None:
        """Retrieve a job by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_data: JobData) -> None:
        """
        Update existing job.

        Args:
            job_data: Updated job data

        Raises:
            KeyError: If job not found
        """
        with self._lock:
            if job_data.job_id not in self._jobs:
                raise KeyError(f"Job not found: {job_data.job_id}")
            self._jobs[job_data.job_id] = job_data

    def find_by_idempotency_hash(self, hash_value: str) -> JobData | None:
        """Find a job by idempotency hash."""
        with self._lock:
            for job_data in self._jobs.values():
                if job_data.idempotency_hash == hash_value:
                    return job_data
            return None

    def cleanup_expired(self, ttl_seconds: int) -> int:
        """Remove expired jobs."""
        cutoff_time = time.time() - ttl_seconds
        expired_ids: list[str] = []

        with self._lock:
            for job_id, job_data in self._jobs.items():
                if (
                    job_data.finished_at is not None
                    and job_data.finished_at < cutoff_time
                ):
                    expired_ids.append(job_id)

            for job_id in expired_ids:
                del self._jobs[job_id]

        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired jobs")

        return len(expired_ids)

    def clear(self) -> None:
        """Clear all jobs."""
        with self._lock:
            self._jobs.clear()


class ThreadPoolJobRunner(JobRunner):
    """
    Thread pool-based job runner.

    Executes jobs in a thread pool. Suitable for I/O-bound operations.
    For CPU-bound work, consider a process pool or distributed queue.
    """

    def __init__(
        self,
        registry: OperationRegistry,
        store: JobStore,
        max_workers: int = 4,
        hmac_secret: str | None = None,
    ) -> None:
        """
        Initialize thread pool runner.

        Args:
            registry: Operation registry
            store: Job store
            max_workers: Maximum number of worker threads
            hmac_secret: Optional HMAC secret for callback signing
        """
        self._registry = registry
        self._store = store
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._hmac_secret = hmac_secret
        logger.info(f"ThreadPoolJobRunner initialized with {max_workers} workers")

    def submit(
        self,
        job_id: str,
        op_name: str,
        params: dict[str, Any],
        callback_url: str | None,
    ) -> None:
        """Submit a job for execution."""
        self._executor.submit(
            self._execute_job,
            job_id,
            op_name,
            params,
            callback_url,
        )

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the thread pool."""
        self._executor.shutdown(wait=wait)
        logger.info("ThreadPoolJobRunner shutdown")

    def _execute_job(
        self,
        job_id: str,
        op_name: str,
        params: dict[str, Any],
        callback_url: str | None,
    ) -> None:
        """Execute a job in the thread pool."""
        logger.info(f"Starting job {job_id}: {op_name}")

        # Update status to running
        job_data = self._store.get(job_id)
        if job_data is None:
            logger.error(f"Job {job_id} not found in store")
            return

        job_data.status = JobStatus.RUNNING
        self._store.update(job_data)

        try:
            # Resolve operation
            op = self._registry.get_or_error(op_name)

            # Execute operation using shared invoker
            # Note: asyncio.run() is safe here because ThreadPoolExecutor threads
            # don't have a running event loop. If execution model changes, this
            # will raise a clear error.
            from quack_core.core.registry import invoke_operation

            try:
                result = asyncio.run(invoke_operation(op, params))
            except RuntimeError as e:
                if "cannot be called from a running event loop" in str(e):
                    raise RuntimeError(
                        "Async operation execution failed: asyncio.run() "
                        "called from a running loop. "
                        "ThreadPoolJobRunner expects to run in a worker thread "
                        "without an active event loop."
                    ) from e
                raise

            # Update job with result
            job_data.status = JobStatus.DONE
            job_data.result = result
            job_data.finished_at = time.time()
            self._store.update(job_data)

            logger.info(f"Job {job_id} completed successfully")

            # Send callback if configured
            if callback_url:
                self._send_callback(job_id, job_data, callback_url)

        except Exception as e:
            error_msg = str(e).split("\n")[0]
            logger.error(f"Job {job_id} failed: {e}")

            # Update job with error
            job_data.status = JobStatus.ERROR
            job_data.error = error_msg
            job_data.finished_at = time.time()
            self._store.update(job_data)

            # Send error callback
            if callback_url:
                self._send_callback(job_id, job_data, callback_url)

    def _send_callback(
        self,
        job_id: str,
        job_data: JobData,
        callback_url: str,
    ) -> None:
        """Send callback for job completion."""
        from quack_core.adapters.http.auth import sign_payload
        from quack_core.adapters.http.util import post_callback

        callback_data = {
            "job_id": job_id,
            "status": job_data.status.value,
            "result": job_data.result,
            "error": job_data.error,
        }

        signature_header = None
        if self._hmac_secret:
            signature_header = sign_payload(callback_data, self._hmac_secret)

        try:
            asyncio.run(post_callback(callback_url, callback_data, signature_header))
            logger.info(f"Callback sent successfully for job {job_id}")
        except Exception as e:
            logger.error(f"Callback failed for job {job_id} to {callback_url}: {e}")
