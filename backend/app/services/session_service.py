"""
SessionService — CRUD operations for the 'sessions' collection.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pymongo import ReturnDocument

from app.db.mongodb import get_db
from app.models.session import SessionCreate, SessionUpdate, SessionStatus, SessionSummary


class SessionService:

    @property
    def _col(self):
        return get_db()["sessions"]

    # ── Create ─────────────────────────────────────────────────────────────────

    async def create(self, payload: SessionCreate) -> str:
        doc = payload.model_dump()
        doc["status"] = SessionStatus.processing.value
        doc["started_at"] = datetime.utcnow()
        result = await self._col.insert_one(doc)
        return str(result.inserted_id)

    # ── Read ───────────────────────────────────────────────────────────────────

    async def get_by_id(self, session_id: str) -> Optional[dict]:
        return await self._col.find_one({"_id": ObjectId(session_id)})

    async def list_by_camera(
        self,
        camera_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> List[dict]:
        cursor = (
            self._col.find({"camera_id": camera_id})
            .skip(skip)
            .limit(limit)
            .sort("started_at", -1)
        )
        return await cursor.to_list(length=limit)

    async def list_by_org(
        self,
        org_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[dict]:
        query: dict = {}
        if org_id:
            query["org_id"] = org_id
        if status:
            query["status"] = status
        cursor = self._col.find(query).skip(skip).limit(limit).sort("started_at", -1)
        return await cursor.to_list(length=limit)

    # ── Update ─────────────────────────────────────────────────────────────────

    async def update(self, session_id: str, payload: SessionUpdate) -> Optional[dict]:
        update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not update_data:
            return await self.get_by_id(session_id)
        return await self._col.find_one_and_update(
            {"_id": ObjectId(session_id)},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER,
        )

    async def increment_processed_frames(self, session_id: str, count: int = 1) -> None:
        await self._col.update_one(
            {"_id": ObjectId(session_id)},
            {"$inc": {"processed_frames": count}},
        )

    async def complete(
        self,
        session_id: str,
        summary: SessionSummary,
        total_frames: int,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Mark a session as completed and write its aggregated summary."""
        await self._col.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {
                "status": SessionStatus.completed.value,
                "completed_at": datetime.utcnow(),
                "total_frames": total_frames,
                "processed_frames": total_frames,
                "duration_seconds": duration_seconds,
                "summary": summary.model_dump(),
            }},
        )

    async def fail(self, session_id: str, error_message: str) -> None:
        """Mark a session as failed with an error message."""
        await self._col.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {
                "status": SessionStatus.failed.value,
                "completed_at": datetime.utcnow(),
                "error_message": error_message,
            }},
        )

    # ── Delete ─────────────────────────────────────────────────────────────────

    async def delete(self, session_id: str) -> bool:
        result = await self._col.delete_one({"_id": ObjectId(session_id)})
        return result.deleted_count > 0


session_service = SessionService()
