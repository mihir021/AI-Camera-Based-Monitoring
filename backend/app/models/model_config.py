"""
ModelConfig model — versioned AI inference configuration registry.

Blueprint reference: COLLECTION 7 — model_configs
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from app.models.base import MongoBaseModel, PyObjectId


class ModelConfigCreate(MongoBaseModel):
    name: str
    org_id: Optional[str] = None
    model_variant: str = "yolov8n"
    confidence_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    target_classes: List[int] = Field(default_factory=lambda: [0])
    max_detections: Optional[int] = Field(default=100, ge=1)
    is_default: bool = False
    created_by: Optional[str] = None
    notes: Optional[str] = None


class ModelConfigInDB(MongoBaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    org_id: Optional[str] = None
    model_variant: str = "yolov8n"
    confidence_threshold: float = 0.55
    iou_threshold: float = 0.45
    target_classes: List[int] = Field(default_factory=lambda: [0])
    max_detections: Optional[int] = 100
    is_default: bool = False
    version: int = 1
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None


class ModelConfigResponse(ModelConfigInDB):
    pass


class ModelConfigUpdate(MongoBaseModel):
    name: Optional[str] = None
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    iou_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    target_classes: Optional[List[int]] = None
    max_detections: Optional[int] = Field(default=None, ge=1)
    is_default: Optional[bool] = None
    notes: Optional[str] = None


# ── System default document ────────────────────────────────────────────────────
# Inserted on first startup if no default config exists.
DEFAULT_MODEL_CONFIG: dict = {
    "name": "Default — Person Detection (YOLOv8 Nano)",
    "org_id": None,
    "model_variant": "yolov8n",
    "confidence_threshold": 0.55,   # matches current inference.py hardcoded value
    "iou_threshold": 0.45,
    "target_classes": [0],          # 0 = person (COCO class)
    "max_detections": 100,
    "is_default": True,
    "version": 1,
    "created_by": None,
    "notes": "System default. Matches Phase 1 hardcoded inference.py values.",
}
