import cv2
import os
import json
import shutil
import numpy as np
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO

app = FastAPI(title="AI Camera Platform Demo")

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the YOLOv8 model
model = YOLO('yolov8n.pt')

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Store latest analytics globally
latest_analytics = {
    "person_count": 0,
    "fps": 0,
    "confidence_avg": 0,
    "frame_number": 0,
    "total_frames": 0,
}


def draw_premium_box(frame, box, conf, person_id):
    """Draw a sleek, modern bounding box with rounded corners and glow effect."""
    x1, y1, x2, y2 = map(int, box)
    
    # Color based on confidence
    if conf >= 0.75:
        color = (72, 199, 142)       # Green - high confidence
    elif conf >= 0.60:
        color = (59, 130, 246)       # Blue - medium confidence
    else:
        color = (251, 191, 36)       # Yellow - lower confidence
    
    # Draw semi-transparent fill
    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)
    
    # Draw corner accents instead of full rectangle (more modern look)
    corner_len = min(25, (x2 - x1) // 4, (y2 - y1) // 4)
    thickness = 2
    
    # Top-left corner
    cv2.line(frame, (x1, y1), (x1 + corner_len, y1), color, thickness)
    cv2.line(frame, (x1, y1), (x1, y1 + corner_len), color, thickness)
    # Top-right corner
    cv2.line(frame, (x2, y1), (x2 - corner_len, y1), color, thickness)
    cv2.line(frame, (x2, y1), (x2, y1 + corner_len), color, thickness)
    # Bottom-left corner
    cv2.line(frame, (x1, y2), (x1 + corner_len, y2), color, thickness)
    cv2.line(frame, (x1, y2), (x1, y2 - corner_len), color, thickness)
    # Bottom-right corner
    cv2.line(frame, (x2, y2), (x2 - corner_len, y2), color, thickness)
    cv2.line(frame, (x2, y2), (x2, y2 - corner_len), color, thickness)
    
    # Label background
    label = f"#{person_id}  {conf:.0%}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.45
    (tw, th), baseline = cv2.getTextSize(label, font, font_scale, 1)
    
    label_x1 = x1
    label_y1 = y1 - th - 10
    label_x2 = x1 + tw + 10
    label_y2 = y1
    
    # Ensure label stays within frame
    if label_y1 < 0:
        label_y1 = y2
        label_y2 = y2 + th + 10
    
    cv2.rectangle(frame, (label_x1, label_y1), (label_x2, label_y2), color, -1)
    cv2.putText(frame, label, (label_x1 + 5, label_y2 - 5), font, font_scale, (255, 255, 255), 1, cv2.LINE_AA)
    
    return frame


def draw_hud(frame, person_count, fps, conf_avg, frame_num, total_frames):
    """Draw a professional heads-up display overlay."""
    h, w = frame.shape[:2]
    
    # Semi-transparent top bar
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 52), (15, 23, 42), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    
    # Divider line
    cv2.line(frame, (0, 52), (w, 52), (59, 130, 246), 1)
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # Left side: Student count with icon
    count_text = f"STUDENTS: {person_count}"
    cv2.putText(frame, count_text, (15, 35), font, 0.7, (72, 199, 142), 2, cv2.LINE_AA)
    
    # Center: Confidence
    if conf_avg > 0:
        conf_text = f"AVG CONF: {conf_avg:.0%}"
        (cw, _), _ = cv2.getTextSize(conf_text, font, 0.5, 1)
        cv2.putText(frame, conf_text, (w // 2 - cw // 2, 35), font, 0.5, (148, 163, 184), 1, cv2.LINE_AA)
    
    # Right side: Frame info and FPS
    fps_text = f"FPS: {fps:.0f}"
    (fw, _), _ = cv2.getTextSize(fps_text, font, 0.5, 1)
    cv2.putText(frame, fps_text, (w - fw - 15, 22), font, 0.5, (251, 191, 36), 1, cv2.LINE_AA)
    
    if total_frames > 0:
        progress = frame_num / total_frames
        progress_text = f"{progress:.0%}"
        (pw, _), _ = cv2.getTextSize(progress_text, font, 0.5, 1)
        cv2.putText(frame, progress_text, (w - pw - 15, 42), font, 0.5, (148, 163, 184), 1, cv2.LINE_AA)
    
    # Bottom progress bar
    if total_frames > 0:
        progress = frame_num / total_frames
        bar_y = h - 4
        cv2.rectangle(frame, (0, bar_y), (w, h), (30, 41, 59), -1)
        cv2.rectangle(frame, (0, bar_y), (int(w * progress), h), (59, 130, 246), -1)
    
    # Live indicator
    cv2.circle(frame, (w - fw - 30, 18), 4, (239, 68, 68), -1)
    
    return frame


def generate_frames(video_path: str):
    global latest_analytics
    cap = cv2.VideoCapture(video_path)
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_number = 0
    
    # Process every Nth frame for performance, but still yield smoothly
    import time
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        
        frame_number += 1
        start_time = time.time()
        
        # Run YOLOv8 inference — person class only, HIGH confidence threshold
        results = model(frame, classes=0, conf=0.55, verbose=False)
        
        inference_time = time.time() - start_time
        fps = 1.0 / inference_time if inference_time > 0 else 0
        
        # Get detections
        boxes = results[0].boxes
        person_count = len(boxes)
        
        # Calculate average confidence
        conf_avg = 0
        if person_count > 0:
            conf_avg = float(boxes.conf.mean())
        
        # Draw premium bounding boxes
        for i, (box, conf) in enumerate(zip(boxes.xyxy, boxes.conf)):
            frame = draw_premium_box(frame, box, float(conf), i + 1)
        
        # Draw HUD
        frame = draw_hud(frame, person_count, fps, conf_avg, frame_number, total_frames)
        
        # Update analytics for the API
        latest_analytics = {
            "person_count": person_count,
            "fps": round(fps, 1),
            "confidence_avg": round(conf_avg, 3),
            "frame_number": frame_number,
            "total_frames": total_frames,
        }
        
        # Encode the frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
               
    cap.release()


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"message": "Video uploaded successfully", "video_id": file.filename}


@app.get("/stream/{video_id}")
async def video_feed(video_id: str):
    file_path = os.path.join(UPLOAD_DIR, video_id)
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "Video not found"})
        
    return StreamingResponse(
        generate_frames(file_path),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/analytics")
async def get_analytics():
    """Return latest real-time analytics for the frontend."""
    return latest_analytics


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
