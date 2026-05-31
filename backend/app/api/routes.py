import os
import shutil
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse

from app.core.config import UPLOAD_DIR
from app.core.state import latest_analytics
from app.services.inference import generate_frames

router = APIRouter()

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"message": "Video uploaded successfully", "video_id": file.filename}

@router.get("/stream/{video_id}")
async def video_feed(video_id: str):
    file_path = os.path.join(UPLOAD_DIR, video_id)
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "Video not found"})
        
    return StreamingResponse(
        generate_frames(file_path),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/analytics")
async def get_analytics():
    """Return latest real-time analytics for the frontend."""
    return latest_analytics
