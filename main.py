import speech_recognition as sr
import pyttsx3

# Function for voice input (speech-to-text)
def get_voice_input():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Speak now...")
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio)
        print(f"📝 You said: {text}")
        return text
    except sr.UnknownValueError:
        return "Sorry, I didn't understand that."
    except sr.RequestError:
        return "Speech service unavailable."

# Function for voice output (text-to-speech)
def speak_output(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

# Main logic
#if __name__ == "__main__":
    #user_text = get_voice_input()
    #speak_output(f"You said: {user_text}")
#---------------------------weather voice-----------------

import speech_recognition as sr
import pyttsx3
import re
from weather import get_weather

def speak_output(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def get_voice_input(prompt="Speak now..."):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print(f"🎤 {prompt}")
        speak_output(prompt)
        audio = recognizer.listen(source)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return None
    except sr.RequestError:
        return None

def extract_city(text):
    if not text:
        return None
    text = text.lower()
    match = re.search(r"in\s+([a-zA-Z\s]+)", text)
    if match:
        city = match.group(1).strip()
        city = re.sub(r"\b(today|now|please|tomorrow)\b", "", city).strip()
        return city.title() if city else None
    elif text.strip().isalpha():
        return text.strip().title()
    return None

if __name__ == "__main__":
    #  Ask only ONCE here
    spoken = get_voice_input("Speak now...")

    attempts = 1
    MAX_ATTEMPTS = 2
    city = extract_city(spoken)

    while not city and attempts < MAX_ATTEMPTS:
        print("❌ Could not detect any city name.")
        speak_output("I couldn't detect the city. Please say the city name again.")
        spoken = get_voice_input("Say the city name again")
        city = extract_city(spoken)
        attempts += 1

    if not city:
       # print(" Switching to manual input...")
        speak_output("Please type the city name.")
        city = input("Enter city name: ")

    if city:
        print(f" Using city: {city}")
        weather_report = get_weather(city)
        print("📢", weather_report)
        speak_output(weather_report)
    else:
        print("❌ No city provided. Exiting.")
        speak_output("No city provided. Exiting now.")




