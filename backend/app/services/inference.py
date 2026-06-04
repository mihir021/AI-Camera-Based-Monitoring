"""
inference.py — SAHI + YOLOv8m crowd-detection pipeline.

Architecture (3-stage threaded pipeline):
┌─────────────────────────────────────────────────────────────┐
│  Thread 1: READER                                           │
│    cv2.VideoCapture → raw frames → frame_queue              │
├─────────────────────────────────────────────────────────────┤
│  Thread 2: INFERENCER  (SAHI + YOLOv8m)                     │
│    frame_queue → SAHI sliced predict → result_queue         │
├─────────────────────────────────────────────────────────────┤
│  Main thread: ENCODER (generator)                           │
│    result_queue → draw boxes/HUD → JPEG → yield to ASGI    │
└─────────────────────────────────────────────────────────────┘

Key upgrades vs standard YOLO inference:
  1. SAHI slicing — divides frame into 512×512 overlapping tiles
     so small / far-away students at the back of the class are caught
  2. YOLOv8m model — significantly better capacity than Nano/Small
  3. Crowd-tuned NMS (NMM, IOU 0.40) — keeps overlapping boxes
  4. Confidence threshold lowered to 0.30 to catch partial occlusions
  5. Frame-skip keeps display smooth even at lower inference FPS
  6. Parallel read + infer + encode (3× throughput on multi-core CPU)

For live camera:
  Change video_path to:
    0                      → laptop webcam
    "rtsp://IP:PORT/..."   → IP/CCTV camera stream
    "http://IP:PORT/..."   → HTTP MJPEG camera (DroidCam, IP Webcam)
"""

from __future__ import annotations
from typing import Generator
import threading
import queue
import time
import os
import cv2
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction

from app.core.config import MODEL_PATH
from app.core.state import latest_analytics

# ─────────────────────────────────────────────────────────────────────────────
# Constants — tune these for speed vs accuracy tradeoff
# ─────────────────────────────────────────────────────────────────────────────

INFERENCE_SIZE    = 640   # Kept for reference; SAHI uses full-res slices instead
CONFIDENCE_THRESH = 0.30  # Lowered to catch heavily occluded/partial students
FRAME_SKIP        = 3     # SAHI is slow per-frame: run every 3rd, reuse boxes on others
JPEG_QUALITY      = 75    # JPEG stream quality: 60=smallest, 85=best (75 is good)
QUEUE_SIZE        = 3     # SAHI is slower — smaller queue reduces RAM usage

# ─────────────────────────────────────────────────────────────────────────────
# Model singleton
# ─────────────────────────────────────────────────────────────────────────────

_model: AutoDetectionModel | None = None
_model_error: str | None = None
_model_lock = threading.Lock()


def get_model() -> AutoDetectionModel | None:
    global _model, _model_error
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:          # double-checked locking
            return _model
        try:
            import torch
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
            
            _model = AutoDetectionModel.from_pretrained(
                model_type='yolov8',
                model_path=MODEL_PATH,
                confidence_threshold=CONFIDENCE_THRESH,
                device=device,
            )

            if device == "cuda:0":
                print("🚀 SAHI YOLO running on GPU")
            else:
                print("⚠️  SAHI YOLO running on CPU — GPU not detected")

            _model_error = None
        except Exception as exc:        # noqa: BLE001
            _model_error = str(exc)
            _model = None
    return _model


def get_model_error() -> str | None:
    get_model()
    return _model_error


# ─────────────────────────────────────────────────────────────────────────────
# Drawing helpers
# ─────────────────────────────────────────────────────────────────────────────

