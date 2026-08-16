# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_http/test_jobs.py
# === QV-LLM:END ===

"""
Tests for job management functionality using core.jobs abstractions.
"""

import time
import uuid

import pytest
from quack_core.core.jobs import (
    InMemoryJobStore,
    JobData,
    JobStatus,
    ThreadPoolJobRunner,
)
from quack_core.core.registry import Operation, OperationRegistry


def test_job_store_create_and_get(job_store: InMemoryJobStore) -> None:
    """Test creating and retrieving jobs."""
    job_data = JobData(
        job_id=str(uuid.uuid4()),
        op="test.operation",
        params={"key": "value"},
        status=JobStatus.QUEUED,
        created_at=time.time(),
    )

    job_store.create(job_data)

    retrieved = job_store.get(job_data.job_id)
    assert retrieved is not None
    assert retrieved.job_id == job_data.job_id
    assert retrieved.op == "test.operation"
    assert retrieved.params == {"key": "value"}
    assert retrieved.status == JobStatus.QUEUED


def test_job_store_update(job_store: InMemoryJobStore) -> None:
    """Test updating job data."""
    job_data = JobData(
        job_id=str(uuid.uuid4()),
        op="test.operation",
        params={},
        status=JobStatus.QUEUED,
        created_at=time.time(),
    )

    job_store.create(job_data)

    # Update status
    job_data.status = JobStatus.RUNNING
    job_store.update(job_data)

    retrieved = job_store.get(job_data.job_id)
    assert retrieved is not None
    assert retrieved.status == JobStatus.RUNNING


def test_job_store_update_nonexistent(job_store: InMemoryJobStore) -> None:
    """Test updating non-existent job raises error."""
    job_data = JobData(
        job_id=str(uuid.uuid4()),
        op="test.operation",
        params={},
        status=JobStatus.QUEUED,
        created_at=time.time(),
    )

    with pytest.raises(KeyError):
        job_store.update(job_data)


def test_job_store_idempotency(job_store: InMemoryJobStore) -> None:
    """Test finding jobs by idempotency hash."""
    hash_value = "test-hash-123"

    job_data = JobData(
        job_id=str(uuid.uuid4()),
        op="test.operation",
        params={},
        status=JobStatus.QUEUED,
        created_at=time.time(),
        idempotency_hash=hash_value,
    )

    job_store.create(job_data)

    # Find by hash
    found = job_store.find_by_idempotency_hash(hash_value)
    assert found is not None
    assert found.job_id == job_data.job_id
    assert found.idempotency_hash == hash_value

    # Non-existent hash
    not_found = job_store.find_by_idempotency_hash("non-existent")
    assert not_found is None


def test_job_store_cleanup_expired(job_store: InMemoryJobStore) -> None:
    """Test cleanup of expired jobs."""
    current_time = time.time()

    # Create finished job (old)
    old_job = JobData(
        job_id=str(uuid.uuid4()),
        op="test.operation",
        params={},
        status=JobStatus.DONE,
        created_at=current_time - 200,
        finished_at=current_time - 150,
    )
    job_store.create(old_job)

    # Create finished job (recent)
    recent_job = JobData(
        job_id=str(uuid.uuid4()),
        op="test.operation",
        params={},
        status=JobStatus.DONE,
        created_at=current_time - 30,
        finished_at=current_time - 20,
    )
    job_store.create(recent_job)

    # Create running job (not finished)
    running_job = JobData(
        job_id=str(uuid.uuid4()),
        op="test.operation",
        params={},
        status=JobStatus.RUNNING,
        created_at=current_time - 200,
    )
    job_store.create(running_job)

    # Cleanup jobs older than 100 seconds
    removed = job_store.cleanup_expired(ttl_seconds=100)

    assert removed == 1  # Only old_job should be removed
    assert job_store.get(old_job.job_id) is None
    assert job_store.get(recent_job.job_id) is not None
    assert job_store.get(running_job.job_id) is not None


