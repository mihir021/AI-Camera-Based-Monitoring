import cv2
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))
from app.services.inference import model, draw_premium_box, draw_hud

def test_single_frame(input_video, output_image):
    print(f"Loading video: {input_video}")
    cap = cv2.VideoCapture(input_video)
    
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    # Skip ahead to a random frame (e.g., frame 100) to grab a screenshot
    cap.set(cv2.CAP_PROP_POS_FRAMES, 100)
    success, frame = cap.read()
    if not success:
        print("Failed to read frame")
        return
        
    print("Running YOLOv8 inference...")
    # Lowered confidence threshold to 0.40 to help detect partially hidden students
    results = model(frame, classes=0, conf=0.40, verbose=False) 
    
    boxes = results[0].boxes
    person_count = len(boxes)
    conf_avg = float(boxes.conf.mean()) if person_count > 0 else 0
    
    print(f"Detected {person_count} students.")
    
    for i, (box, conf) in enumerate(zip(boxes.xyxy, boxes.conf)):
        frame = draw_premium_box(frame, box, float(conf), i + 1)
        
    frame = draw_hud(frame, person_count, 30.0, conf_avg, 100, 1000)
    
    cv2.imwrite(output_image, frame)
    print(f"Saved output to {output_image}")
    cap.release()

if __name__ == "__main__":
    # Ensure data directory exists
    os.makedirs("../data", exist_ok=True)
    test_single_frame("../../sample_classroom.mp4", "../data/classroom_test.jpg")
