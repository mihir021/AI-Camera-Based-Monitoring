"""
UserService — CRUD operations for the 'users' collection.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pymongo import ReturnDocument

from app.db.mongodb import get_db
from app.models.user import UserCreate, UserUpdate


class UserService:
    """Async service layer for the users collection."""

    @property
    def _col(self):
        return get_db()["users"]

    # ── Create ─────────────────────────────────────────────────────────────────

    async def create(self, payload: UserCreate) -> str:
        """Hash the password and insert a new user. Returns the new _id as str."""
        doc = payload.model_dump()
        doc["password_hash"] = self._hash_password(doc.pop("password"))
        doc["is_active"] = True
        doc["created_at"] = datetime.utcnow()
        result = await self._col.insert_one(doc)
        return str(result.inserted_id)

    # ── Read ───────────────────────────────────────────────────────────────────

    async def get_by_id(self, user_id: str) -> Optional[dict]:
        return await self._col.find_one({"_id": ObjectId(user_id)})

    async def get_by_email(self, email: str) -> Optional[dict]:
        return await self._col.find_one({"email": email.lower()})

    async def list_by_org(
        self,
        org_id: str,
        role: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[dict]:
        query: dict = {"org_id": org_id}
        if role:
            query["role"] = role
        cursor = self._col.find(query).skip(skip).limit(limit).sort("created_at", -1)
        return await cursor.to_list(length=limit)

    # ── Update ─────────────────────────────────────────────────────────────────

    async def update(self, user_id: str, payload: UserUpdate) -> Optional[dict]:
        update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not update_data:
            return await self.get_by_id(user_id)
        return await self._col.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER,
        )

    async def record_login(self, user_id: str) -> None:
        await self._col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"last_login_at": datetime.utcnow()}},
        )

    # ── Delete ─────────────────────────────────────────────────────────────────

    async def deactivate(self, user_id: str) -> bool:
        """Soft-delete: set is_active=False."""
        result = await self._col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": False}},
        )
        return result.modified_count > 0

    async def hard_delete(self, user_id: str) -> bool:
        result = await self._col.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0

    # ── Auth helpers ───────────────────────────────────────────────────────────

    def _hash_password(self, password: str) -> str:
        """
        Simple SHA-256 hash for Phase 1.
        Replace with argon2 / bcrypt for production auth.
        """
        salt = secrets.token_hex(16)
        h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return f"sha256${salt}${h}"

    def verify_password(self, plain: str, password_hash: str) -> bool:
        parts = password_hash.split("$")
        if len(parts) != 3 or parts[0] != "sha256":
            return False
        _, salt, expected = parts
        h = hashlib.sha256(f"{salt}{plain}".encode()).hexdigest()
        return secrets.compare_digest(h, expected)


# ── Module-level singleton ────────────────────────────────────────────────────
user_service = UserService()
