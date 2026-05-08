"""
ui_app.py
---------
Professional dark-theme desktop UI for the Gesture Controller.
Built with PyQt5.

Layout:
  Left  → Live webcam feed with skeleton overlay
  Right → Controls: Start/Stop, Mode toggle, Gesture display, Status panel
"""

import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QFrame,
    QSizePolicy, QGroupBox  


)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor, QPalette

# Our modules
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from gesture_detection import GestureDetector, FRIENDLY_NAMES

# Try importing controllers (gracefully degrade if deps missing)
try:
    #from windows_control import WindowsController
    from src.windows_control import WindowsController
    WIN_CTRL_OK = True
except Exception:
    WIN_CTRL_OK = False

try:
    from android_control import AndroidController
    ADB_CTRL_OK = True
except Exception:
    ADB_CTRL_OK = False


# ─────────────────────────────────────────────
#  Dark palette
# ─────────────────────────────────────────────
DARK_BG   = "#1A1A2E"
PANEL_BG  = "#16213E"
CARD_BG   = "#0F3460"
ACCENT    = "#00D4AA"
ACCENT2   = "#E94560"
TEXT      = "#E0E0E0"
MUTED     = "#7A7A9D"
BTN_GREEN = "#00B894"
BTN_RED   = "#E74C3C"


STYLE = f"""
QMainWindow, QWidget {{
    background-color: {DARK_BG};
    color: {TEXT};
    font-family: 'Segoe UI', Arial;
}}
QGroupBox {{
    border: 1px solid {CARD_BG};
    border-radius: 8px;
    margin-top: 12px;
    padding: 10px;
    font-size: 11px;
    color: {MUTED};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {ACCENT};
    font-weight: bold;
    font-size: 11px;
    letter-spacing: 1px;
}}
QPushButton {{
    background-color: {CARD_BG};
    color: {TEXT};
    border: 1px solid {MUTED};
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: bold;
}}
QPushButton:hover {{ background-color: #1a4a7a; border-color: {ACCENT}; }}
QPushButton:pressed {{ background-color: {ACCENT}; color: #000; }}
QPushButton:disabled {{ color: {MUTED}; border-color: #333; }}
QLabel {{ color: {TEXT}; background: transparent; }}
QFrame {{ background: transparent; }}
"""


# ─────────────────────────────────────────────
#  Camera thread (runs in background)
# ─────────────────────────────────────────────

class CameraThread(QThread):
    frame_ready   = pyqtSignal(np.ndarray, object)   # annotated frame, gesture
    error_signal  = pyqtSignal(str)

    def __init__(self, cooldown=1.5):
        super().__init__()
        self._running  = False
        self._detector = None
        self._cooldown = cooldown

    def run(self):
        self._detector = GestureDetector(cooldown_sec=self._cooldown)
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            self.error_signal.emit("Cannot open webcam. Check camera connection.")
            return

        self._running = True
        while self._running:
            ret, frame = cap.read()
            if not ret:
                self.error_signal.emit("Frame read failed.")
                break

            frame = cv2.flip(frame, 1)
            annotated, gesture, _ = self._detector.process(frame)
            self.frame_ready.emit(annotated, gesture)

        cap.release()
        if self._detector:
            self._detector.release()

    def stop(self):
        self._running = False
        self.wait()


