"""
AlertService — CRUD operations for the 'alerts' collection.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pymongo import ReturnDocument

from app.db.mongodb import get_db
from app.models.alert import AlertCreate, AlertUpdate, AlertSeverity, AlertType


class AlertService:

    @property
    def _col(self):
        return get_db()["alerts"]

    # ── Create ─────────────────────────────────────────────────────────────────

    async def create(self, payload: AlertCreate) -> str:
        doc = payload.model_dump()
        doc["triggered_at"] = datetime.utcnow()
        doc["is_acknowledged"] = False
        result = await self._col.insert_one(doc)
        return str(result.inserted_id)

    async def check_and_create_overcrowding_alert(
        self,
        session_id: str,
        camera_id: str,
        person_count: int,
        max_occupancy: int,
        frame_number: int,
        org_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Auto-create a critical alert when person_count exceeds max_occupancy.
        Returns the new alert _id (str) or None if no alert was needed.
        """
        if max_occupancy <= 0 or person_count <= max_occupancy:
            return None

        payload = AlertCreate(
            org_id=org_id,
            camera_id=camera_id,
            session_id=session_id,
            type=AlertType.overcrowding,
            severity=AlertSeverity.critical,
            value_at_trigger=float(person_count),
            threshold_value=float(max_occupancy),
            message=(
                f"Overcrowding detected. {person_count} persons detected, "
                f"threshold is {max_occupancy}."
            ),
            frame_number=frame_number,
        )
        return await self.create(payload)

    async def check_and_create_confidence_alert(
        self,
        session_id: str,
        camera_id: str,
        confidence_avg: float,
        min_confidence: float,
        frame_number: int,
        org_id: Optional[str] = None,
    ) -> Optional[str]:
        """Auto-create a warning alert when avg confidence drops below threshold."""
        if confidence_avg <= 0 or confidence_avg >= min_confidence:
            return None

        payload = AlertCreate(
            org_id=org_id,
            camera_id=camera_id,
            session_id=session_id,
            type=AlertType.confidence_degraded,
            severity=AlertSeverity.warning,
            value_at_trigger=round(confidence_avg, 3),
            threshold_value=round(min_confidence, 3),
            message=(
                f"Detection confidence degraded to {confidence_avg:.1%}, "
                f"below threshold {min_confidence:.1%}."
            ),
            frame_number=frame_number,
        )
        return await self.create(payload)

    # ── Read ───────────────────────────────────────────────────────────────────

    async def get_by_id(self, alert_id: str) -> Optional[dict]:
        return await self._col.find_one({"_id": ObjectId(alert_id)})

    async def list_unacknowledged(
        self,
        org_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        query: dict = {"is_acknowledged": False}
        if org_id:
            query["org_id"] = org_id
        cursor = self._col.find(query).sort("triggered_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def list_by_session(self, session_id: str) -> List[dict]:
        cursor = self._col.find({"session_id": session_id}).sort("triggered_at", 1)
        return await cursor.to_list(length=500)

    async def list_by_camera(
        self,
        camera_id: str,
        severity: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        query: dict = {"camera_id": camera_id}
        if severity:
            query["severity"] = severity
        cursor = self._col.find(query).sort("triggered_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    # ── Update ─────────────────────────────────────────────────────────────────

    async def acknowledge(self, alert_id: str, acknowledged_by: Optional[str] = None) -> Optional[dict]:
        return await self._col.find_one_and_update(
            {"_id": ObjectId(alert_id)},
            {"$set": {
                "is_acknowledged": True,
                "acknowledged_by": acknowledged_by,
                "acknowledged_at": datetime.utcnow(),
            }},
            return_document=ReturnDocument.AFTER,
        )

    async def resolve(self, alert_id: str) -> Optional[dict]:
        return await self._col.find_one_and_update(
            {"_id": ObjectId(alert_id)},
            {"$set": {"resolved_at": datetime.utcnow()}},
            return_document=ReturnDocument.AFTER,
        )

    async def update(self, alert_id: str, payload: AlertUpdate) -> Optional[dict]:
        update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not update_data:
            return await self.get_by_id(alert_id)
        return await self._col.find_one_and_update(
            {"_id": ObjectId(alert_id)},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER,
        )

    # ── Delete ─────────────────────────────────────────────────────────────────

    async def delete(self, alert_id: str) -> bool:
        result = await self._col.delete_one({"_id": ObjectId(alert_id)})
        return result.deleted_count > 0


alert_service = AlertService()
