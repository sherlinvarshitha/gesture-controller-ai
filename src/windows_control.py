"""
windows_control.py
------------------
Maps recognized gestures to Windows OS actions using PyAutoGUI.

Actions:
  open_palm    → Space bar          (Play / Pause media)
  closed_fist  → Space bar          (Play / Pause media)
  swipe_right  → Right arrow key    (Skip forward)
  swipe_left   → Left arrow key     (Skip backward)
  thumb_up     → Volume Up          (system volume)
  thumb_down   → Volume Down        (system volume)

Why a separate module?
  Keeping OS control isolated means you can swap it out (e.g. for Linux / macOS)
  without touching the detection or UI code.
"""

import time
import logging

# PyAutoGUI is the cross-platform automation library.
# 'pause' adds a small delay after every action (safety net).
try:
    import pyautogui
    pyautogui.PAUSE = 0.05          # 50 ms gap between PyAutoGUI calls
    pyautogui.FAILSAFE = True       # move mouse to corner to abort
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    logging.warning("PyAutoGUI not installed — Windows control disabled.")

# Windows-only volume control via ctypes
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    VOLUME_API_AVAILABLE = True
except ImportError:
    VOLUME_API_AVAILABLE = False
    logging.warning(
        "pycaw not installed — volume control will use keyboard fallback."
    )

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Volume controller (pycaw preferred, keyboard fallback)
# ─────────────────────────────────────────────

class VolumeController:
    """
    Adjusts system volume.
    Uses pycaw (precise dB control) when available,
    falls back to pressing the keyboard volume keys.
    """

    STEP = 0.05   # 5 % per gesture

    def __init__(self):
        self._volume_interface = None
        if VOLUME_API_AVAILABLE:
            try:
                devices   = AudioUtilities.GetSpeakers()
                interface = devices.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None
                )
                self._volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
                logger.info("pycaw volume interface ready.")
            except Exception as e:
                logger.warning(f"pycaw init failed: {e}. Using keyboard fallback.")

    def up(self):
        if self._volume_interface:
            current = self._volume_interface.GetMasterVolumeLevelScalar()
            self._volume_interface.SetMasterVolumeLevelScalar(
                min(1.0, current + self.STEP), None
            )
        elif PYAUTOGUI_AVAILABLE:
            pyautogui.press("volumeup")

    def down(self):
        if self._volume_interface:
            current = self._volume_interface.GetMasterVolumeLevelScalar()
            self._volume_interface.SetMasterVolumeLevelScalar(
                max(0.0, current - self.STEP), None
            )
        elif PYAUTOGUI_AVAILABLE:
            pyautogui.press("volumedown")

    def get_level(self):
        """Returns current volume as 0–100 integer, or None."""
        if self._volume_interface:
            return int(self._volume_interface.GetMasterVolumeLevelScalar() * 100)
        return None


# ─────────────────────────────────────────────
#  Windows controller
# ─────────────────────────────────────────────

class WindowsController:
    """
    Translates gesture labels into Windows keyboard / volume actions.

    False-detection guard
    ---------------------
    Each gesture must be confirmed for `confirm_frames` consecutive frames
    before an action is triggered. This prevents single-frame glitches from
    firing unwanted key presses.

    Cooldown
    --------
    After firing an action the controller is silent for `cooldown_sec` seconds.
    This is a second layer of protection on top of GestureDetector's own cooldown.
    """

    # gesture label → (action description, callable)
    # We build the map lazily so VolumeController is constructed once.
    def __init__(self, cooldown_sec: float = 1.2, confirm_frames: int = 2):
        self.cooldown_sec    = cooldown_sec
        self.confirm_frames  = confirm_frames

        self._last_action_time = 0.0
        self._pending_gesture  = None
        self._pending_count    = 0

        self._volume = VolumeController()

        self._action_map = {
            "open_palm":    ("▶  Play / Pause",  self._play_pause),
            "closed_fist":  ("⏸  Play / Pause",  self._play_pause),
            "swipe_right":  ("⏩ Forward",        self._forward),
            "swipe_left":   ("⏪ Backward",       self._backward),
            "thumb_up":     ("🔊 Volume Up",      self._vol_up),
            "thumb_down":   ("🔈 Volume Down",    self._vol_down),
        }

        logger.info("WindowsController ready.")

    # ── Action executors ─────────────────────────────────────────────

    @staticmethod
    def _play_pause():
        if PYAUTOGUI_AVAILABLE:
            pyautogui.press("space")

    @staticmethod
    def _forward():
        if PYAUTOGUI_AVAILABLE:
            pyautogui.press("right")

    @staticmethod
    def _backward():
        if PYAUTOGUI_AVAILABLE:
            pyautogui.press("left")

    def _vol_up(self):
        self._volume.up()

    def _vol_down(self):
        self._volume.down()

    # ── Public API ────────────────────────────────────────────────────

    def execute(self, gesture: str) -> str | None:
        """
        Call this every frame with the gesture label (or None).

        Returns the action description string when an action fires,
        otherwise None.
        """
        if gesture is None or gesture not in self._action_map:
            self._pending_gesture = None
            self._pending_count   = 0
            return None

        now = time.time()

        # Cooldown check
        if (now - self._last_action_time) < self.cooldown_sec:
            return None

        # Confirmation accumulation
        if gesture == self._pending_gesture:
            self._pending_count += 1
        else:
            self._pending_gesture = gesture
            self._pending_count   = 1

        if self._pending_count < self.confirm_frames:
            return None   # not confirmed yet

        # ── Fire the action ──
        description, fn = self._action_map[gesture]
        try:
            fn()
            self._last_action_time = now
            self._pending_gesture  = None
            self._pending_count    = 0
            logger.info(f"Action fired: {description}")
            return description
        except Exception as e:
            logger.error(f"Action failed for '{gesture}': {e}")
            return None

    def get_volume_level(self) -> int | None:
        return self._volume.get_level()
