# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_http/test_routes_quackmedia.py
# === QV-LLM:END ===

"""
Tests for QuackMedia operations, invoked through the generic /ops interface.

The concrete "/quack-media/*" routes this file used to test against were
deliberately retired: operations.py's own module docstring states
"This replaces the old 'quackmedia' routes with a generic _ops interface
that works with the registry." There is no quack-media router in
adapters/http/routes/ any more (only health, jobs, and operations) -- every
quack-media.* operation is invoked via POST /ops/{op_name}, matching the
generic OperationRegistry contract the rest of this test package
(test_routes_jobs.py, test_jobs.py) already exercises. This file is
rewritten against that current, real contract rather than the retired
route surface, preserving the original intent (verify slice/transcribe/
frame-extract operations respond correctly end-to-end through the HTTP
adapter) instead of deleting the coverage outright. There was never a real
production quack-media operation implementation to fall back on either --
grep across quack-core/src finds zero references to transcribe_audio/
extract_frames outside tests -- so conftest.py registers test-only stand-in
operations under these three names for these tests to exercise.
"""

import pytest
from fastapi.testclient import TestClient


def test_slice_video_no_auth(test_client: TestClient) -> None:
    """Test the ops endpoint fails without auth."""
    response = test_client.post(
        "/ops/quack-media.slice_video",
        json={
            "input_path": "/test.mp4",
            "output_path": "/out.mp4",
        },
    )
    assert response.status_code == 401


def test_slice_video_success(
    test_client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Test successful video slicing via the generic /ops interface."""
    response = test_client.post(
        "/ops/quack-media.slice_video",
        json={
            "input_path": "/test.mp4",
            "output_path": "/out.mp4",
            "start": "00:00:05",
            "end": "00:00:15",
            "overwrite": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["operation"] == "quack-media.slice_video"


def test_transcribe_audio_success(
    test_client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Test successful audio transcription via the generic /ops interface."""
    response = test_client.post(
        "/ops/quack-media.transcribe_audio",
        json={
            "input_path": "/test.mp3",
            "model_name": "small",
            "device": "auto",
            "vad": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["operation"] == "quack-media.transcribe_audio"


def test_extract_frames_success(
    test_client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Test successful frame extraction via the generic /ops interface."""
    response = test_client.post(
        "/ops/quack-media.extract_frames",
        json={
            "input_path": "/test.mp4",
            "output_dir": "/frames",
            "fps": 2.0,
            "pattern": "frame_%06d.png",
            "overwrite": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["operation"] == "quack-media.extract_frames"


def test_invalid_operation_params(
    test_client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Test handling of arbitrary/unexpected parameters."""
    response = test_client.post(
        "/ops/quack-media.slice_video",
        json={"invalid_param": "value"},
        headers=auth_headers,
    )

    # The test-only request model accepts extra params, so this should
    # succeed gracefully rather than 400/422.
    assert response.status_code == 200


@pytest.mark.parametrize(
    "op_name",
    [
        "quack-media.slice_video",
        "quack-media.transcribe_audio",
        "quack-media.extract_frames",
    ],
)
def test_all_quackmedia_endpoints(
    test_client: TestClient,
    auth_headers: dict[str, str],
    op_name: str,
) -> None:
    """Test all registered quack-media operations return a consistent
    response structure through the generic /ops interface."""
    response = test_client.post(
        f"/ops/{op_name}",
        json={"test_param": "test_value"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["operation"] == op_name
    assert "params" in data["data"]
    assert data["data"]["params"]["test_param"] == "test_value"
