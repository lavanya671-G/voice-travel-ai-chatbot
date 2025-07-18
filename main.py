import speech_recognition as sr
import pyttsx3
import re
import json
import os
import time
from uuid import uuid4
from datetime import datetime
from flask import Flask, request, jsonify
from places import get_top_attractions
from weather import get_weather  # ✅ Real Weather API

# ---------------------------
# ✅ Flask App Initialization
# ---------------------------
app = Flask(__name__)

# ---------------------------
# ✅ Text-to-Speech Engine (CLI Only)
# ---------------------------
engine = pyttsx3.init()
engine.setProperty('rate', 150)
is_speaking = False  # ✅ Lock to prevent mic tap while speaking

DATABASE_FILE = "bookings.json"

# ---------------------------
# ✅ Database Functions
# ---------------------------
def init_db():
    if not os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'w') as f:
            json.dump({"bookings": []}, f)

def load_bookings():
    try:
        with open(DATABASE_FILE, 'r') as f:
            return json.load(f)["bookings"]
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_booking(booking):
    init_db()
    bookings = load_bookings()
    bookings.append(booking)
    with open(DATABASE_FILE, 'w') as f:
        json.dump({"bookings": bookings}, f, indent=2)
    return generate_confirmation(booking)

def generate_confirmation(booking):
    details = ""
    if booking['type'] == 'hotel':
        details = f"Hotel: {booking['hotel']} in {booking['city']}"
    elif booking['type'] == 'flight':
        details = f"Flight: {booking['airline']} to {booking['destination']}"

    return (
        f"✅ Booking confirmed!\n"
        f"Confirmation ID: {booking['id']}\n"
        f"Name: {booking['user']}\n"
        f"Type: {booking['type'].title()}\n"
        f"{details}\n"
        f"Date: {booking['date']}\n"
        "Thank you for choosing our service!"
    )

# ---------------------------
# ✅ Dummy Data (Replace later with real APIs)
# ---------------------------
def get_hotel_options(city):
    return [
        {"name": f"Grand {city} Hotel", "price": "$150/night", "rating": 4.5},
        {"name": f"{city} Plaza", "price": "$200/night", "rating": 4.2},
        {"name": f"Cozy {city} Inn", "price": "$120/night", "rating": 3.9}
    ]

def get_flight_options(destination):
    return [
        {"airline": "SkyHigh Airlines", "departure": "08:00 AM", "price": "$250"},
        {"airline": "Global Airways", "departure": "02:00 PM", "price": "$320"}
    ]

# ---------------------------
# ✅ Attractions with Fallback Fake Data
# ---------------------------
def get_fake_attractions(city):
    fake_data = {
        "paris": [
            "Eiffel Tower - Champ de Mars, Paris",
            "Louvre Museum - Rue de Rivoli, Paris",
            "Notre-Dame Cathedral - 6 Parvis Notre-Dame, Paris",
            "Arc de Triomphe - Place Charles de Gaulle, Paris",
            "Montmartre & Sacré-Cœur - 35 Rue du Chevalier, Paris"
        ],
        "default": [
            f"City Park - Central Square, {city}",
            f"Famous Museum - Downtown Street, {city}",
            f"Historic Monument - Old Town, {city}",
            f"Botanical Garden - Green Park, {city}",
            f"Popular Market - Main Market Street, {city}"
        ]
    }
    return fake_data.get(city.lower(), fake_data["default"])


def get_attractions(city):
    try:
        attractions = get_top_attractions(city)
    except Exception:
        attractions = []

    # ✅ Use fallback if empty
    if not attractions:
        attractions = get_fake_attractions(city)
        note = f"⚠️ No live data found for '{city}'. Showing popular places instead.\n\n"
    else:
        note = f"Top attractions in {city}:\n\n"

    formatted = "\n".join([f"{i+1}. {a}" for i, a in enumerate(attractions)])
    return note + formatted


# ---------------------------
# ✅ Utility Functions
# ---------------------------
ORDINAL_WORDS = {1: "first", 2: "second", 3: "third"}
NUMBER_WORDS = {
    "first": 1, "second": 2, "third": 3,
    "1st": 1, "2nd": 2, "3rd": 3,
    "1": 1, "2": 2, "3": 3
}
POSITIVE_WORDS = ["confirm", "confirmed", "yes", "book", "okay", "sure", "done"]
NEGATIVE_WORDS = ["cancel", "no", "exit", "quit", "goodbye"]

