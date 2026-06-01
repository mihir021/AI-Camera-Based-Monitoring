"""
Incident model — investigation records with vector search support.

Blueprint reference: COLLECTION 8 — incidents
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import Field

from app.models.base import MongoBaseModel, PyObjectId


class IncidentCategory(str, Enum):
    overcrowding = "overcrowding"
    unauthorized_access = "unauthorized_access"
    equipment_failure = "equipment_failure"
    behavioral = "behavioral"
    other = "other"


class IncidentSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatus(str, Enum):
    open = "open"
    investigating = "investigating"
    resolved = "resolved"
    closed = "closed"


class IncidentAttachment(MongoBaseModel):
    url: str
    label: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class IncidentCreate(MongoBaseModel):
    org_id: Optional[str] = None
    title: str = Field(min_length=3)
    description: str = Field(min_length=10)
    category: IncidentCategory
    severity: IncidentSeverity
    camera_ids: List[str] = Field(default_factory=list)
    session_ids: List[str] = Field(default_factory=list)
    alert_ids: List[str] = Field(default_factory=list)
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    assigned_to: Optional[str] = None
    attachments: List[IncidentAttachment] = Field(default_factory=list)


class IncidentInDB(MongoBaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    org_id: Optional[str] = None
    title: str
    description: str
    category: IncidentCategory
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.open
    camera_ids: List[str] = Field(default_factory=list)
    session_ids: List[str] = Field(default_factory=list)
    alert_ids: List[str] = Field(default_factory=list)
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    reported_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    assigned_to: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    attachments: List[IncidentAttachment] = Field(default_factory=list)
    # Atlas Vector Search — Phase 4
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None


class IncidentResponse(IncidentInDB):
    pass


class IncidentUpdate(MongoBaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[IncidentCategory] = None
    severity: Optional[IncidentSeverity] = None
    status: Optional[IncidentStatus] = None
    assigned_to: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    attachments: Optional[List[IncidentAttachment]] = None
