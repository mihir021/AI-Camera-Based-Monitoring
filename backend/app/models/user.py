"""
User model — authentication, roles, preferences.

Blueprint reference: COLLECTION 1 — users
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import EmailStr, Field

from app.models.base import MongoBaseModel, PyObjectId


# ── Enums ──────────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    admin = "admin"
    operator = "operator"
    viewer = "viewer"


# ── Embedded objects ───────────────────────────────────────────────────────────

class UserPreferences(MongoBaseModel):
    timezone: str = "Asia/Kolkata"
    dashboard_refresh_ms: int = 500
    alert_notifications: bool = True


class ApiKey(MongoBaseModel):
    key_id: str
    label: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


# ── Document models ────────────────────────────────────────────────────────────

class UserCreate(MongoBaseModel):
    """Payload accepted by POST /users."""
    email: EmailStr
    full_name: str
    password: str                        # plain-text — hashed in service layer
    role: UserRole = UserRole.operator
    org_id: Optional[str] = None


class UserInDB(MongoBaseModel):
    """Full document as stored in MongoDB (includes password_hash)."""
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    email: EmailStr
    full_name: str
    password_hash: str
    role: UserRole = UserRole.operator
    org_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None
    avatar_url: Optional[str] = None
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    api_keys: List[ApiKey] = Field(default_factory=list)
    mfa_secret: Optional[str] = None


class UserResponse(MongoBaseModel):
    """Safe public representation — no password_hash, no mfa_secret."""
    id: Optional[str] = Field(alias="_id", default=None)
    email: EmailStr
    full_name: str
    role: UserRole
    org_id: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    avatar_url: Optional[str] = None
    preferences: Optional[UserPreferences] = None


class UserUpdate(MongoBaseModel):
    """Partial update payload — all fields optional."""
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    avatar_url: Optional[str] = None
    preferences: Optional[UserPreferences] = None
