"""
AnalyticsService — writes to the 'analytics_snapshots' time-series collection
and provides aggregation helpers for the dashboard API.

Dual-write design:
  - latest_analytics dict  → real-time polling (500 ms interval, frontend)
  - analytics_snapshots    → durable historical record (MongoDB time-series)

The periodic_snapshot_saver() coroutine bridges the two: it samples the
in-memory dict every SAMPLE_INTERVAL_SECONDS and writes a document to MongoDB.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.state import latest_analytics
from app.db.mongodb import get_db
from app.models.analytics_snapshot import AnalyticsSnapshotCreate, SnapshotMeta

# How often (seconds) to sample latest_analytics and persist to MongoDB.
# Chosen to balance write volume vs. historical resolution.
SAMPLE_INTERVAL_SECONDS: float = 1.0


class AnalyticsService:

    @property
    def _col(self):
        return get_db()["analytics_snapshots"]

    # ── Write ──────────────────────────────────────────────────────────────────

    async def save_snapshot(
        self,
        session_id: str,
        camera_id: str,
        analytics: Dict[str, Any],
        org_id: Optional[str] = None,
    ) -> None:
        """
        Validate and insert one analytics snapshot into the time-series collection.

        Skips the write if frame_number == 0 (no frames processed yet).
        """
        frame_number = analytics.get("frame_number", 0)
        if frame_number <= 0:
            return

        confidence_avg = float(analytics.get("confidence_avg", 0.0))
        fps = float(analytics.get("fps", 0.0))
        person_count = int(analytics.get("person_count", 0))

        # Clamp confidence to valid range to avoid validation errors
        confidence_avg = max(0.0, min(1.0, confidence_avg))

        payload = AnalyticsSnapshotCreate(
            timestamp=datetime.utcnow(),
            meta=SnapshotMeta(
                session_id=session_id,
                camera_id=camera_id,
                org_id=org_id,
            ),
            frame_number=frame_number,
            person_count=person_count,
            fps=fps,
            confidence_avg=confidence_avg,
        )

        try:
            await self._col.insert_one(payload.model_dump())
        except Exception:   # noqa: BLE001  — never crash the stream for a DB write
            pass

    async def bulk_save(self, docs: List[dict]) -> None:
        """Insert a batch of pre-validated snapshot dicts."""
        if docs:
            try:
                await self._col.insert_many(docs, ordered=False)
            except Exception:  # noqa: BLE001
                pass

    # ── Periodic background saver ──────────────────────────────────────────────

    async def periodic_snapshot_saver(
        self,
        session_id: str,
        camera_id: str,
        org_id: Optional[str] = None,
    ) -> None:
        """
        Long-running coroutine launched as asyncio.create_task().

        Samples latest_analytics every SAMPLE_INTERVAL_SECONDS and persists
        the data to MongoDB.  Designed to run for the lifetime of a streaming
        session — cancel the task to stop it.

        The coroutine is intentionally tolerant of cancellation (CancelledError
        is re-raised normally, which asyncio.create_task() handles cleanly).
        """
        last_frame: int = -1

        while True:
            await asyncio.sleep(SAMPLE_INTERVAL_SECONDS)

            # Only save if a new frame has been processed since last check
            current_frame = latest_analytics.get("frame_number", 0)
            if current_frame > last_frame:
                last_frame = current_frame
                await self.save_snapshot(session_id, camera_id, dict(latest_analytics), org_id)

    # ── Read / Aggregation ─────────────────────────────────────────────────────

    async def get_latest_for_camera(self, camera_id: str) -> Optional[dict]:
        """Return the most recent snapshot document for a given camera."""
        cursor = (
            self._col.find({"meta.camera_id": camera_id})
            .sort("timestamp", -1)
            .limit(1)
        )
        docs = await cursor.to_list(length=1)
        return docs[0] if docs else None

    async def get_session_history(
        self,
        session_id: str,
        limit: int = 1000,
    ) -> List[dict]:
        """Return all snapshots for a session ordered by time."""
        cursor = (
            self._col.find({"meta.session_id": session_id})
            .sort("timestamp", 1)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def get_session_summary(self, session_id: str) -> dict:
        """
        Aggregate analytics_snapshots to produce a session summary dict.

        Used by SessionService.complete() to compute the final summary.
        """
        pipeline = [
            {"$match": {"meta.session_id": session_id}},
            {"$group": {
                "_id": "$meta.session_id",
                "peak_person_count": {"$max": "$person_count"},
                "avg_person_count": {"$avg": "$person_count"},
                "avg_confidence": {"$avg": "$confidence_avg"},
                "avg_fps": {"$avg": "$fps"},
                "total_snapshots": {"$sum": 1},
            }},
        ]
        results = await self._col.aggregate(pipeline).to_list(length=1)
        if results:
            doc = results[0]
            return {
                "peak_person_count": int(doc.get("peak_person_count", 0)),
                "avg_person_count": round(float(doc.get("avg_person_count", 0)), 2),
                "avg_confidence": round(float(doc.get("avg_confidence", 0)), 3),
                "avg_fps": round(float(doc.get("avg_fps", 0)), 1),
                "total_snapshots": int(doc.get("total_snapshots", 0)),
                "alert_count": 0,
            }
        return {
            "peak_person_count": 0,
            "avg_person_count": 0.0,
            "avg_confidence": 0.0,
            "avg_fps": 0.0,
            "total_snapshots": 0,
            "alert_count": 0,
        }


analytics_service = AnalyticsService()
