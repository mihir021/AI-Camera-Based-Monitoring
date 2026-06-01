"""
Session model — video analysis lifecycle, summary aggregation.

Blueprint reference: COLLECTION 3 — sessions
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import Field

from app.models.base import MongoBaseModel, PyObjectId


class SessionStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ModelConfigSnapshot(MongoBaseModel):
    """Immutable snapshot of the AI config used during this session."""
    model: str = "yolov8n"
    confidence_threshold: float = 0.55
    iou_threshold: float = 0.45
    target_classes: List[int] = Field(default_factory=lambda: [0])


class SessionSummary(MongoBaseModel):
    """Computed and written once when the session completes."""
    peak_person_count: int = 0
    avg_person_count: float = 0.0
    avg_confidence: float = 0.0
    avg_fps: float = 0.0
    alert_count: int = 0
    total_snapshots: int = 0


class SessionCreate(MongoBaseModel):
    camera_id: str
    upload_id: str
    org_id: Optional[str] = None
    created_by: Optional[str] = None
    total_frames: int = 0
    model_config_snapshot: ModelConfigSnapshot = Field(
        default_factory=ModelConfigSnapshot
    )
    tags: List[str] = Field(default_factory=list)


class SessionInDB(MongoBaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    org_id: Optional[str] = None
    camera_id: str
    upload_id: str
    created_by: Optional[str] = None
    status: SessionStatus = SessionStatus.queued
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_frames: int = 0
    processed_frames: int = 0
    duration_seconds: Optional[float] = None
    summary: Optional[SessionSummary] = None
    model_config_snapshot: ModelConfigSnapshot = Field(
        default_factory=ModelConfigSnapshot
    )
    error_message: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class SessionResponse(SessionInDB):
    pass


class SessionUpdate(MongoBaseModel):
    status: Optional[SessionStatus] = None
    processed_frames: Optional[int] = None
    total_frames: Optional[int] = None
    duration_seconds: Optional[float] = None
    completed_at: Optional[datetime] = None
    summary: Optional[SessionSummary] = None
    error_message: Optional[str] = None
