"""
gesture_detection.py
--------------------
Core gesture recognition engine using MediaPipe Hands.

How it works:
  1. MediaPipe detects 21 hand landmarks per frame (x, y, z coordinates).
  2. We compute finger states (up/down) + thumb direction from landmark geometry.
  3. Rules map those states to one of 6 gesture labels.
  4. A cooldown timer prevents the same gesture firing repeatedly.

Gestures detected:
  open_palm  → Play
  closed_fist → Pause
  swipe_right → Forward
  swipe_left  → Backward
  thumb_up    → Volume Up
  thumb_down  → Volume Down
"""

import cv2
import mediapipe as mp
import numpy as np
import time
from collections import deque


# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────
GESTURE_LABELS = [
    "open_palm",
    "closed_fist",
    "swipe_right",
    "swipe_left",
    "thumb_up",
    "thumb_down",
    "unknown",
]

FRIENDLY_NAMES = {
    "open_palm":    "▶  Play",
    "closed_fist":  "⏸  Pause",
    "swipe_right":  "⏩ Forward",
    "swipe_left":   "⏪ Backward",
    "thumb_up":     "🔊 Volume Up",
    "thumb_down":   "🔈 Volume Down",
    "unknown":      "—  No Gesture",
}

# Landmark indices (MediaPipe convention)
WRIST       = 0
THUMB_CMC   = 1
THUMB_MCP   = 2
THUMB_IP    = 3
THUMB_TIP   = 4
INDEX_MCP   = 5
INDEX_PIP   = 6
INDEX_DIP   = 7
INDEX_TIP   = 8
MIDDLE_MCP  = 9
MIDDLE_PIP  = 10
MIDDLE_DIP  = 11
MIDDLE_TIP  = 12
RING_MCP    = 13
RING_PIP    = 14
RING_DIP    = 15
RING_TIP    = 16
PINKY_MCP   = 17
PINKY_PIP   = 18
PINKY_DIP   = 19
PINKY_TIP   = 20


# ─────────────────────────────────────────────
#  Landmark helpers
# ─────────────────────────────────────────────

def _lm(landmarks, idx):
    """Return (x, y, z) for a landmark index."""
    p = landmarks[idx]
    return np.array([p.x, p.y, p.z])


