# 🖐 AI-Based Gesture-Controlled Video & Smartphone Controller

> Control your PC and Android phone using **hand gestures only** — no touch required.  
> Built with MediaPipe, OpenCV, PyQt5, and Python.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![OpenCV](https://img.shields.io/badge/OpenCV-4.9-green?logo=opencv)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10-orange)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15-purple)
![License](https://img.shields.io/badge/License-MIT-brightgreen)

---

## 📸 Screenshots

| Live Camera Feed | Gesture Detection | Dark UI |
|---|---|---|
| *(add screenshot here)* | *(add screenshot here)* | *(add screenshot here)* |

---

## ✨ Features

- 🤚 **Real-time hand tracking** using MediaPipe (21 landmarks, <80ms latency)
- 🧠 **6 gesture classes** — open palm, fist, swipe left/right, thumb up/down
- 🖥️ **Windows control** — media keys, volume, arrow navigation via PyAutoGUI
- 📱 **Android control** — play/pause, volume, YouTube, swipes via ADB
- 🎨 **Professional dark-theme UI** built with PyQt5
- 🔒 **False-detection guard** — cooldown + confirmation frame logic
- 📦 **Exportable to .exe** via PyInstaller

---

## 🖐 Gesture Map

| Gesture | Windows Action | Android Action |
|---|---|---|
| ✋ Open Palm | ▶ Play / Pause (Space) | ▶ Play / Pause |
| ✊ Closed Fist | ⏸ Play / Pause (Space) | ⏸ Play / Pause |
| 👉 Swipe Right | ⏩ Forward (→ key) | ⏭ Next track |
| 👈 Swipe Left | ⏪ Backward (← key) | ⏮ Prev track |
| 👍 Thumb Up | 🔊 Volume Up | 🔊 Volume Up |
| 👎 Thumb Down | 🔈 Volume Down | 🔈 Volume Down |

---

## 📁 Project Structure

```
gesture-controller/
│
├── src/
│   ├── gesture_detection.py   # MediaPipe hand tracking + gesture rules
│   ├── windows_control.py     # PyAutoGUI + pycaw OS control
│   ├── android_control.py     # ADB commands for Android
│   └── ui_app.py              # PyQt5 dark-theme desktop UI
│
├── scripts/
│   ├── collect_dataset.py     # Optional: record images for CNN training
│   └── train_model.py         # Optional: train custom CNN
│
├── data/                      # Raw gesture images (gitignored)
├── model/                     # Trained model files (gitignored)
├── main.py                    # ← Run this to launch the app
├── requirements.txt
└── README.md
```

---

## 🚀 Installation & Running

### Step 1 — Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/gesture-controller.git
cd gesture-controller
```

### Step 2 — Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Run the app
```bash
# Full GUI (recommended)
python main.py

# Terminal / headless mode
python main.py --nogui
```

---

## 📱 Android ADB Setup

1. Download [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools)
2. Extract and add to your system **PATH**
3. On your phone: **Settings → About Phone → tap Build Number 7 times**
4. Go to **Developer Options → enable USB Debugging**
5. Connect phone via USB → accept the prompt on your phone
6. Verify: `adb devices` — your device should appear
7. In the app: click **Connect Android (USB)**

**WiFi ADB (no cable after setup):**
```bash
adb tcpip 5555
adb connect <your_phone_ip>:5555
```

---

## 📦 Build .exe (Windows)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name GestureController main.py
# Output: dist/GestureController.exe
```

---

## 🛠 Common Errors & Fixes

| Error | Fix |
|---|---|
| `ModuleNotFoundError: mediapipe` | Run `pip install mediapipe` |
| `Cannot open webcam` | Check camera permissions / try index `1` in `cv2.VideoCapture(1)` |
| `adb not found` | Add Android SDK Platform Tools folder to PATH |
| `Device unauthorized` | Accept USB Debugging prompt on your phone |
| `PyQt5 import error` | Run `pip install PyQt5` |
| `pycaw` not working | Volume uses keyboard fallback — works without pycaw |

---

## 🔮 Future Improvements

- [ ] Custom CNN model for improved accuracy in low light
- [ ] Two-hand gesture support
- [ ] Voice + gesture combined commands
- [ ] iOS support via alternative automation
- [ ] Gesture recording & custom mapping UI
- [ ] Web dashboard via Flask/FastAPI

---

## 🤝 Contributing

Pull requests are welcome! Please open an issue first to discuss major changes.

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 👨‍💻 Author

Built with ❤️ using Python, MediaPipe, OpenCV, and PyQt5.
