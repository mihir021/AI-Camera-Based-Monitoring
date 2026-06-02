import os

# ── Upload directory ──────────────────────────────────────────────────────────
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── AI model ──────────────────────────────────────────────────────────────────
# Swap this path to change which model the backend uses:
#   yolov8n.pt        → Base pretrained model (80 general objects)
#   classroom_v1.pt   → Fine-tuned classroom student detection model
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../../../ai/models/classroom_v1.pt')

# ── MongoDB ───────────────────────────────────────────────────────────────────
# Canonical database name used across the entire application.
# All services reference this constant so renaming requires one change only.
DB_NAME = "ai_camera_platform"