def _fingers_extended(landmarks):
    """
    Returns a list of 5 booleans [thumb, index, middle, ring, pinky].
    True  → finger is extended (up).
    False → finger is curled (down).

    Thumb:  compare tip-x vs ip-x (horizontal check, works for right hand).
    Others: tip-y < pip-y (tip is above proximal joint in image coords).
    """
    tips  = [THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
    pips  = [THUMB_IP,  INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP]

    extended = []

    # --- Thumb (horizontal check) ---
    thumb_tip = _lm(landmarks, THUMB_TIP)
    thumb_ip  = _lm(landmarks, THUMB_IP)
    thumb_mcp = _lm(landmarks, THUMB_MCP)
    # If tip is further from palm center than IP joint, thumb is out
    palm_center = _lm(landmarks, MIDDLE_MCP)
    extended.append(
        np.linalg.norm(thumb_tip[:2] - palm_center[:2]) >
        np.linalg.norm(thumb_ip[:2]  - palm_center[:2])
    )

    # --- Four fingers (vertical check) ---
    for tip_idx, pip_idx in zip(tips[1:], pips[1:]):
        tip = _lm(landmarks, tip_idx)
        pip = _lm(landmarks, pip_idx)
        extended.append(tip[1] < pip[1])   # smaller y = higher on screen

    return extended   # [thumb, index, middle, ring, pinky]


# ─────────────────────────────────────────────
#  Gesture classifier (rule-based)
# ─────────────────────────────────────────────

class GestureClassifier:
    """Rule-based classifier built on MediaPipe landmarks."""

    def __init__(self):
        self._swipe_history = deque(maxlen=10)   # x positions for swipe detection
        self._prev_palm_x   = None

    def classify(self, landmarks, handedness="Right"):
        """
        landmarks : list of 21 mediapipe NormalizedLandmark
        handedness: "Right" or "Left" (from MediaPipe)
        Returns gesture label string.
        """
        ext = _fingers_extended(landmarks)
        thumb, index, middle, ring, pinky = ext

        wrist_x = landmarks[WRIST].x
        self._swipe_history.append(wrist_x)

        # ── Thumb Up / Down ──────────────────────────────────────────
        if thumb and not any([index, middle, ring, pinky]):
            thumb_tip_y  = landmarks[THUMB_TIP].y
            wrist_y      = landmarks[WRIST].y
            if thumb_tip_y < wrist_y - 0.05:
                return "thumb_up"
            elif thumb_tip_y > wrist_y + 0.05:
                return "thumb_down"

        # ── Open Palm ────────────────────────────────────────────────
        if all([index, middle, ring, pinky]):
            return "open_palm"

        # ── Closed Fist ──────────────────────────────────────────────
        if not any([index, middle, ring, pinky]) and not thumb:
            return "closed_fist"

        # ── Swipe Detection (motion-based) ───────────────────────────
        if len(self._swipe_history) >= 6:
            delta = self._swipe_history[-1] - self._swipe_history[0]
            if abs(delta) > 0.12:           # threshold: 12% of frame width
                # Note: MediaPipe mirrors x for front camera
                if delta < 0:
                    return "swipe_right"
                else:
                    return "swipe_left"

        return "unknown"

    def reset_swipe(self):
        self._swipe_history.clear()


# ─────────────────────────────────────────────
#  Main detector class
# ─────────────────────────────────────────────

class GestureDetector:
    """
    Full pipeline:
      frame → MediaPipe → landmarks → classify → cooldown → gesture label
    """

    def __init__(self, cooldown_sec=1.5, confidence=0.7):
        """
        cooldown_sec : seconds to wait before firing the same gesture again.
        confidence   : minimum detection confidence for MediaPipe.
        """
        self.cooldown_sec   = cooldown_sec
        self._last_gesture  = None
        self._last_time     = 0.0

        self._classifier = GestureClassifier()

        # MediaPipe setup
        self._mp_hands   = mp.solutions.hands
        self._mp_draw    = mp.solutions.drawing_utils
        self._mp_styles  = mp.solutions.drawing_styles
        self._hands      = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=confidence,
            min_tracking_confidence=confidence,
        )

    # ── Public API ────────────────────────────────────────────────────

    def process(self, frame):
        """
        Process one BGR frame.

        Returns:
          annotated_frame : frame with skeleton drawn
          gesture         : label string (or None if cooldown / unknown)
          landmarks       : raw landmark list (or None)
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)
        rgb.flags.writeable = True

        annotated = frame.copy()

        if not results.multi_hand_landmarks:
            return annotated, None, None

        hand_lm     = results.multi_hand_landmarks[0]
        handedness  = (
            results.multi_handedness[0].classification[0].label
            if results.multi_handedness else "Right"
        )

        # Draw skeleton
        self._mp_draw.draw_landmarks(
            annotated,
            hand_lm,
            self._mp_hands.HAND_CONNECTIONS,
            self._mp_styles.get_default_hand_landmarks_style(),
            self._mp_styles.get_default_hand_connections_style(),
        )

        raw_gesture = self._classifier.classify(hand_lm.landmark, handedness)

        # Apply cooldown
        now = time.time()
        if raw_gesture == "unknown":
            return annotated, None, hand_lm.landmark

        if raw_gesture == self._last_gesture and (now - self._last_time) < self.cooldown_sec:
            return annotated, None, hand_lm.landmark   # still in cooldown

        # New or different gesture — fire it
        self._last_gesture = raw_gesture
        self._last_time    = now
        return annotated, raw_gesture, hand_lm.landmark

    def release(self):
        self._hands.close()


# ─────────────────────────────────────────────
#  Standalone test (run this file directly)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    cap      = cv2.VideoCapture(0)
    detector = GestureDetector(cooldown_sec=1.5)

    print("Gesture Detector running — press Q to quit.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)   # mirror for natural interaction
        annotated, gesture, _ = detector.process(frame)

        label = FRIENDLY_NAMES.get(gesture, "—  No Gesture") if gesture else "—  No Gesture"

        # HUD overlay
        cv2.rectangle(annotated, (0, 0), (320, 50), (30, 30, 30), -1)
        cv2.putText(annotated, label, (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 150), 2)

        cv2.imshow("Gesture Detector", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    detector.release()
    cap.release()
    cv2.destroyAllWindows()
