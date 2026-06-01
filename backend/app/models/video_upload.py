"""
VideoUpload model — file metadata, storage reference, lifecycle.

Blueprint reference: COLLECTION 6 — video_uploads
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from app.models.base import MongoBaseModel, PyObjectId


class VideoUploadStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    archived = "archived"
    deleted = "deleted"


class StorageType(str, Enum):
    local = "local"
    s3 = "s3"
    gcs = "gcs"


class VideoResolution(MongoBaseModel):
    width: int
    height: int


class VideoUploadCreate(MongoBaseModel):
    """Data provided at upload time (before processing)."""
    original_filename: str
    stored_filename: str
    storage_path: str
    storage_type: StorageType = StorageType.local
    file_size_bytes: int = Field(ge=0)
    mime_type: str = "video/mp4"
    uploaded_by: Optional[str] = None
    camera_id: Optional[str] = None
    org_id: Optional[str] = None
    expires_at: Optional[datetime] = None          # set for auto-deletion


class VideoUploadInDB(MongoBaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    original_filename: str
    stored_filename: str
    storage_path: str
    storage_type: StorageType = StorageType.local
    file_size_bytes: int
    mime_type: str
    duration_seconds: Optional[float] = None       # populated after processing
    resolution: Optional[VideoResolution] = None   # populated after processing
    frame_rate: Optional[float] = None             # populated after processing
    uploaded_by: Optional[str] = None
    camera_id: Optional[str] = None
    org_id: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    status: VideoUploadStatus = VideoUploadStatus.pending


class VideoUploadResponse(VideoUploadInDB):
    pass


class VideoUploadUpdate(MongoBaseModel):
    status: Optional[VideoUploadStatus] = None
    duration_seconds: Optional[float] = None
    resolution: Optional[VideoResolution] = None
    frame_rate: Optional[float] = None
    expires_at: Optional[datetime] = None