import threading

def speak_output(text):
    global is_speaking

    def _speak():
        global is_speaking
        is_speaking = True
        print(text)
        engine.say(text)
        engine.runAndWait()
        is_speaking = False

    threading.Thread(target=_speak, daemon=True).start()

def list_options(options_list, item_type, city):
    options_text = f"Here are the available {item_type} options in {city}:\n"
    for i, option in enumerate(options_list, 1):
        if item_type == "hotel":
            options_text += f"{ORDINAL_WORDS.get(i, str(i))}. {option['name']} - {option['price']} - Rating: {option['rating']}\n"
        elif item_type == "flight":
            options_text += f"{ORDINAL_WORDS.get(i, str(i))}. {option['airline']} - Departs at {option['departure']} for {option['price']}\n"
    options_text += f"Please say first through {ORDINAL_WORDS[len(options_list)]} or 'cancel'."
    return options_text.strip()

def extract_city(text):
    text = text.strip()
    match = re.search(r"(?:at|in|to)\s+([A-Za-z\s]+)", text, re.IGNORECASE)
    if match:
        city = match.group(1).strip()
    else:
        parts = text.split()
        city = parts[-1] if parts else text

    city = re.sub(
        r"\b(book|hotel|flight|a|the|with|to|at|in|on|for|weather|is|what)\b",
        "",
        city,
        flags=re.IGNORECASE,
    ).strip()

    city = re.sub(r"\s+", " ", city)
    return city.title()

def convert_to_number(word):
    clean_word = re.sub(r"[^\w]", "", word).lower().strip()
    return NUMBER_WORDS.get(clean_word, None)

# ---------------------------
# ✅ Booking Workflow Context
# ---------------------------
context = {
    "current_action": None,
    "current_city": None,
    "current_options": [],
    "selected_option": None,
    "awaiting_name": False
}

def proceed_with_booking(item_type, item_data, city, user_name="Guest"):
    booking = {
        "id": str(uuid4())[:8].upper(),
        "type": item_type,
        "user": user_name,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }
    if item_type == "hotel":
        booking.update({"hotel": item_data['name'], "city": city})
    elif item_type == "flight":
        booking.update({"airline": item_data['airline'], "destination": city})
    return save_booking(booking)

