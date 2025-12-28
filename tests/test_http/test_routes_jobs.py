# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_http/test_routes_jobs.py
# role: tests
# neighbors: __init__.py, conftest.py, test_auth.py, test_config.py, test_integration.py, test_jobs.py (+2 more)
# exports: test_post_jobs_no_auth, test_post_jobs_success, test_post_jobs_with_callback, test_post_jobs_with_idempotency_header, test_get_job_status_not_found, test_get_job_status_success, test_job_lifecycle
# git_branch: refactor/newHeaders
# git_commit: 98b2a5c
# === QV-LLM:END ===

"""
Tests for job routes.
"""

import pytest
import time


def test_post_jobs_no_auth(test_client):
    """Test job creation fails without auth."""
    response = test_client.post("/jobs", json={
        "op": "quack-media.slice_video",
        "params": {"input_path": "/test"}
    })
    assert response.status_code == 401


def test_post_jobs_success(test_client, auth_headers):
    """Test successful job creation."""
    response = test_client.post("/jobs", json={
        "op": "quack-media.slice_video",
        "params": {"input_path": "/test", "output_path": "/out"}
    }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"


def test_post_jobs_with_callback(test_client, auth_headers):
    """Test job creation with callback URL."""
    response = test_client.post("/jobs", json={
        "op": "quack-media.slice_video",
        "params": {"input_path": "/test"},
        "callback_url": "http://example.com/callback"
    }, headers=auth_headers)

    assert response.status_code == 200


def test_post_jobs_with_idempotency_header(test_client, auth_headers):
    """Test job creation with idempotency header."""
    headers = {**auth_headers, "Idempotency-Key": "test-123"}

    response1 = test_client.post("/jobs", json={
        "op": "quack-media.slice_video",
        "params": {"input_path": "/test"}
    }, headers=headers)

    # Make second request immediately
    response2 = test_client.post("/jobs", json={
        "op": "quack-media.slice_video",
        "params": {"input_path": "/test"}
    }, headers=headers)

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json()["job_id"] == response2.json()["job_id"]


def test_get_job_status_not_found(test_client, auth_headers):
    """Test getting status for non-existent job."""
    response = test_client.get("/jobs/non-existent", headers=auth_headers)
    assert response.status_code == 404


def test_get_job_status_success(test_client, auth_headers):
    """Test getting job status."""
    # Create a job first
    create_response = test_client.post("/jobs", json={
        "op": "quack-media.slice_video",
        "params": {"input_path": "/test"}
    }, headers=auth_headers)

    job_id = create_response.json()["job_id"]

    # Get status immediately (should exist)
    status_response = test_client.get(f"/jobs/{job_id}", headers=auth_headers)
    assert status_response.status_code == 200

    data = status_response.json()
    assert data["job_id"] == job_id
    assert data["status"] in ["queued", "running", "done"]


def test_job_lifecycle(test_client, auth_headers):
    """Test complete job lifecycle."""
    # Create job
    create_response = test_client.post("/jobs", json={
        "op": "quack-media.slice_video",
        "params": {"input_path": "/test", "output_path": "/out"}
    }, headers=auth_headers)

    assert create_response.status_code == 200
    job_id = create_response.json()["job_id"]

    # Poll until completion (with timeout)
    max_wait = 5  # seconds
    start_time = time.time()

    while time.time() - start_time < max_wait:
        status_response = test_client.get(f"/jobs/{job_id}", headers=auth_headers)
        assert status_response.status_code == 200  # Should always find the job
        data = status_response.json()

        if data["status"] in ["done", "error"]:
            break

        time.sleep(0.1)

    # Check final status
    assert data["status"] == "done"
    assert data["result"] is not None
    assert data["result"]["success"] is True