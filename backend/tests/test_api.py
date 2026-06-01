"""
Basic API tests for the AI Camera Platform backend.
These run in CI on every push to validate the app is healthy.

Mock strategy:
  - cv2 / ultralytics   → heavy ML/CV libraries mocked to avoid installation
  - motor / pymongo      → MongoDB driver mocked so tests run without Atlas
  - connect_to_mongodb  → patched to no-op so FastAPI lifespan doesn't block
"""
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import pytest


# ── 1. Mock ALL heavy/unavailable modules BEFORE any import ──────────────────

# cv2 (OpenCV) — not installed in base CI
cv2_mock = MagicMock()
cv2_mock.VideoCapture.return_value = MagicMock()
cv2_mock.CAP_PROP_FRAME_COUNT = 7
cv2_mock.CAP_PROP_FPS = 5
sys.modules.setdefault("cv2", cv2_mock)

# ultralytics — large ML dep, ~200MB
mock_yolo = MagicMock()
mock_yolo.return_value = MagicMock()
ultralytics_mock = MagicMock()
ultralytics_mock.YOLO = mock_yolo
sys.modules.setdefault("ultralytics", ultralytics_mock)

# motor — async MongoDB driver
motor_mock = MagicMock()
motor_asyncio_mock = MagicMock()
motor_mock.motor_asyncio = motor_asyncio_mock
sys.modules.setdefault("motor", motor_mock)
sys.modules.setdefault("motor.motor_asyncio", motor_asyncio_mock)

# Build a Motor-compatible async collection mock
# Motor calls: collection.find().sort().limit().to_list(length=N)
_cursor_mock = MagicMock()
_cursor_mock.sort.return_value = _cursor_mock
_cursor_mock.limit.return_value = _cursor_mock
_cursor_mock.skip.return_value = _cursor_mock
_cursor_mock.to_list = AsyncMock(return_value=[])
_cursor_mock.aggregate = MagicMock(return_value=_cursor_mock)

_col_mock = MagicMock()
_col_mock.find.return_value = _cursor_mock
_col_mock.find_one = AsyncMock(return_value=None)
_col_mock.insert_one = AsyncMock(return_value=MagicMock(inserted_id="mock_id"))
_col_mock.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
_col_mock.find_one_and_update = AsyncMock(return_value=None)
_col_mock.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
_col_mock.create_index = AsyncMock()
_col_mock.list_collection_names = AsyncMock(return_value=["users"])
_col_mock.aggregate.return_value = _cursor_mock

_db_mock = MagicMock()
_db_mock.__getitem__.return_value = _col_mock
_db_mock.list_collection_names = AsyncMock(return_value=["users"])

# pymongo — sync MongoDB driver (used for ASCENDING/DESCENDING constants)
pymongo_mock = MagicMock()
pymongo_mock.ASCENDING = 1
pymongo_mock.DESCENDING = -1
pymongo_mock.ReturnDocument = MagicMock()
pymongo_errors_mock = MagicMock()
sys.modules.setdefault("pymongo", pymongo_mock)
sys.modules.setdefault("pymongo.errors", pymongo_errors_mock)

# bson — ObjectId serialisation
bson_mock = MagicMock()
bson_mock.ObjectId = MagicMock(side_effect=lambda x: x)
sys.modules.setdefault("bson", bson_mock)

# dotenv
dotenv_mock = MagicMock()
dotenv_mock.load_dotenv = MagicMock()
sys.modules.setdefault("dotenv", dotenv_mock)


# ── 2. Import FastAPI test client and app with patches ────────────────────────

from fastapi.testclient import TestClient  # noqa: E402

# Patch connect/disconnect so the lifespan becomes a no-op in tests
with (
    patch("app.db.mongodb.connect_to_mongodb", new_callable=AsyncMock),
    patch("app.db.mongodb.disconnect_from_mongodb", new_callable=AsyncMock),
    patch("app.db.mongodb.get_db", return_value=_db_mock),
):
    # Clear any cached modules so the mocks take effect
    for mod in list(sys.modules.keys()):
        if mod.startswith("app."):
            del sys.modules[mod]

    import app.main as app_module  # noqa: E402

# Patch get_db at the service level so runtime calls also resolve to the mock
for svc_module in [
    "app.services.camera_service",
    "app.services.upload_service",
    "app.services.session_service",
    "app.services.analytics_service",
    "app.services.alert_service",
    "app.services.incident_service",
]:
    mod = sys.modules.get(svc_module)
    if mod and hasattr(mod, "get_db"):
        mod.get_db = lambda: _db_mock  # type: ignore[assignment]

client = TestClient(app_module.app, raise_server_exceptions=False)


# ── Tests ─────────────────────────────────────────────────────────────────────

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


def test_health_endpoint_returns_200():
    """GET /health should return 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_sessions_endpoint_is_reachable():
    """GET /sessions should not return 404 — DB layer is mocked."""
    response = client.get("/sessions")
    assert response.status_code != 404


def test_cameras_endpoint_is_reachable():
    """GET /cameras should not return 404."""
    response = client.get("/cameras")
    assert response.status_code != 404


def test_alerts_endpoint_is_reachable():
    """GET /alerts should not return 404."""
    response = client.get("/alerts")
    assert response.status_code != 404


def test_incidents_endpoint_is_reachable():
    """GET /incidents should not return 404."""
    response = client.get("/incidents")
    assert response.status_code != 404
