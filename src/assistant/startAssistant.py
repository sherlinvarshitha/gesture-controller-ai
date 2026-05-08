import cv2
import time
import threading

from src.gesture_detection import GestureDetector
from src.windows_control import WindowsController
from src.voice_control import listen_command

gesture_detector = GestureDetector()
windows = WindowsController()

latest_voice_command = ""


def voice_loop():
    global latest_voice_command

    while True:
        try:
            command = listen_command()

            if command:
                latest_voice_command = command.lower()

        except Exception as e:
            print("Voice Error:", e)

        time.sleep(0.3)


voice_thread = threading.Thread(target=voice_loop, daemon=True)
voice_thread.start()

cap = cv2.VideoCapture(0)

print("AI Assistant Started")

while True:

    ret, frame = cap.read()

    if not ret:
        break

    frame = cv2.flip(frame, 1)

    annotated, gesture, _ = gesture_detector.process(frame)

    # ---------------- GESTURE ----------------

    if gesture:
        windows.execute(gesture)

    # ---------------- VOICE ----------------

    if latest_voice_command:

        command = latest_voice_command
        latest_voice_command = ""

        if "open chrome" in command:
            windows.execute_voice_action("OPEN_CHROME")

        elif "open youtube" in command:
            windows.execute_voice_action("OPEN_YOUTUBE")

        elif "open google" in command:
            windows.execute_voice_action("OPEN_GOOGLE")

        elif "open whatsapp" in command:
            windows.execute_voice_action("OPEN_WHATSAPP")

        elif "volume up" in command:
            windows.execute_voice_action("VOLUME_UP")

        elif "volume down" in command:
            windows.execute_voice_action("VOLUME_DOWN")

        elif "type" in command:

            text = command.replace("type", "").strip()

            windows.execute_voice_action("TYPE_TEXT", text)

        elif "play" in command:

            song = command.replace("play", "").strip()

            windows.execute_voice_action("PLAY_YOUTUBE", song)

        elif "stop assistant" in command:
            break

    cv2.imshow("AI Gesture + Voice Assistant", annotated)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


cap.release()
cv2.destroyAllWindows()