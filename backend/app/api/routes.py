"""
API routes — all endpoints for the AI Camera Platform backend.

Existing routes (preserved, backward compatible):
  POST /upload          — upload a video file
  GET  /stream/{id}     — MJPEG stream with YOLO inference
  GET  /analytics       — real-time in-memory analytics dict

New routes (added — do not affect frontend):
  GET  /sessions        — list sessions
  GET  /sessions/{id}   — session detail + analytics summary
  GET  /sessions/{id}/analytics  — raw time-series snapshots for a session
  GET  /cameras         — list cameras
  GET  /alerts          — list unacknowledged alerts
  GET  /alerts/{id}/acknowledge  — acknowledge an alert
  GET  /incidents       — list open incidents
  POST /incidents       — create incident
  GET  /health          — liveness check
"""

from __future__ import annotations

import asyncio
import os
import shutil
import threading
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.config import UPLOAD_DIR
from app.core.state import latest_analytics
from app.models.incident import IncidentCreate
from app.models.video_upload import VideoUploadCreate
from app.models.session import SessionCreate
from app.services.analytics_service import analytics_service
from app.services.alert_service import alert_service
from app.services.camera_service import camera_service
from app.services.incident_service import incident_service
from app.services.session_service import session_service
from app.services.upload_service import upload_service
from app.services.inference import generate_frames, get_model_error

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Existing routes (preserved — no breaking changes)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file.

    Changes vs Phase 1:
      - Generates a UUID-based stored_filename (safe, no path-traversal risk)
      - Creates a video_uploads document in MongoDB
      - Creates a sessions document in MongoDB
      - Still returns video_id = stored_filename for frontend backward compat
      - Falls back gracefully if DB is unavailable
    """
    # ── Persist to disk ───────────────────────────────────────────────────────
    original_name = file.filename or "upload"
    suffix = Path(original_name).suffix.lower() or ".mp4"
    stored_filename = f"{uuid4().hex}{suffix}"
    file_path = os.path.join(UPLOAD_DIR, stored_filename)

    with open(file_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    file_size = os.path.getsize(file_path)

    # ── Persist upload metadata to MongoDB ───────────────────────────────────
    upload_id: str | None = None
    session_id: str | None = None

    try:
        # Get or create the default camera (Zone A)
        camera_id = await camera_service.get_or_create_default()

        upload_payload = VideoUploadCreate(
            original_filename=original_name,
            stored_filename=stored_filename,
            storage_path=file_path,
            file_size_bytes=file_size,
            mime_type=file.content_type or "video/mp4",
            camera_id=camera_id,
        )
        upload_id = await upload_service.create(upload_payload)

        session_payload = SessionCreate(
            camera_id=camera_id,
            upload_id=upload_id,
        )
        session_id = await session_service.create(session_payload)

        await camera_service.mark_active(camera_id)

    except Exception as exc:  # noqa: BLE001
        # DB persistence failure must NOT break the upload response
        print(f"[WARN] DB persistence during upload failed: {exc}")

    return {
        "message": "Video uploaded successfully",
        "video_id": stored_filename,          # backward compat — frontend uses this
        "upload_id": upload_id,
        "session_id": session_id,
    }


@router.get("/stream/{video_id}")
async def video_feed(video_id: str):
    """
    MJPEG stream with YOLO inference.

    Changes vs Phase 1:
      - Looks up file path from MongoDB (falls back to disk check)
      - Launches a background asyncio task that samples latest_analytics every
        second and persists snapshots to analytics_snapshots (time-series)
      - Marks the session as completed when the stream ends
      - Still returns an identical MJPEG stream — frontend is unaffected
    """
    # ── Resolve file path ─────────────────────────────────────────────────────
    db_doc = None
    camera_id_for_session: str | None = None
    session_id_for_stream: str | None = None

    try:
        db_doc = await upload_service.get_by_stored_filename(video_id)
    except Exception:  # noqa: BLE001
        pass

    if db_doc:
        file_path = db_doc["storage_path"]
        camera_id_for_session = db_doc.get("camera_id")
    else:
        # Fallback: Phase 1 behaviour — look on disk directly
        file_path = os.path.join(UPLOAD_DIR, video_id)

    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "Video not found"})

    # ── Check AI model ────────────────────────────────────────────────────────
    model_error = get_model_error()
    if model_error is not None:
        return JSONResponse(
            status_code=503,
            content={"error": "AI model unavailable", "details": model_error},
        )

    # ── Find most recent session for this upload ──────────────────────────────
    try:
        if camera_id_for_session:
            sessions = await session_service.list_by_camera(camera_id_for_session, limit=1)
            if sessions:
                session_id_for_stream = str(sessions[0]["_id"])
    except Exception:  # noqa: BLE001
        pass

    # ── Async streaming generator with background analytics saver ─────────────
    async def stream_frames_async():
        """
        Wraps the sync generate_frames() generator.

        Strategy:
          1. Run sync generator in a daemon thread.
          2. Thread pushes JPEG chunks into a bounded asyncio.Queue.
          3. This async generator awaits each chunk and yields to ASGI.
          4. An asyncio.Task samples latest_analytics every second → MongoDB.
          5. On stream end (None sentinel), cancel the saver task and finalise session.
        """
        # Bounded queue — prevents memory blow-up if consumer is slow
        frame_queue: asyncio.Queue = asyncio.Queue(maxsize=8)
        loop = asyncio.get_event_loop()

        def run_sync_generator():
            """Thread target: iterate sync generator, push to queue."""
            try:
                for chunk in generate_frames(file_path):
                    future = asyncio.run_coroutine_threadsafe(
                        frame_queue.put(chunk), loop
                    )
                    future.result(timeout=10)
            except Exception:  # noqa: BLE001
                pass
            finally:
                asyncio.run_coroutine_threadsafe(
                    frame_queue.put(None), loop   # sentinel
                ).result(timeout=5)

        # Start analytics saver task (only if we have a real session)
        saver_task: asyncio.Task | None = None
        if session_id_for_stream and camera_id_for_session:
            saver_task = asyncio.create_task(
                analytics_service.periodic_snapshot_saver(
                    session_id=session_id_for_stream,
                    camera_id=camera_id_for_session,
                )
            )

        # Run the sync generator in a daemon thread
        gen_thread = threading.Thread(target=run_sync_generator, daemon=True)
        gen_thread.start()

        total_frames_seen = 0
        try:
            while True:
                chunk = await frame_queue.get()
                if chunk is None:
                    break
                total_frames_seen += 1
                yield chunk
        finally:
            # ── Cleanup ────────────────────────────────────────────────────
            if saver_task and not saver_task.done():
                saver_task.cancel()
                try:
                    await saver_task
                except asyncio.CancelledError:
                    pass

            # Finalise the session with aggregated summary
            if session_id_for_stream:
                try:
                    from app.models.session import SessionSummary
                    agg = await analytics_service.get_session_summary(
                        session_id_for_stream
                    )
                    summary = SessionSummary(**agg)
                    total_f = latest_analytics.get("total_frames", 0)
                    await session_service.complete(
                        session_id=session_id_for_stream,
                        summary=summary,
                        total_frames=total_f,
                    )
                    if camera_id_for_session:
                        await camera_service.mark_idle(camera_id_for_session)
                except Exception:  # noqa: BLE001
                    pass

            gen_thread.join(timeout=2)

    return StreamingResponse(
        stream_frames_async(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/stream-url")
async def video_feed_url(url: str):
    """
    Directly streams an RTSP/HTTP URL (e.g., from a mobile IP Webcam app).
    Bypasses DB lookup and session management for quick testing.
    """
    model_error = get_model_error()
    if model_error is not None:
        return JSONResponse(
            status_code=503,
            content={"error": "AI model unavailable", "details": model_error},
        )

    async def stream_frames_async():
        frame_queue: asyncio.Queue = asyncio.Queue(maxsize=8)
        loop = asyncio.get_event_loop()

        def run_sync_generator():
            try:
                # generate_frames gracefully accepts HTTP/RTSP URLs
                for chunk in generate_frames(url):
                    future = asyncio.run_coroutine_threadsafe(
                        frame_queue.put(chunk), loop
                    )
                    future.result(timeout=10)
            except Exception:  # noqa: BLE001
                pass
            finally:
                asyncio.run_coroutine_threadsafe(
                    frame_queue.put(None), loop
                ).result(timeout=5)

        gen_thread = threading.Thread(target=run_sync_generator, daemon=True)
        gen_thread.start()

        try:
            while True:
                chunk = await frame_queue.get()
                if chunk is None:
                    break
                yield chunk
        finally:
            gen_thread.join(timeout=2)

    return StreamingResponse(
        stream_frames_async(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/analytics")
async def get_analytics():
    """
    Return latest real-time analytics for the frontend.

    Unchanged — returns the in-memory dict that YOLO updates per-frame.
    The 500 ms polling from the frontend continues to work identically.
    """
    return latest_analytics


# ─────────────────────────────────────────────────────────────────────────────
# New routes (additional — do not affect existing frontend)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    """Liveness check — returns DB connection status."""
    from app.db.mongodb import get_db
    db_ok = get_db() is not None
    return {"status": "ok" if db_ok else "degraded", "db_connected": db_ok}


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions(status: str | None = None, limit: int = 20):
    docs = await session_service.list_by_org(status=status, limit=limit)
    return _serialise_list(docs)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    doc = await session_service.get_by_id(session_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    return _serialise(doc)


@router.get("/sessions/{session_id}/analytics")
async def get_session_analytics(session_id: str, limit: int = 1000):
    """Return time-series snapshots for a completed session (historical charts)."""
    docs = await analytics_service.get_session_history(session_id, limit=limit)
    return _serialise_list(docs)


# ── Cameras ───────────────────────────────────────────────────────────────────

@router.get("/cameras")
async def list_cameras(zone: str | None = None, limit: int = 50):
    docs = await camera_service.list_by_org(zone=zone, limit=limit)
    return _serialise_list(docs)


@router.get("/cameras/{camera_id}")
async def get_camera(camera_id: str):
    doc = await camera_service.get_by_id(camera_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Camera not found")
    return _serialise(doc)


# ── Alerts ────────────────────────────────────────────────────────────────────

@router.get("/alerts")
async def list_alerts(unacknowledged_only: bool = True, limit: int = 50):
    if unacknowledged_only:
        docs = await alert_service.list_unacknowledged(limit=limit)
    else:
        docs = await alert_service.list_unacknowledged(limit=limit)  # extend later
    return _serialise_list(docs)


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    doc = await alert_service.acknowledge(alert_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _serialise(doc)


# ── Incidents ─────────────────────────────────────────────────────────────────

@router.get("/incidents")
async def list_incidents(status: str | None = None, limit: int = 20):
    docs = await incident_service.list_by_org(status=status, limit=limit)
    return _serialise_list(docs)


@router.post("/incidents")
async def create_incident(payload: IncidentCreate):
    incident_id = await incident_service.create(payload)
    return {"id": incident_id, "message": "Incident created"}


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    doc = await incident_service.get_by_id(incident_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _serialise(doc)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _serialise(doc: dict) -> dict:
    """Convert ObjectId → str and datetime → ISO string for JSON responses."""
    from bson import ObjectId
    from datetime import datetime
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = _serialise(v)
        elif isinstance(v, list):
            out[k] = [_serialise(i) if isinstance(i, dict) else
                      str(i) if isinstance(i, ObjectId) else i
                      for i in v]
        else:
            out[k] = v
    return out


def _serialise_list(docs: list) -> list:
    return [_serialise(d) for d in docs]
