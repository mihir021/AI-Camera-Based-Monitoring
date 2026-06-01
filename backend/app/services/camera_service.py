"""
CameraService — CRUD operations for the 'cameras' collection.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pymongo import ReturnDocument

from app.db.mongodb import get_db
from app.models.camera import CameraCreate, CameraUpdate, CameraStatus


class CameraService:

    @property
    def _col(self):
        return get_db()["cameras"]

    # ── Create ─────────────────────────────────────────────────────────────────

    async def create(self, payload: CameraCreate) -> str:
        doc = payload.model_dump()
        doc["status"] = CameraStatus.idle.value
        doc["created_at"] = datetime.utcnow()
        result = await self._col.insert_one(doc)
        return str(result.inserted_id)

    async def get_or_create_default(self, org_id: Optional[str] = None) -> str:
        """
        Return the _id of the system default camera, creating it if necessary.

        The default camera represents Zone A from the current frontend.
        """
        query = {"name": "Zone A — Default Camera"}
        if org_id:
            query["org_id"] = org_id

        existing = await self._col.find_one(query)
        if existing:
            return str(existing["_id"])

        payload = CameraCreate(
            name="Zone A — Default Camera",
            org_id=org_id,
        )
        return await self.create(payload)

    # ── Read ───────────────────────────────────────────────────────────────────

    async def get_by_id(self, camera_id: str) -> Optional[dict]:
        return await self._col.find_one({"_id": ObjectId(camera_id)})

    async def list_by_org(
        self,
        org_id: Optional[str] = None,
        status: Optional[str] = None,
        zone: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[dict]:
        query: dict = {}
        if org_id:
            query["org_id"] = org_id
        if status:
            query["status"] = status
        if zone:
            query["location.zone"] = zone
        cursor = self._col.find(query).skip(skip).limit(limit).sort("last_active_at", -1)
        return await cursor.to_list(length=limit)

    # ── Update ─────────────────────────────────────────────────────────────────

    async def update(self, camera_id: str, payload: CameraUpdate) -> Optional[dict]:
        update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not update_data:
            return await self.get_by_id(camera_id)
        return await self._col.find_one_and_update(
            {"_id": ObjectId(camera_id)},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER,
        )

    async def mark_active(self, camera_id: str) -> None:
        """Update status → active and refresh last_active_at timestamp."""
        await self._col.update_one(
            {"_id": ObjectId(camera_id)},
            {"$set": {
                "status": CameraStatus.active.value,
                "last_active_at": datetime.utcnow(),
            }},
        )

    async def mark_idle(self, camera_id: str) -> None:
        await self._col.update_one(
            {"_id": ObjectId(camera_id)},
            {"$set": {"status": CameraStatus.idle.value}},
        )

    # ── Delete ─────────────────────────────────────────────────────────────────

    async def delete(self, camera_id: str) -> bool:
        result = await self._col.delete_one({"_id": ObjectId(camera_id)})
        return result.deleted_count > 0


camera_service = CameraService()
