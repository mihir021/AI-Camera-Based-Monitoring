"""
models package — exports all Pydantic document models.
"""

from app.models.base import MongoBaseModel, PyObjectId
from app.models.user import UserCreate, UserInDB, UserResponse, UserUpdate, UserRole
from app.models.camera import (
    CameraCreate, CameraInDB, CameraResponse, CameraUpdate,
    CameraStatus, CameraLocation, CameraConfig,
)
from app.models.video_upload import (
    VideoUploadCreate, VideoUploadInDB, VideoUploadResponse, VideoUploadUpdate,
    VideoUploadStatus,
)
from app.models.session import (
    SessionCreate, SessionInDB, SessionResponse, SessionUpdate,
    SessionStatus, SessionSummary, ModelConfigSnapshot,
)
from app.models.analytics_snapshot import (
    AnalyticsSnapshotCreate, AnalyticsSnapshotResponse,
    SnapshotMeta, DetectionBox,
)
from app.models.alert import (
    AlertCreate, AlertInDB, AlertResponse, AlertUpdate,
    AlertType, AlertSeverity,
)
from app.models.model_config import (
    ModelConfigCreate, ModelConfigInDB, ModelConfigResponse, ModelConfigUpdate,
    DEFAULT_MODEL_CONFIG,
)
from app.models.incident import (
    IncidentCreate, IncidentInDB, IncidentResponse, IncidentUpdate,
    IncidentCategory, IncidentSeverity, IncidentStatus,
)

__all__ = [
    # Base
    "MongoBaseModel", "PyObjectId",
    # User
    "UserCreate", "UserInDB", "UserResponse", "UserUpdate", "UserRole",
    # Camera
    "CameraCreate", "CameraInDB", "CameraResponse", "CameraUpdate",
    "CameraStatus", "CameraLocation", "CameraConfig",
    # VideoUpload
    "VideoUploadCreate", "VideoUploadInDB", "VideoUploadResponse",
    "VideoUploadUpdate", "VideoUploadStatus",
    # Session
    "SessionCreate", "SessionInDB", "SessionResponse", "SessionUpdate",
    "SessionStatus", "SessionSummary", "ModelConfigSnapshot",
    # AnalyticsSnapshot
    "AnalyticsSnapshotCreate", "AnalyticsSnapshotResponse",
    "SnapshotMeta", "DetectionBox",
    # Alert
    "AlertCreate", "AlertInDB", "AlertResponse", "AlertUpdate",
    "AlertType", "AlertSeverity",
    # ModelConfig
    "ModelConfigCreate", "ModelConfigInDB", "ModelConfigResponse",
    "ModelConfigUpdate", "DEFAULT_MODEL_CONFIG",
    # Incident
    "IncidentCreate", "IncidentInDB", "IncidentResponse", "IncidentUpdate",
    "IncidentCategory", "IncidentSeverity", "IncidentStatus",
]
