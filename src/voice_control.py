import speech_recognition as sr
import pyttsx3
import pyautogui
import pywhatkit
import webbrowser
import os
import time
import keyboard

engine = pyttsx3.init()
engine.setProperty('rate', 185)

recognizer = sr.Recognizer()
recognizer.energy_threshold = 250
#recognizer.pause_threshold = 0.4
recognizer.pause_threshold = 0.8
recognizer.non_speaking_duration = 0.5

def speak(text):
    print("Assistant:", text)
    engine.say(text)
    engine.runAndWait()

def listen():
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source, phrase_time_limit=5)

    try:
        command = recognizer.recognize_google(audio).lower()
        print("You:", command)
        return command

    except:
        return ""

speak("Advanced AI assistant started")

while True:

    command = listen()

    # ---------- OPEN APPS ----------

    if "open chrome" in command:
        os.system("start chrome")

    elif "open youtube" in command:
        webbrowser.open("https://youtube.com")

    elif "open google" in command:
        webbrowser.open("https://google.com")

    elif "open whatsapp" in command:
        webbrowser.open("https://web.whatsapp.com")

    elif "open vscode" in command:
        os.system("code")

    elif "open calculator" in command:
        os.system("calc")

    elif "open notepad" in command:
        os.system("notepad")

    # ---------- YOUTUBE ----------

    elif "play" in command:
        song = command.replace("play", "")
        speak(f"Playing {song}")
        pywhatkit.playonyt(song)

    # ---------- GOOGLE SEARCH ----------

    elif "search" in command:
        query = command.replace("search", "")
        speak(f"Searching {query}")
        pywhatkit.search(query)

    # ---------- TYPE ANYTHING ----------

    elif "type" in command:
        text = command.replace("type", "")
        pyautogui.write(text, interval=0.02)

    # ---------- WHATSAPP ----------

    elif "message" in command:
        speak("What should I type")
        msg = listen()

        pyautogui.write(msg)
        pyautogui.press("enter")

    # ---------- TABS ----------

    elif "new tab" in command:
        pyautogui.hotkey("ctrl", "t")

    elif "close tab" in command:
        pyautogui.hotkey("ctrl", "w")

    elif "next tab" in command:
        pyautogui.hotkey("ctrl", "tab")

    # ---------- SCROLL ----------

    elif "scroll down" in command:
        pyautogui.scroll(-1000)

    elif "scroll up" in command:
        pyautogui.scroll(1000)

    # ---------- MEDIA ----------

    elif "pause" in command:
        pyautogui.press("k")

    elif "forward" in command:
        pyautogui.press("right")

    elif "backward" in command:
        pyautogui.press("left")

    elif "volume up" in command:
        pyautogui.press("volumeup")

    elif "volume down" in command:
        pyautogui.press("volumedown")

    # ---------- STOP ----------

    elif "stop assistant" in command:
        speak("Goodbye")
        break