def test_job_runner_execution(job_store: InMemoryJobStore) -> None:
    """Test job runner executes jobs successfully."""
    registry = OperationRegistry()

    # Register a test operation
    def test_operation(x: int, y: int) -> dict:
        return {"result": x + y}

    registry.register(
        Operation(
            name="test.add",
            fn=test_operation,
            is_async=False,
        )
    )

    runner = ThreadPoolJobRunner(
        registry=registry,
        store=job_store,
        max_workers=2,
    )

    try:
        # Create and submit job
        job_id = str(uuid.uuid4())
        job_data = JobData(
            job_id=job_id,
            op="test.add",
            params={"x": 5, "y": 3},
            status=JobStatus.QUEUED,
            created_at=time.time(),
        )
        job_store.create(job_data)

        runner.submit(
            job_id=job_id,
            op_name="test.add",
            params={"x": 5, "y": 3},
            callback_url=None,
        )

        # Wait for completion
        for _ in range(50):  # 5 seconds max
            job = job_store.get(job_id)
            if job and job.status == JobStatus.DONE:
                break
            time.sleep(0.1)

        # Verify result
        final_job = job_store.get(job_id)
        assert final_job is not None
        assert final_job.status == JobStatus.DONE
        assert final_job.result == {"result": 8}
        assert final_job.error is None
        assert final_job.finished_at is not None

    finally:
        runner.shutdown(wait=True)


def test_job_runner_error_handling(job_store: InMemoryJobStore) -> None:
    """Test job runner handles errors properly."""
    registry = OperationRegistry()

    # Register an operation that fails
    def failing_operation() -> dict:
        raise ValueError("Test error message")

    registry.register(
        Operation(
            name="test.fail",
            fn=failing_operation,
            is_async=False,
        )
    )

    runner = ThreadPoolJobRunner(
        registry=registry,
        store=job_store,
        max_workers=2,
    )

    try:
        # Create and submit job
        job_id = str(uuid.uuid4())
        job_data = JobData(
            job_id=job_id,
            op="test.fail",
            params={},
            status=JobStatus.QUEUED,
            created_at=time.time(),
        )
        job_store.create(job_data)

        runner.submit(
            job_id=job_id,
            op_name="test.fail",
            params={},
            callback_url=None,
        )

        # Wait for completion
        for _ in range(50):
            job = job_store.get(job_id)
            if job and job.status == JobStatus.ERROR:
                break
            time.sleep(0.1)

        # Verify error
        final_job = job_store.get(job_id)
        assert final_job is not None
        assert final_job.status == JobStatus.ERROR
        assert final_job.error is not None
        assert "Test error message" in final_job.error
        assert final_job.result is None
        assert final_job.finished_at is not None

    finally:
        runner.shutdown(wait=True)


def test_job_runner_async_operation(job_store: InMemoryJobStore) -> None:
    """Test job runner executes async operations."""
    registry = OperationRegistry()

    # Register an async operation
    async def async_operation(value: str) -> dict:
        return {"echo": value}

    registry.register(
        Operation(
            name="test.async",
            fn=async_operation,
            is_async=True,
        )
    )

    runner = ThreadPoolJobRunner(
        registry=registry,
        store=job_store,
        max_workers=2,
    )

    try:
        # Create and submit job
        job_id = str(uuid.uuid4())
        job_data = JobData(
            job_id=job_id,
            op="test.async",
            params={"value": "hello"},
            status=JobStatus.QUEUED,
            created_at=time.time(),
        )
        job_store.create(job_data)

        runner.submit(
            job_id=job_id,
            op_name="test.async",
            params={"value": "hello"},
            callback_url=None,
        )

        # Wait for completion
        for _ in range(50):
            job = job_store.get(job_id)
            if job and job.status == JobStatus.DONE:
                break
            time.sleep(0.1)

        # Verify result
        final_job = job_store.get(job_id)
        assert final_job is not None
        assert final_job.status == JobStatus.DONE
        assert final_job.result == {"echo": "hello"}

    finally:
        runner.shutdown(wait=True)


def test_job_data_to_dict() -> None:
    """Test JobData serialization to dict."""
    job_data = JobData(
        job_id="test-123",
        op="test.operation",
        params={"key": "value"},
        status=JobStatus.DONE,
        created_at=1234567890.0,
        result={"output": "data"},
        error=None,
        finished_at=1234567900.0,
        callback_url="https://example.com/callback",
    )

    result = job_data.to_dict()

    assert result["job_id"] == "test-123"
    assert result["op"] == "test.operation"
    assert result["params"] == {"key": "value"}
    assert result["status"] == "done"
    assert result["result"] == {"output": "data"}
    assert result["error"] is None
    assert result["created_at"] == 1234567890.0
    assert result["finished_at"] == 1234567900.0
    assert result["callback_url"] == "https://example.com/callback"
