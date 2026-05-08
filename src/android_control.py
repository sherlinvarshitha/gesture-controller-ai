"""
android_control.py
------------------
Controls an Android device over ADB (Android Debug Bridge).

Supports USB and WiFi connections.

ADB Setup (Windows)
-------------------
1. Download "Android SDK Platform Tools" from:
   https://developer.android.com/studio/releases/platform-tools
2. Extract the zip → add the folder to your system PATH.
3. Enable "Developer Options" on your phone:
   Settings → About Phone → tap "Build Number" 7 times.
4. Enable "USB Debugging" inside Developer Options.
5. Connect phone via USB → accept the "Allow USB Debugging" prompt.
6. Verify: open CMD and run: adb devices
   You should see your device listed.

WiFi ADB (optional, no USB after setup)
-----------------------------------------
1. Connect phone via USB first.
2. Run: adb tcpip 5555
3. Find phone IP: Settings → WiFi → tap connected network.
4. Run: adb connect <phone_ip>:5555
5. Unplug USB — WiFi ADB is now active.
"""

import subprocess
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Low-level ADB runner
# ─────────────────────────────────────────────

def _run_adb(args: list[str], timeout: float = 5.0) -> tuple[bool, str]:
    """
    Execute an adb command.

    args    : list of arguments after 'adb', e.g. ['shell', 'input', 'keyevent', '26']
    timeout : seconds before giving up

    Returns (success: bool, output: str)
    """
    cmd = ["adb"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout.strip() or result.stderr.strip()
        if result.returncode != 0:
            logger.warning(f"ADB non-zero exit: {' '.join(cmd)} → {output}")
            return False, output
        return True, output
    except FileNotFoundError:
        logger.error("'adb' not found. Add Android SDK Platform Tools to PATH.")
        return False, "adb not found"
    except subprocess.TimeoutExpired:
        logger.error(f"ADB command timed out: {' '.join(cmd)}")
        return False, "timeout"
    except Exception as e:
        logger.error(f"ADB error: {e}")
        return False, str(e)


# ─────────────────────────────────────────────
#  ADB key codes
# ─────────────────────────────────────────────

class KeyCode:
    """Android KeyEvent constants used most often."""
    HOME           = 3
    BACK           = 4
    VOLUME_UP      = 24
    VOLUME_DOWN    = 25
    POWER          = 26
    MEDIA_PLAY_PAUSE = 85
    MEDIA_NEXT     = 87
    MEDIA_PREVIOUS = 88
    MEDIA_STOP     = 86
    DPAD_UP        = 19
    DPAD_DOWN      = 20
    DPAD_LEFT      = 21
    DPAD_RIGHT     = 22


# ─────────────────────────────────────────────
#  Android controller
# ─────────────────────────────────────────────

class AndroidController:
    """
    High-level Android controller via ADB.

    Usage
    -----
    ctrl = AndroidController()
    if ctrl.is_connected():
        ctrl.play_pause()
        ctrl.open_youtube()
    """

    YOUTUBE_PACKAGE = "com.google.android.youtube"
    SCREEN_WIDTH    = 1080   # update to match your device
    SCREEN_HEIGHT   = 2400

    def __init__(self, device_ip: Optional[str] = None, port: int = 5555,
                 cooldown_sec: float = 1.0):
        """
        device_ip  : WiFi ADB target IP. None = USB connection.
        port       : ADB WiFi port (default 5555).
        cooldown_sec: minimum seconds between repeated actions.
        """
        self.device_ip    = device_ip
        self.port         = port
        self.cooldown_sec = cooldown_sec
        self._last_action_time = 0.0
        self._connected   = False

        if device_ip:
            self.connect_wifi(device_ip, port)
        else:
            self._connected = self.is_connected()

    # ── Connection management ─────────────────────────────────────────

    def connect_wifi(self, ip: str, port: int = 5555) -> bool:
        ok, out = _run_adb(["connect", f"{ip}:{port}"])
        if ok and "connected" in out.lower():
            self._connected = True
            logger.info(f"WiFi ADB connected to {ip}:{port}")
        else:
            logger.error(f"WiFi ADB failed: {out}")
        return self._connected

    def is_connected(self) -> bool:
        """Check whether at least one device is visible to adb."""
        ok, out = _run_adb(["devices"])
        # 'adb devices' lists header + one line per device
        lines = [l for l in out.splitlines() if l.strip() and "List of" not in l]
        self._connected = len(lines) > 0
        return self._connected

    def disconnect(self):
        if self.device_ip:
            _run_adb(["disconnect", f"{self.device_ip}:{self.port}"])
        self._connected = False

    # ── Internal helpers ──────────────────────────────────────────────

    def _cooldown_ok(self) -> bool:
        return (time.time() - self._last_action_time) >= self.cooldown_sec

    def _mark_action(self):
        self._last_action_time = time.time()

    def _keyevent(self, code: int) -> bool:
        if not self._connected:
            logger.warning("No device connected.")
            return False
        ok, _ = _run_adb(["shell", "input", "keyevent", str(code)])
        return ok

    def _swipe(self, x1, y1, x2, y2, duration_ms=300) -> bool:
        if not self._connected:
            return False
        ok, _ = _run_adb([
            "shell", "input", "swipe",
            str(x1), str(y1), str(x2), str(y2), str(duration_ms)
        ])
        return ok

    # ── Media actions ─────────────────────────────────────────────────

    def play_pause(self) -> bool:
        if not self._cooldown_ok():
            return False
        self._mark_action()
        return self._keyevent(KeyCode.MEDIA_PLAY_PAUSE)

    def next_track(self) -> bool:
        if not self._cooldown_ok():
            return False
        self._mark_action()
        return self._keyevent(KeyCode.MEDIA_NEXT)

    def prev_track(self) -> bool:
        if not self._cooldown_ok():
            return False
        self._mark_action()
        return self._keyevent(KeyCode.MEDIA_PREVIOUS)

    def volume_up(self) -> bool:
        if not self._cooldown_ok():
            return False
        self._mark_action()
        return self._keyevent(KeyCode.VOLUME_UP)

    def volume_down(self) -> bool:
        if not self._cooldown_ok():
            return False
        self._mark_action()
        return self._keyevent(KeyCode.VOLUME_DOWN)

    # ── Navigation swipes ─────────────────────────────────────────────

    def swipe_right(self) -> bool:
        """Swipe right on screen (e.g. go to previous page)."""
        if not self._cooldown_ok():
            return False
        self._mark_action()
        cx = self.SCREEN_WIDTH  // 2
        cy = self.SCREEN_HEIGHT // 2
        return self._swipe(cx - 200, cy, cx + 200, cy)

    def swipe_left(self) -> bool:
        """Swipe left on screen (e.g. go to next page)."""
        if not self._cooldown_ok():
            return False
        self._mark_action()
        cx = self.SCREEN_WIDTH  // 2
        cy = self.SCREEN_HEIGHT // 2
        return self._swipe(cx + 200, cy, cx - 200, cy)

    # ── App control ───────────────────────────────────────────────────

    def open_youtube(self) -> bool:
        """Launch YouTube app."""
        if not self._connected:
            return False
        ok, _ = _run_adb([
            "shell", "monkey", "-p", self.YOUTUBE_PACKAGE,
            "-c", "android.intent.category.LAUNCHER", "1"
        ])
        return ok

    def go_home(self) -> bool:
        return self._keyevent(KeyCode.HOME)

    def go_back(self) -> bool:
        return self._keyevent(KeyCode.BACK)

    def wake_screen(self) -> bool:
        """Wake device if screen is off."""
        return self._keyevent(KeyCode.POWER)

    # ── Gesture → ADB mapping ─────────────────────────────────────────

    def handle_gesture(self, gesture: str) -> Optional[str]:
        """
        Maps a gesture label to an ADB action.
        Returns description string on success, None otherwise.
        """
        dispatch = {
            "open_palm":   (self.play_pause,  "▶  Play / Pause"),
            "closed_fist": (self.play_pause,  "⏸  Play / Pause"),
            "swipe_right": (self.next_track,  "⏩ Next Track"),
            "swipe_left":  (self.prev_track,  "⏪ Prev Track"),
            "thumb_up":    (self.volume_up,   "🔊 Volume Up"),
            "thumb_down":  (self.volume_down, "🔈 Volume Down"),
        }

        if gesture not in dispatch:
            return None

        fn, desc = dispatch[gesture]
        ok = fn()
        if ok:
            logger.info(f"Android: {desc}")
            return desc
        return None


# ─────────────────────────────────────────────
#  Debugging helpers
# ─────────────────────────────────────────────

def diagnose():
    """
    Print a detailed connection report.
    Run this if your device is not showing up.
    """
    print("\n=== ADB Diagnostics ===")

    ok, out = _run_adb(["version"])
    if ok:
        print(f"✅ ADB found: {out.splitlines()[0]}")
    else:
        print("❌ ADB not found — add platform-tools to PATH")
        return

    ok, out = _run_adb(["devices", "-l"])
    print(f"\nDevices output:\n{out}")

    if "unauthorized" in out:
        print("\n⚠  Device shows 'unauthorized' — accept the prompt on your phone.")
    elif "offline" in out:
        print("\n⚠  Device offline — unplug/replug USB and rerun.")
    elif out.strip() == "List of devices attached":
        print("\n⚠  No devices found. Check cable, drivers, and USB Debugging setting.")
    else:
        print("\n✅ Device connected successfully.")

    print("=======================\n")


if __name__ == "__main__":
    diagnose()
