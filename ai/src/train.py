"""
ai/src/train.py
───────────────
YOLOv8 Fine-Tuning Script for Classroom Student Detection
Developer: Dev 1 (AI / Computer Vision)

HOW TO USE:
  1. Put your labeled classroom images in:
       ai/data/images/train/   (training images)
       ai/data/images/val/     (validation images)

  2. Put your YOLO label text files in:
       ai/data/labels/train/   (one .txt per image)
       ai/data/labels/val/     (one .txt per image)

  3. Run this script from the project root:
       cd AI-Camera-Based-Monitoring
       python ai/src/train.py

  4. When training finishes, your best model is saved to:
       ai/models/classroom_v1.pt

YOLO Label Format (each .txt file):
  Each line = one object in the image
  Format:  <class_id> <x_center> <y_center> <width> <height>
  Example: 0 0.52 0.34 0.12 0.25
           ↑ class 0 = person
"""

import os
import shutil
from ultralytics import YOLO

# ─── Configuration ─────────────────────────────────────────────────────────────

# Start from the official pre-trained YOLO base model
# (We are "fine-tuning" it, not training from scratch — much faster!)
BASE_MODEL = "ai/models/yolov8n.pt"

# The dataset config we just created
DATASET_CONFIG = "ai/data/dataset.yaml"

# Where to save our trained model after it finishes
OUTPUT_MODEL_PATH = "ai/models/classroom_v1.pt"

# ─── Training Parameters ───────────────────────────────────────────────────────
EPOCHS      = 30      # How many times the AI studies all your images
              # Start with 30 for testing. Use 100+ for production accuracy.
IMAGE_SIZE  = 640     # Size of each image during training (standard for YOLO)
BATCH_SIZE  = 8       # Images processed at once. Lower if RAM runs out (try 4 or 2)
PATIENCE    = 10      # Stop early if accuracy stops improving for 10 epochs

# ─── Main Training Function ────────────────────────────────────────────────────
def train():
    print("=" * 60)
    print("  AI Camera Platform — YOLOv8 Fine-Tuning Script")
    print("=" * 60)

    # Verify the base model exists
    if not os.path.exists(BASE_MODEL):
        print(f"❌ Base model not found at {BASE_MODEL}")
        print("   Please ensure yolov8n.pt is inside ai/models/")
        return

    # Verify the dataset config exists
    if not os.path.exists(DATASET_CONFIG):
        print(f"❌ Dataset config not found at {DATASET_CONFIG}")
        return

    print(f"\n✅ Base model:    {BASE_MODEL}")
    print(f"✅ Dataset config: {DATASET_CONFIG}")
    print(f"\n🚀 Starting training for {EPOCHS} epochs...")
    print("   (This will take several minutes or hours depending on dataset size)\n")

    # Load the base model
    model = YOLO(BASE_MODEL)

    # START TRAINING
    # YOLO saves results automatically inside runs/detect/<name>/
    results = model.train(
        data=DATASET_CONFIG,
        epochs=EPOCHS,
        imgsz=IMAGE_SIZE,
        batch=BATCH_SIZE,
        patience=PATIENCE,          # Early stopping
        name="classroom_v1",        # Folder name for results
        project="ai/runs",          # Save inside ai/runs/ (not the root)
        exist_ok=True,              # Overwrite previous run if name matches
        verbose=True,
    )

    print("\n" + "=" * 60)
    print("  ✅ Training Complete!")
    print("=" * 60)

    # Copy the best trained model to our ai/models/ folder
    trained_model_path = "ai/runs/classroom_v1/weights/best.pt"
    if os.path.exists(trained_model_path):
        shutil.copy(trained_model_path, OUTPUT_MODEL_PATH)
        print(f"\n🏆 Best model saved to: {OUTPUT_MODEL_PATH}")
        print(f"   Update backend/app/core/config.py to use this new model!")
    else:
        print(f"\n⚠️ Could not find trained model at {trained_model_path}")
        print("   Check the ai/runs/ folder manually.")


if __name__ == "__main__":
    train()
