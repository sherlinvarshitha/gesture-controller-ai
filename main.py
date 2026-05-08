"""
main.py
-------
Entry point for the Gesture Controller application.
Run this file to launch the full desktop UI.

Usage:
    python main.py           # Launch full GUI
    python main.py --nogui   # Run in terminal (webcam window only)
"""

import sys
import os

# Add src/ to path so all modules resolve cleanly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def launch_gui():
    """Launch the PyQt5 desktop application."""
    try:
        from src.ui_app import run_app
        run_app()
    except ImportError as e:
        print(f"[ERROR] PyQt5 not installed: {e}")
        print("Install with:  pip install PyQt5")
        sys.exit(1)


def launch_terminal():
    """Run gesture detection in a plain OpenCV window (no GUI)."""
    import cv2
    from src.gesture_detection import GestureDetector, FRIENDLY_NAMES
    from src.windows_control import WindowsController

    detector = GestureDetector(cooldown_sec=1.5)
    controller = WindowsController()
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[ERROR] Cannot open webcam.")
        sys.exit(1)

    print("Gesture Controller running — press Q to quit.")
    print("Gestures: open palm, closed fist, swipe left/right, thumb up/down\n")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        annotated, gesture, _ = detector.process(frame)

        label = FRIENDLY_NAMES.get(gesture, "—") if gesture else "—"

        if gesture:
            action = controller.execute(gesture)
            if action:
                print(f"  Gesture: {label:<20}  →  Action: {action}")

        # HUD
        cv2.rectangle(annotated, (0, 0), (400, 55), (20, 20, 40), -1)
        cv2.putText(annotated, label, (12, 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 212, 170), 2)

        cv2.imshow("Gesture Controller — Press Q to quit", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    detector.release()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    if "--nogui" in sys.argv:
        launch_terminal()
    else:
        launch_gui()
