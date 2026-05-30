"""
Basic API tests for the AI Camera Platform backend.
These run in CI on every push to validate the app is healthy.
"""
from unittest.mock import MagicMock, patch
import pytest


# --- Mock heavy ML dependencies BEFORE importing main ---
# This prevents YOLOv8 from actually loading a model during CI,
# which would require downloading a 6MB file and GPU/CPU time.
mock_yolo = MagicMock()
mock_yolo.return_value = MagicMock()

with patch.dict("sys.modules", {"ultralytics": MagicMock(YOLO=mock_yolo)}):
    from fastapi.testclient import TestClient
    import sys, types

    # Patch ultralytics in the already-loaded module namespace
    import importlib
    import unittest.mock as mock

    with mock.patch("ultralytics.YOLO", mock_yolo):
        # Reload to pick up mock
        if "main" in sys.modules:
            del sys.modules["main"]
        import main as app_module

    client = TestClient(app_module.app)


# ─── Tests ───────────────────────────────────────────────

def test_analytics_endpoint_returns_200():
    """GET /analytics should return 200 with the correct JSON structure."""
    response = client.get("/analytics")
    assert response.status_code == 200


def test_analytics_response_has_required_fields():
    """Analytics response must contain all required keys."""
    response = client.get("/analytics")
    data = response.json()
    required_keys = ["person_count", "fps", "confidence_avg", "frame_number", "total_frames"]
    for key in required_keys:
        assert key in data, f"Missing key: {key}"


def test_analytics_default_values_are_numbers():
    """All analytics values should be numeric (int or float)."""
    response = client.get("/analytics")
    data = response.json()
    assert isinstance(data["person_count"], (int, float))
    assert isinstance(data["fps"], (int, float))
    assert isinstance(data["confidence_avg"], (int, float))


def test_upload_with_no_file_returns_error():
    """POST /upload with no file should return a 4xx error."""
    response = client.post("/upload")
    assert response.status_code in (400, 422)


def test_stream_nonexistent_video_returns_404():
    """GET /stream/<invalid-id> should return 404."""
    response = client.get("/stream/nonexistent-video-id-12345")
    assert response.status_code == 404