# ─────────────────────────────────────────────
#  Main window
# ─────────────────────────────────────────────
print("WIN_CTRL_OK =", WIN_CTRL_OK)
class GestureControllerUI(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🖐  Gesture Controller")
        self.setMinimumSize(1100, 680)

        # State
        self._camera_thread  = None
        #self._win_ctrl       = WindowsController() if WIN_CTRL_OK else None
        self._win_ctrl = None
        if WIN_CTRL_OK:
            try:
                self._win_ctrl = WindowsController()
            except Exception as e:
                print("WindowsController init error:", e)
                self._win_ctrl = None
            self._adb_ctrl       = None
            self._mode           = "windows"   # "windows" | "android"
            self._last_action    = "—"

            self._build_ui()
            self.setStyleSheet(STYLE)

    # ── UI construction ────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # ── Left: video panel ──
        video_box = QGroupBox("LIVE CAMERA FEED")
        v_layout  = QVBoxLayout(video_box)
        self.video_label = QLabel("Camera not started")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet(
            f"background: {PANEL_BG}; border-radius: 8px; color: {MUTED}; font-size:14px;"
        )
        v_layout.addWidget(self.video_label)
        root.addWidget(video_box, stretch=3)

        # ── Right: control panel ──
        ctrl_panel = QWidget()
        ctrl_panel.setMaximumWidth(340)
        c_layout   = QVBoxLayout(ctrl_panel)
        c_layout.setSpacing(12)

        # Title
        title = QLabel("🖐  Gesture Controller")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {ACCENT}; margin-bottom: 4px;")
        c_layout.addWidget(title)

        sub = QLabel("Real-time hand gesture recognition")
        sub.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        c_layout.addWidget(sub)

        c_layout.addSpacing(8)

        # ── Camera controls ──
        cam_box = QGroupBox("CAMERA")
        cam_layout = QHBoxLayout(cam_box)
        self.start_btn = QPushButton("▶  Start")
        self.stop_btn  = QPushButton("⏹  Stop")
        self.stop_btn.setEnabled(False)
        self.start_btn.setStyleSheet(f"background: {BTN_GREEN}; color: #fff; border: none;")
        self.stop_btn.setStyleSheet( f"background: {BTN_RED};   color: #fff; border: none;")
        self.start_btn.clicked.connect(self._start_camera)
        self.stop_btn.clicked.connect(self._stop_camera)
        cam_layout.addWidget(self.start_btn)
        cam_layout.addWidget(self.stop_btn)
        c_layout.addWidget(cam_box)

        # ── Gesture display ──
        gest_box = QGroupBox("DETECTED GESTURE")
        gest_layout = QVBoxLayout(gest_box)
        self.gesture_label = QLabel("—  No Gesture")
        self.gesture_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.gesture_label.setAlignment(Qt.AlignCenter)
        self.gesture_label.setStyleSheet(
            f"color: {ACCENT}; background: {PANEL_BG}; border-radius: 8px; padding: 18px;"
        )
        gest_layout.addWidget(self.gesture_label)
        c_layout.addWidget(gest_box)

        # ── Last action ──
        action_box = QGroupBox("LAST ACTION FIRED")
        action_layout = QVBoxLayout(action_box)
        self.action_label = QLabel("—")
        self.action_label.setFont(QFont("Segoe UI", 13))
        self.action_label.setAlignment(Qt.AlignCenter)
        self.action_label.setStyleSheet(
            f"color: {TEXT}; background: {PANEL_BG}; border-radius: 8px; padding: 12px;"
        )
        action_layout.addWidget(self.action_label)
        c_layout.addWidget(action_box)

        # ── Mode toggle ──
        mode_box = QGroupBox("CONTROL MODE")
        mode_layout = QHBoxLayout(mode_box)
        self.win_btn = QPushButton("🖥  Windows")
        self.adb_btn = QPushButton("📱 Android")
        self.win_btn.clicked.connect(lambda: self._set_mode("windows"))
        self.adb_btn.clicked.connect(lambda: self._set_mode("android"))
        self._highlight_mode_btn()
        mode_layout.addWidget(self.win_btn)
        mode_layout.addWidget(self.adb_btn)
        c_layout.addWidget(mode_box)

        # ── Status panel ──
        status_box = QGroupBox("STATUS")
        status_layout = QVBoxLayout(status_box)

        self.cam_status  = self._status_row("Camera",  "Stopped",  False)
        self.win_status  = self._status_row("Windows", "Ready" if WIN_CTRL_OK else "Unavailable", WIN_CTRL_OK)
        self.adb_status  = self._status_row("Android ADB", "Not connected", False)

        for row in [self.cam_status, self.win_status, self.adb_status]:
            status_layout.addWidget(row["widget"])

        # ADB connect button
        self.adb_connect_btn = QPushButton("🔌  Connect Android (USB)")
        self.adb_connect_btn.clicked.connect(self._connect_android)
        status_layout.addWidget(self.adb_connect_btn)
        c_layout.addWidget(status_box)

        c_layout.addStretch()

        # Footer
        footer = QLabel("MediaPipe · OpenCV · PyQt5")
        footer.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        footer.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(footer)

        root.addWidget(ctrl_panel, stretch=1)

    def _status_row(self, name, value, ok):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {'#00D4AA' if ok else '#E94560'}; font-size: 14px;")

        lbl_name  = QLabel(name)
        lbl_name.setStyleSheet(f"color: {MUTED}; font-size: 12px;")

        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(f"color: {TEXT}; font-size: 12px; font-weight: bold;")
        lbl_value.setAlignment(Qt.AlignRight)

        layout.addWidget(dot)
        layout.addWidget(lbl_name)
        layout.addStretch()
        layout.addWidget(lbl_value)

        return {"widget": widget, "dot": dot, "value": lbl_value}

    def _update_status_row(self, row, value, ok):
        row["dot"].setStyleSheet(f"color: {'#00D4AA' if ok else '#E94560'}; font-size: 14px;")
        row["value"].setText(value)

    # ── Camera control ─────────────────────────────────────────────────

    def _start_camera(self):
        self._camera_thread = CameraThread(cooldown=1.5)
        self._camera_thread.frame_ready.connect(self._on_frame)
        self._camera_thread.error_signal.connect(self._on_error)
        self._camera_thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._update_status_row(self.cam_status, "Running", True)

    def _stop_camera(self):
        if self._camera_thread:
            self._camera_thread.stop()
            self._camera_thread = None

        self.video_label.setText("Camera not started")
        self.video_label.setPixmap(QPixmap())
        self.gesture_label.setText("—  No Gesture")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._update_status_row(self.cam_status, "Stopped", False)

    # ── Frame handler ──────────────────────────────────────────────────
    
    def _on_frame(self, frame: np.ndarray, gesture):
        print("GESTURE RAW:", gesture)
        # Convert frame to QPixmap and display
        h, w, ch = frame.shape
        rgb       = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qimg      = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap    = QPixmap.fromImage(qimg).scaled(
            self.video_label.width(), self.video_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pixmap)

        # Update gesture label
        if gesture:
            friendly = FRIENDLY_NAMES.get(gesture, gesture)
            self.gesture_label.setText(friendly)
            self._dispatch_gesture(gesture)
        else:
            self.gesture_label.setText("—  No Gesture")

    def _dispatch_gesture(self, gesture: str):
        action = None
        if self._mode == "windows" and self._win_ctrl:
            action = self._win_ctrl.execute(gesture)
        elif self._mode == "android" and self._adb_ctrl:
            action = self._adb_ctrl.handle_gesture(gesture)

        if action:
            print("ACTION:", action)
            self.action_label.setText(action)

    # ── Mode toggle ────────────────────────────────────────────────────

    def _set_mode(self, mode: str):
        self._mode = mode
        self._highlight_mode_btn()

    def _highlight_mode_btn(self):
        active   = f"background: {ACCENT}; color: #000; border: none; font-weight: bold;"
        inactive = f"background: {CARD_BG}; color: {TEXT};"
        if self._mode == "windows":
            self.win_btn.setStyleSheet(active)
            self.adb_btn.setStyleSheet(inactive)
        else:
            self.adb_btn.setStyleSheet(active)
            self.win_btn.setStyleSheet(inactive)

    # ── Android connect ────────────────────────────────────────────────

    def _connect_android(self):
        if not ADB_CTRL_OK:
            self._update_status_row(self.adb_status, "adb module error", False)
            return
        self._adb_ctrl = AndroidController()
        if self._adb_ctrl.is_connected():
            self._update_status_row(self.adb_status, "Connected ✅", True)
            self._set_mode("android")
        else:
            self._update_status_row(self.adb_status, "Not found ❌", False)

    # ── Error handler ──────────────────────────────────────────────────

    def _on_error(self, msg: str):
        self.gesture_label.setText(f"⚠ {msg}")
        self._stop_camera()

    # ── Cleanup on close ───────────────────────────────────────────────

    def closeEvent(self, event):
        self._stop_camera()
        if self._adb_ctrl:
            self._adb_ctrl.disconnect()
        event.accept()


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

def run_app():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = GestureControllerUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_app()
