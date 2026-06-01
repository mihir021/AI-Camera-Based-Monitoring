"""
UploadService — CRUD operations for the 'video_uploads' collection.
"""

from __future__ import annotations

from typing import List, Optional

from bson import ObjectId
from pymongo import ReturnDocument

from app.db.mongodb import get_db
from app.models.video_upload import VideoUploadCreate, VideoUploadUpdate, VideoUploadStatus


class UploadService:

    @property
    def _col(self):
        return get_db()["video_uploads"]

    # ── Create ─────────────────────────────────────────────────────────────────

    async def create(self, payload: VideoUploadCreate) -> str:
        doc = payload.model_dump()
        result = await self._col.insert_one(doc)
        return str(result.inserted_id)

    # ── Read ───────────────────────────────────────────────────────────────────

    async def get_by_id(self, upload_id: str) -> Optional[dict]:
        return await self._col.find_one({"_id": ObjectId(upload_id)})

    async def get_by_stored_filename(self, stored_filename: str) -> Optional[dict]:
        """
        Look up a video_uploads document by stored_filename.
        The stored_filename is what the frontend sends as 'video_id'.
        """
        return await self._col.find_one({"stored_filename": stored_filename})

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
        cursor = self._col.find(query).skip(skip).limit(limit).sort("uploaded_at", -1)
        return await cursor.to_list(length=limit)

    # ── Update ─────────────────────────────────────────────────────────────────

    async def update(self, upload_id: str, payload: VideoUploadUpdate) -> Optional[dict]:
        update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not update_data:
            return await self.get_by_id(upload_id)
        return await self._col.find_one_and_update(
            {"_id": ObjectId(upload_id)},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER,
        )

    async def mark_processing(self, upload_id: str) -> None:
        await self._col.update_one(
            {"_id": ObjectId(upload_id)},
            {"$set": {"status": VideoUploadStatus.processing.value}},
        )

    async def mark_archived(self, upload_id: str) -> None:
        await self._col.update_one(
            {"_id": ObjectId(upload_id)},
            {"$set": {"status": VideoUploadStatus.archived.value}},
        )

    # ── Delete ─────────────────────────────────────────────────────────────────

    async def delete(self, upload_id: str) -> bool:
        result = await self._col.delete_one({"_id": ObjectId(upload_id)})
        return result.deleted_count > 0


upload_service = UploadService()
