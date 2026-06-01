"""
AnalyticsSnapshot model — time-series per-frame metrics.

This maps to a MongoDB native time-series collection.

Blueprint reference: COLLECTION 4 — analytics_snapshots (Time-Series)

Time-series fields:
  timeField  = "timestamp"
  metaField  = "meta"
  granularity = "seconds"
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from app.models.base import MongoBaseModel


class SnapshotMeta(MongoBaseModel):
    """
    metaField for the time-series collection.
    MongoDB groups buckets by the metaField value.
    """
    session_id: str
    camera_id: str
    org_id: Optional[str] = None


class DetectionBox(MongoBaseModel):
    """Individual bounding-box detection — stored on sampled frames only."""
    bbox: List[float] = Field(min_length=4, max_length=4)   # [x1, y1, x2, y2]
    confidence: float = Field(ge=0.0, le=1.0)
    tier: str = "medium"                                     # high / medium / low


class AnalyticsSnapshotCreate(MongoBaseModel):
    """
    Payload written by the analytics service after each sampled frame.

    Validation:
      - person_count   ≥ 0
      - fps            ≥ 0
      - confidence_avg  0.0 – 1.0
      - frame_number   ≥ 1
    """
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    meta: SnapshotMeta

    frame_number: int = Field(ge=1)
    person_count: int = Field(ge=0)
    fps: float = Field(ge=0.0)
    confidence_avg: float = Field(ge=0.0, le=1.0)
    detections: Optional[List[DetectionBox]] = None          # sampled frames only


class AnalyticsSnapshotResponse(AnalyticsSnapshotCreate):
    """Add _id when reading back from MongoDB."""
    id: Optional[str] = Field(alias="_id", default=None)