def draw_premium_box(frame, box, conf: float, person_id: int):
    """Sleek bounding box with corner accents and confidence label."""
    x1, y1, x2, y2 = map(int, box)

    # Colour by confidence tier
    if conf >= 0.75:
        color = (72, 199, 142)      # green  — high
    elif conf >= 0.60:
        color = (59, 130, 246)      # blue   — medium
    else:
        color = (251, 191, 36)      # yellow — lower

    # Subtle fill
    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)

    # Corner accents
    cl = min(25, (x2 - x1) // 4, (y2 - y1) // 4)
    t  = 2
    cv2.line(frame, (x1, y1), (x1 + cl, y1), color, t)
    cv2.line(frame, (x1, y1), (x1, y1 + cl), color, t)
    cv2.line(frame, (x2, y1), (x2 - cl, y1), color, t)
    cv2.line(frame, (x2, y1), (x2, y1 + cl), color, t)
    cv2.line(frame, (x1, y2), (x1 + cl, y2), color, t)
    cv2.line(frame, (x1, y2), (x1, y2 - cl), color, t)
    cv2.line(frame, (x2, y2), (x2 - cl, y2), color, t)
    cv2.line(frame, (x2, y2), (x2, y2 - cl), color, t)

    # Label
    label = f"#{person_id}  {conf:.0%}"
    font  = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.45
    (tw, th), _ = cv2.getTextSize(label, font, scale, 1)
    lx1, ly1 = x1, y1 - th - 10
    lx2, ly2 = x1 + tw + 10, y1
    if ly1 < 0:
        ly1, ly2 = y2, y2 + th + 10
    cv2.rectangle(frame, (lx1, ly1), (lx2, ly2), color, -1)
    cv2.putText(frame, label, (lx1 + 5, ly2 - 5), font, scale, (255, 255, 255), 1, cv2.LINE_AA)
    return frame


def draw_hud(frame, person_count: int, fps: float,
             conf_avg: float, frame_num: int, total_frames: int):
    """Professional heads-up display overlay."""
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 52), (15, 23, 42), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    cv2.line(frame, (0, 52), (w, 52), (59, 130, 246), 1)

    font = cv2.FONT_HERSHEY_SIMPLEX

    cv2.putText(frame, f"STUDENTS: {person_count}", (15, 35),
                font, 0.7, (72, 199, 142), 2, cv2.LINE_AA)

    if conf_avg > 0:
        ct = f"AVG CONF: {conf_avg:.0%}"
        (cw, _), _ = cv2.getTextSize(ct, font, 0.5, 1)
        cv2.putText(frame, ct, (w // 2 - cw // 2, 35),
                    font, 0.5, (148, 163, 184), 1, cv2.LINE_AA)

    ft = f"FPS: {fps:.0f}"
    (fw, _), _ = cv2.getTextSize(ft, font, 0.5, 1)
    cv2.putText(frame, ft, (w - fw - 15, 22),
                font, 0.5, (251, 191, 36), 1, cv2.LINE_AA)

    if total_frames > 0:
        pt = f"{frame_num / total_frames:.0%}"
        (pw, _), _ = cv2.getTextSize(pt, font, 0.5, 1)
        cv2.putText(frame, pt, (w - pw - 15, 42),
                    font, 0.5, (148, 163, 184), 1, cv2.LINE_AA)
        bar_y = h - 4
        cv2.rectangle(frame, (0, bar_y), (w, h), (30, 41, 59), -1)
        cv2.rectangle(frame, (0, bar_y), (int(w * frame_num / total_frames), h),
                      (59, 130, 246), -1)

    cv2.circle(frame, (w - fw - 30, 18), 4, (239, 68, 68), -1)
    return frame


# ─────────────────────────────────────────────────────────────────────────────
# Optimised frame generator — 3-stage threaded pipeline
# ─────────────────────────────────────────────────────────────────────────────

def generate_frames(video_path: str) -> Generator[bytes, None, None]:
    """
    High-performance MJPEG frame generator.

    video_path can be:
      - Path to a .mp4 / .avi / .mov file   → static video
      - 0 or 1                               → webcam index
      - "rtsp://IP:PORT/stream"              → IP/CCTV camera
      - "http://IP:PORT/video"               → HTTP camera stream

    Pipeline:
      reader_thread  → frame_q → inferencer_thread → result_q → main (encode+yield)
    """
    model = get_model()
    if model is None:
        raise RuntimeError(f"YOLO model could not be loaded: {get_model_error()}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video source: {video_path}")

    # For live cameras: reduce internal buffer to get the freshest frame
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0  # 0 for live cameras

    # ── Queues ────────────────────────────────────────────────────────────────
    frame_q:  queue.Queue = queue.Queue(maxsize=QUEUE_SIZE)  # raw frames
    result_q: queue.Queue = queue.Queue(maxsize=QUEUE_SIZE)  # (frame, boxes, fps)
    stop_evt = threading.Event()

    # ── Stage 1: Reader thread ────────────────────────────────────────────────
    def reader():
        """Reads frames from video/camera as fast as possible."""
        frame_idx = 0
        while not stop_evt.is_set():
            ok, frame = cap.read()
            if not ok:
                break                       # end of file or camera disconnected
            frame_idx += 1
            try:
                frame_q.put((frame_idx, frame), timeout=1.0)
            except queue.Full:
                pass                        # drop frame if pipeline is backed up
        frame_q.put(None)                   # sentinel — signals end of stream

    # ── Stage 2: Inferencer thread ────────────────────────────────────────────
    def inferencer():
        """
        Runs YOLO inference on every Nth frame.
        For skipped frames, reuses the last detection result.
        This is the key to high FPS without losing accuracy:
          - Detections update FRAME_SKIP times per second cycle
          - Boxes are drawn on every frame (smooth video)
        """
        last_boxes      = []
        last_confs      = []
        last_fps        = 0.0
        rolling_fps     = 0.0             # smoothed FPS display
        alpha           = 0.3             # EMA smoothing factor

        while not stop_evt.is_set():
            item = frame_q.get()
            if item is None:
                result_q.put(None)        # pass sentinel downstream
                break

            frame_idx, frame = item

            # ── SAHI uses the original high-res frame ──
            # We don't resize the frame because slicing requires the high-res details
            h_orig, w_orig = frame.shape[:2]

            # ── Only run YOLO every FRAME_SKIP frames ────────────────────────
            if frame_idx % FRAME_SKIP == 0:
                t0 = time.perf_counter()

                results = get_sliced_prediction(
                    frame,
                    model,
                    slice_height=512,
                    slice_width=512,
                    overlap_height_ratio=0.2,
                    overlap_width_ratio=0.2,
                    postprocess_type="NMM",
                    postprocess_match_metric="IOU",
                    postprocess_match_threshold=0.40,  # Tuned for crowd overlap
                    postprocess_class_agnostic=False,
                    verbose=0,  # Suppress per-tile progress bar spam
                )

                elapsed = time.perf_counter() - t0
                raw_fps  = 1.0 / elapsed if elapsed > 0 else 0.0
                rolling_fps = alpha * raw_fps + (1 - alpha) * rolling_fps  # smooth
                last_fps = rolling_fps

                # Extract boxes and confs for Person (class 0)
                boxes_xyxy = []
                confs = []
                for obj in results.object_prediction_list:
                    if obj.category.id == 0:
                        b = obj.bbox
                        boxes_xyxy.append([b.minx, b.miny, b.maxx, b.maxy])
                        confs.append(obj.score.value)

                last_boxes = boxes_xyxy
                last_confs = confs

                # Update live analytics
                person_count = len(last_boxes)
                conf_avg     = float(sum(confs) / person_count) if person_count > 0 else 0.0
                latest_analytics["person_count"]   = person_count
                latest_analytics["fps"]            = round(last_fps, 1)
                latest_analytics["confidence_avg"] = round(conf_avg, 3)
                latest_analytics["frame_number"]   = frame_idx
                latest_analytics["total_frames"]   = total_frames

            # Pass frame + latest boxes to encoder (even for skipped frames)
            try:
                result_q.put(
                    (frame, last_boxes, last_confs, last_fps, frame_idx),
                    timeout=1.0,
                )
            except queue.Full:
                pass   # encoder too slow — drop this frame

    # ── Start background threads ──────────────────────────────────────────────
    t_reader = threading.Thread(target=reader,     daemon=True)
    t_infer  = threading.Thread(target=inferencer, daemon=True)
    t_reader.start()
    t_infer.start()

    # ── Stage 3: Encoder (main thread — generator) ────────────────────────────
    try:
        while True:
            item = result_q.get(timeout=5.0)
            if item is None:
                break                       # stream ended

            frame, boxes, confs, fps, frame_idx = item

            # Draw detections on the full-resolution frame
            for i, (box, conf) in enumerate(zip(boxes, confs)):
                frame = draw_premium_box(frame, box, float(conf), i + 1)

            person_count = len(boxes)
            conf_avg     = (sum(float(c) for c in confs) / person_count) if person_count > 0 else 0.0
            frame = draw_hud(frame, person_count, fps, conf_avg, frame_idx, total_frames)

            # Encode at reduced quality for streaming (faster + smaller payload)
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            if not ok:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buf.tobytes()
                + b"\r\n"
            )

    except queue.Empty:
        pass    # timeout — camera disconnected or video ended

    finally:
        stop_evt.set()
        cap.release()
        t_reader.join(timeout=2)
        t_infer.join(timeout=2)
