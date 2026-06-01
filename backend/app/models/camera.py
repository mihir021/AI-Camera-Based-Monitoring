"""
Camera model — camera registry, zone definitions, per-camera AI config.

Blueprint reference: COLLECTION 2 — cameras
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import Field

from app.models.base import MongoBaseModel, PyObjectId


# ── Enums ──────────────────────────────────────────────────────────────────────

class CameraStatus(str, Enum):
    active = "active"
    idle = "idle"
    offline = "offline"
    maintenance = "maintenance"


# ── Embedded objects ───────────────────────────────────────────────────────────

class CameraLocation(MongoBaseModel):
    building: str = "Default Building"
    floor: int = 1
    zone: str = "Zone A"
    description: Optional[str] = None


class CameraConfig(MongoBaseModel):
    """Per-camera AI inference settings."""
    model: str = "yolov8n"
    confidence_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    target_classes: List[int] = Field(default_factory=lambda: [0])  # 0 = person
    max_occupancy: Optional[int] = Field(default=None, ge=1)
    max_detections: int = Field(default=100, ge=1)


# ── Document models ────────────────────────────────────────────────────────────

class CameraCreate(MongoBaseModel):
    name: str
    org_id: Optional[str] = None
    location: CameraLocation = Field(default_factory=CameraLocation)
    config: CameraConfig = Field(default_factory=CameraConfig)
    tags: List[str] = Field(default_factory=list)
    created_by: Optional[str] = None


class CameraInDB(MongoBaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    org_id: Optional[str] = None
    location: CameraLocation = Field(default_factory=CameraLocation)
    status: CameraStatus = CameraStatus.idle
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    config: CameraConfig = Field(default_factory=CameraConfig)
    last_active_at: Optional[datetime] = None
    thumbnail_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class CameraResponse(CameraInDB):
    """Public representation — identical to InDB for cameras."""
    pass


class CameraUpdate(MongoBaseModel):
    name: Optional[str] = None
    location: Optional[CameraLocation] = None
    status: Optional[CameraStatus] = None
    config: Optional[CameraConfig] = None
    thumbnail_url: Optional[str] = None
    tags: Optional[List[str]] = None
