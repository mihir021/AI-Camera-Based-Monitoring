import os

# ── Upload directory ──────────────────────────────────────────────────────────
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── AI model ──────────────────────────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../../../ai/models/yolov8n.pt')

# ── MongoDB ───────────────────────────────────────────────────────────────────
# Canonical database name used across the entire application.
# All services reference this constant so renaming requires one change only.
DB_NAME = "ai_camera_platform"
