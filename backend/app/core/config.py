import os

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Path to the YOLOv8 model relative to this file
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../../../ai/models/yolov8n.pt')
