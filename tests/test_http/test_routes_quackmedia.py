# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_http/test_routes_quackmedia.py
# role: tests
# neighbors: __init__.py, conftest.py, test_auth.py, test_config.py, test_integration.py, test_jobs.py (+2 more)
# exports: test_slice_video_no_auth, test_slice_video_success, test_transcribe_audio_success, test_extract_frames_success, test_invalid_operation_params, test_all_quackmedia_endpoints
# git_branch: refactor/toolkitWorkflow
# git_commit: 234aec0
# === QV-LLM:END ===

"""
Tests for QuackMedia routes.
"""

import pytest


def test_slice_video_no_auth(test_client):
    """Test slice endpoint fails without auth."""
    response = test_client.post("/quack-media/slice", json={
        "input_path": "/test.mp4",
        "output_path": "/out.mp4",
        "start": "00:00:05",
        "end": "00:00:15"
    })
    assert response.status_code == 401


def test_slice_video_success(test_client, auth_headers):
    """Test successful video slicing."""
    response = test_client.post("/quack-media/slice", json={
        "input_path": "/test.mp4",
        "output_path": "/out.mp4",
        "start": "00:00:05",
        "end": "00:00:15",
        "overwrite": True
    }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["operation"] == "quack-media.slice_video"


def test_transcribe_audio_success(test_client, auth_headers):
    """Test successful audio transcription."""
    response = test_client.post("/quack-media/transcribe", json={
        "input_path": "/test.mp3",
        "model_name": "small",
        "device": "auto",
        "vad": True
    }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["operation"] == "quack-media.transcribe_audio"


def test_extract_frames_success(test_client, auth_headers):
    """Test successful frame extraction."""
    response = test_client.post("/quack-media/frames", json={
        "input_path": "/test.mp4",
        "output_dir": "/frames",
        "fps": 2.0,
        "pattern": "frame_%06d.png",
        "overwrite": True
    }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["operation"] == "quack-media.extract_frames"


def test_invalid_operation_params(test_client, auth_headers):
    """Test handling of invalid parameters."""
    response = test_client.post("/quack-media/slice", json={
        "invalid_param": "value"
    }, headers=auth_headers)

    # Should handle gracefully (mock function accepts any kwargs)
    assert response.status_code == 200


@pytest.mark.parametrize("endpoint,operation", [
    ("/quack-media/slice", "quack-media.slice_video"),
    ("/quack-media/transcribe", "quack-media.transcribe_audio"),
    ("/quack-media/frames", "quack-media.extract_frames"),
])
def test_all_quackmedia_endpoints(test_client, auth_headers, endpoint, operation):
    """Test all QuackMedia endpoints return consistent structure."""
    response = test_client.post(endpoint, json={
        "test_param": "test_value"
    }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["operation"] == operation
    assert "params" in data
    assert data["params"]["test_param"] == "test_value"