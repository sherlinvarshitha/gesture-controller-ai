"""
scripts/collect_dataset.py
--------------------------
Optional: Collect your own gesture images for CNN training.
(MediaPipe alone works great for demos — use this only if you want
to fine-tune a custom model.)

How it works:
  - Opens your webcam
  - You press a key (0-5) to label a gesture class
  - It saves cropped hand region images to data/raw/<class_name>/

Gesture key map:
  0 → open_palm
  1 → closed_fist
  2 → swipe_right
  3 → swipe_left
  4 → thumb_up
  5 → thumb_down

Usage:
  python scripts/collect_dataset.py
  Press 0-5 to collect, Q to quit.
  Aim for 200+ images per class.
"""

import cv2
import os
import mediapipe as mp

CLASSES = ["open_palm", "closed_fist", "swipe_right",
           "swipe_left", "thumb_up", "thumb_down"]
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
IMG_SIZE   = 128
KEY_MAP    = {ord(str(i)): cls for i, cls in enumerate(CLASSES)}

mp_hands = mp.solutions.hands
mp_draw  = mp.solutions.drawing_utils

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for cls in CLASSES:
        os.makedirs(os.path.join(OUTPUT_DIR, cls), exist_ok=True)

    counters = {cls: len(os.listdir(os.path.join(OUTPUT_DIR, cls))) for cls in CLASSES}
    cap      = cv2.VideoCapture(0)
    current  = None

    with mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7) as hands:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res   = hands.process(rgb)

            # Draw hand
            if res.multi_hand_landmarks:
                for lm in res.multi_hand_landmarks:
                    mp_draw.draw_landmarks(frame, lm, mp_hands.HAND_CONNECTIONS)

                # Save if label active
                if current and res.multi_hand_landmarks:
                    h, w = frame.shape[:2]
                    lms  = res.multi_hand_landmarks[0].landmark
                    xs   = [int(l.x * w) for l in lms]
                    ys   = [int(l.y * h) for l in lms]
                    pad  = 30
                    x1   = max(0, min(xs) - pad)
                    y1   = max(0, min(ys) - pad)
                    x2   = min(w, max(xs) + pad)
                    y2   = min(h, max(ys) + pad)
                    crop = cv2.resize(frame[y1:y2, x1:x2], (IMG_SIZE, IMG_SIZE))
                    n    = counters[current]
                    path = os.path.join(OUTPUT_DIR, current, f"{n:05d}.jpg")
                    cv2.imwrite(path, crop)
                    counters[current] += 1

            # HUD
            hud = f"Class: {current or 'None'} | Press 0-5 to label | Q to quit"
            for i, cls in enumerate(CLASSES):
                cv2.putText(frame, f"{i}: {cls} ({counters[cls]})",
                            (10, 30 + i * 22), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, (0, 255, 150) if cls == current else (180, 180, 180), 1)
            cv2.putText(frame, hud, (10, frame.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.imshow("Dataset Collector", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key in KEY_MAP:
                current = KEY_MAP[key]
                print(f"Collecting: {current}  ({counters[current]} saved so far)")

    cap.release()
    cv2.destroyAllWindows()
    print("\nCollection complete:")
    for cls, n in counters.items():
        print(f"  {cls:<15} {n} images")

if __name__ == "__main__":
    main()