# ---------------------------
# ✅ Main Query Handler
# ---------------------------
def handle_user_query(text, is_voice=False):
    if not text:
        return "Please provide a query."

    normalized_text = text.lower().strip().strip(".!?,")
    city = extract_city(text)

    # ✅ Global Exit Handling
    if normalized_text in ["exit", "quit", "goodbye"]:
        context.update({
            "current_action": None,
            "current_city": None,
            "current_options": [],
            "selected_option": None,
            "awaiting_name": False
        })
        return "Goodbye! Exiting current task."

    # ✅ Reset context for new booking
    if any(word in normalized_text for word in ["book", "hotel", "flight"]):
        context.update({
            "current_action": None,
            "current_city": None,
            "current_options": [],
            "selected_option": None,
            "awaiting_name": False
        })

    # ✅ Weather Query with Error Handling
    if "weather" in normalized_text:
        if not city:
            return "Please specify a city for the weather update."
        try:
            return get_weather(city)
        except Exception:
            return f"⚠️ Unable to fetch weather for {city}. Please check your internet or try again later."

    # ✅ Attractions Query
    if "attractions" in normalized_text or "places" in normalized_text:
        if not city:
            return "Please specify a city to get attractions."
        return get_attractions(city)

    # ✅ Hotel Booking (Step 1)
    if "hotel" in normalized_text and not context["current_action"]:
        if not city:
            return "Please specify a city for the hotel booking."
        time.sleep(0.2)  # ✅ small human-like pause
        hotels = get_hotel_options(city)
        context.update({
            "current_action": "hotel",
            "current_city": city,
            "current_options": hotels,
            "selected_option": None,
            "awaiting_name": False
        })
        return list_options(hotels, "hotel", city)

    # ✅ Flight Booking (Step 1)
    if "flight" in normalized_text and not context["current_action"]:
        if not city:
            return "Please specify a destination city for the flight booking."
       # time.sleep(0.1)  # ✅ small human-like pause
        flights = get_flight_options(city)
        context.update({
            "current_action": "flight",
            "current_city": city,
            "current_options": flights,
            "selected_option": None,
            "awaiting_name": False
        })
        return list_options(flights, "flight", city)


    # ✅ Step 2: Selecting Option
    if context["current_action"] and context["current_options"] and not context["selected_option"]:
        choice_num = convert_to_number(normalized_text)

        if choice_num and 1 <= choice_num <= len(context["current_options"]):
            context["selected_option"] = context["current_options"][choice_num - 1]
            return f"Do you want to book this {context['current_action']}? Please say confirm or cancel."

        elif normalized_text in NEGATIVE_WORDS:
            context.update({"current_action": None, "current_options": [], "selected_option": None})
            return "Booking cancelled."

        return f"Please say first through {ORDINAL_WORDS[len(context['current_options'])]} or 'cancel'."

    # ✅ Step 3: Confirmation
    if context["selected_option"] and not context["awaiting_name"]:
        if normalized_text in POSITIVE_WORDS:
           # time.sleep(0.1)  # ✅ tiny pause feels natural
            context["awaiting_name"] = True
            return "Great! Please say your full name for the booking."

        elif normalized_text in NEGATIVE_WORDS:
            context.update({"current_action": None, "current_options": [], "selected_option": None})
            return "Booking cancelled."
        else:
            return "Please say confirm or cancel."

    # ✅ Step 4: Name & Final Booking
    if context["awaiting_name"] and context["selected_option"]:
        user_name = text.strip().title()
        booking = proceed_with_booking(
            context["current_action"],
            context["selected_option"],
            context["current_city"],
            user_name
        )
        context.update({
            "current_action": None,
            "current_city": None,
            "current_options": [],
            "selected_option": None,
            "awaiting_name": False
        })
        return booking

    return "Sorry, I didn't understand. Please try again."

# ---------------------------
# ✅ Flask Route
# ---------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "")
        response = handle_user_query(user_message, is_voice=True)
        return jsonify({"response": f"{response}"})
    except Exception as e:
        print(f"❌ Error in /chat route: {e}")
        return jsonify({"response": f"⚠️ Something went wrong: {e}"})

# ---------------------------
# ✅ Voice Input (CLI Only) - Optimized
# ---------------------------
def get_voice_input(prompt="Speak now..."):
    global is_speaking

    # ✅ Wait if assistant is still speaking (optimized CPU usage)
    while is_speaking:
     time.sleep(0.1)

    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print(prompt)
    speak_output(prompt)

    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.3)  # ✅ Faster response
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
        except sr.WaitTimeoutError:
            print("⚠️ Listening timeout.")
            return ""

    try:
        text = recognizer.recognize_google(audio)
        print(f"🗣️ You said: {text}")
        return text
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        return ""

# ---------------------------
# ✅ CLI Voice Mode
# ---------------------------
def cli_main():
    speak_output("Hello! I'm your voice travel assistant. How can I help you today?")
    first_prompt = True

    while True:
        spoken = get_voice_input(
            "You can ask about flights, hotels, weather, or attractions. Say 'exit' to quit."
            if first_prompt else "Speak now..."
        )
        first_prompt = False

        normalized_spoken = spoken.lower().strip().strip(".!?,")
        if normalized_spoken in ["exit", "quit", "goodbye"]:
            speak_output("Goodbye! Have a great trip!")
            break

        # ✅ Ignore empty or very short sounds (like mic accidentally touched)
        if not spoken or len(spoken.strip()) < 2:
            speak_output("I couldn't process your voice. Please try again.")
            continue

        response = handle_user_query(spoken, is_voice=True)
        print( response)
        speak_output(response)

# ---------------------------
# ✅ Run Either CLI or Flask
# ---------------------------
if __name__ == "__main__":
    mode = input("Enter mode (cli/flask): ").strip().lower()
    if mode == "cli":
        cli_main()
    else:
        app.run(debug=True, threaded=True)
