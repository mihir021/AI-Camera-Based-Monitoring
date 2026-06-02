"""
ai/src/prepare_data.py
──────────────────────
Frame Extractor — Turns your classroom .mp4 videos into training images.

HOW TO USE:
  1. Put your classroom .mp4 videos inside:  ai/data/raw_videos/
  2. Run from the project root:
       python ai/src/prepare_data.py
  3. Extracted frames will appear in:
       ai/data/images/train/    (80% of frames)
       ai/data/images/val/      (20% of frames)
  4. NEXT STEP: Open Roboflow or CVAT and manually draw boxes
     around every student in those images to create label files.

WHY DO THIS?
  Instead of searching the internet for classroom images, you can use
  YOUR OWN real classroom footage. This makes the model much more
  accurate because it learns from the exact environment it will be
  deployed in (same lighting, same camera angle, same desks).
"""

import cv2
import os
import random

# ─── Configuration ─────────────────────────────────────────────────────────────
RAW_VIDEOS_DIR = "ai/data/raw_videos"       # Put your .mp4 files here
TRAIN_OUTPUT   = "ai/data/images/train"     # 80% goes here
VAL_OUTPUT     = "ai/data/images/val"       # 20% goes here
FRAME_INTERVAL = 30                         # Extract 1 frame every 30 frames (~1 per second)
VAL_SPLIT      = 0.2                        # 20% of frames become validation data

# ─── Main ──────────────────────────────────────────────────────────────────────
def extract_frames():
    print("=" * 60)
    print("  Frame Extractor — Preparing Training Dataset")
    print("=" * 60)

    os.makedirs(RAW_VIDEOS_DIR, exist_ok=True)
    os.makedirs(TRAIN_OUTPUT, exist_ok=True)
    os.makedirs(VAL_OUTPUT, exist_ok=True)

    video_files = [f for f in os.listdir(RAW_VIDEOS_DIR) if f.endswith(".mp4")]

    if not video_files:
        print(f"\n⚠️  No .mp4 videos found in {RAW_VIDEOS_DIR}")
        print("   Please add your classroom videos and run again.")
        return

    total_extracted = 0

    for video_file in video_files:
        video_path = os.path.join(RAW_VIDEOS_DIR, video_file)
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_name = os.path.splitext(video_file)[0]

        print(f"\n📹 Processing: {video_file} ({total_frames} frames)")

        frame_number = 0
        saved = 0

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            frame_number += 1

            # Only extract every Nth frame to avoid duplicates
            if frame_number % FRAME_INTERVAL != 0:
                continue

            # Randomly assign to train or val set
            split = "val" if random.random() < VAL_SPLIT else "train"
            output_dir = VAL_OUTPUT if split == "val" else TRAIN_OUTPUT

            filename = f"{video_name}_frame{frame_number:05d}.jpg"
            output_path = os.path.join(output_dir, filename)
            cv2.imwrite(output_path, frame)
            saved += 1
            total_extracted += 1

        cap.release()
        print(f"   ✅ Extracted {saved} frames from {video_file}")

    print(f"\n🏁 Done! Total frames extracted: {total_extracted}")
    print(f"   Training images: {TRAIN_OUTPUT}")
    print(f"   Validation images: {VAL_OUTPUT}")
    print(f"\n👉 NEXT STEP: Go to https://roboflow.com and upload these")
    print(f"   images to draw bounding boxes around every student.")
    print(f"   Then download the labeled data in YOLO format back into")
    print(f"   ai/data/labels/train/ and ai/data/labels/val/")


if __name__ == "__main__":
    extract_frames()
