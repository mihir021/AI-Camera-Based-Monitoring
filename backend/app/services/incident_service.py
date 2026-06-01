"""
IncidentService — CRUD operations for the 'incidents' collection.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pymongo import ReturnDocument

from app.db.mongodb import get_db
from app.models.incident import IncidentCreate, IncidentUpdate, IncidentStatus


class IncidentService:

    @property
    def _col(self):
        return get_db()["incidents"]

    # ── Create ─────────────────────────────────────────────────────────────────

    async def create(self, payload: IncidentCreate) -> str:
        doc = payload.model_dump()
        doc["status"] = IncidentStatus.open.value
        doc["reported_at"] = datetime.utcnow()
        result = await self._col.insert_one(doc)
        return str(result.inserted_id)

    async def create_from_alert(
        self,
        alert_id: str,
        camera_id: str,
        session_id: str,
        title: str,
        description: str,
        category: str,
        severity: str,
        org_id: Optional[str] = None,
    ) -> str:
        """
        Convenience: auto-create an incident document linked to a critical alert.
        Called by the alert pipeline when a critical-severity alert fires.
        """
        payload = IncidentCreate(
            org_id=org_id,
            title=title,
            description=description,
            category=category,
            severity=severity,
            camera_ids=[camera_id],
            session_ids=[session_id],
            alert_ids=[alert_id],
        )
        return await self.create(payload)

    # ── Read ───────────────────────────────────────────────────────────────────

    async def get_by_id(self, incident_id: str) -> Optional[dict]:
        return await self._col.find_one({"_id": ObjectId(incident_id)})

    async def list_open(
        self,
        org_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        query: dict = {"status": {"$in": [
            IncidentStatus.open.value,
            IncidentStatus.investigating.value,
        ]}}
        if org_id:
            query["org_id"] = org_id
        cursor = self._col.find(query).sort("occurred_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def list_by_org(
        self,
        org_id: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[dict]:
        query: dict = {}
        if org_id:
            query["org_id"] = org_id
        if status:
            query["status"] = status
        if category:
            query["category"] = category
        if severity:
            query["severity"] = severity
        cursor = self._col.find(query).skip(skip).limit(limit).sort("occurred_at", -1)
        return await cursor.to_list(length=limit)

    async def list_by_camera(self, camera_id: str, limit: int = 20) -> List[dict]:
        cursor = (
            self._col.find({"camera_ids": camera_id})
            .sort("occurred_at", -1)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    # ── Update ─────────────────────────────────────────────────────────────────

    async def update(self, incident_id: str, payload: IncidentUpdate) -> Optional[dict]:
        update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not update_data:
            return await self.get_by_id(incident_id)
        return await self._col.find_one_and_update(
            {"_id": ObjectId(incident_id)},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER,
        )

    async def resolve(self, incident_id: str, resolution_notes: str) -> Optional[dict]:
        return await self._col.find_one_and_update(
            {"_id": ObjectId(incident_id)},
            {"$set": {
                "status": IncidentStatus.resolved.value,
                "resolved_at": datetime.utcnow(),
                "resolution_notes": resolution_notes,
            }},
            return_document=ReturnDocument.AFTER,
        )

    async def assign(self, incident_id: str, assignee_id: str) -> Optional[dict]:
        return await self._col.find_one_and_update(
            {"_id": ObjectId(incident_id)},
            {"$set": {
                "assigned_to": assignee_id,
                "status": IncidentStatus.investigating.value,
            }},
            return_document=ReturnDocument.AFTER,
        )

    # ── Delete ─────────────────────────────────────────────────────────────────

    async def delete(self, incident_id: str) -> bool:
        result = await self._col.delete_one({"_id": ObjectId(incident_id)})
        return result.deleted_count > 0


incident_service = IncidentService()
