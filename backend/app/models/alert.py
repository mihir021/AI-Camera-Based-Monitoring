"""
Alert model — threshold breach events and notifications.

Blueprint reference: COLLECTION 5 — alerts
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import Field

from app.models.base import MongoBaseModel, PyObjectId


class AlertType(str, Enum):
    overcrowding = "overcrowding"
    low_occupancy = "low_occupancy"
    confidence_degraded = "confidence_degraded"
    processing_slow = "processing_slow"
    stream_lost = "stream_lost"
    model_failure = "model_failure"


class AlertSeverity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class AlertCreate(MongoBaseModel):
    org_id: Optional[str] = None
    camera_id: str
    session_id: str
    type: AlertType
    severity: AlertSeverity
    value_at_trigger: float        # the metric value that crossed the threshold
    threshold_value: float         # the configured threshold
    message: str = Field(min_length=1)
    frame_number: Optional[int] = Field(default=None, ge=1)
    snapshot_url: Optional[str] = None


class AlertInDB(MongoBaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    org_id: Optional[str] = None
    camera_id: str
    session_id: str
    type: AlertType
    severity: AlertSeverity
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    value_at_trigger: float
    threshold_value: float
    message: str
    frame_number: Optional[int] = None
    snapshot_url: Optional[str] = None
    # Reserved for Atlas Vector Search — populated by embedding service (Phase 4)
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None


class AlertResponse(AlertInDB):
    pass


class AlertUpdate(MongoBaseModel):
    resolved_at: Optional[datetime] = None
    is_acknowledged: Optional[bool] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    snapshot_url: Optional[str] = None
