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
from weather import get_weather
from typing import Dict, List, Optional, Union

app = Flask(__name__)

# Text-to-Speech Engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)
is_speaking = False

DATABASE_FILE = "bookings.json"

# Constants
ORDINAL_WORDS = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}
NUMBER_WORDS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
    "number one": 1, "number two": 2, "number three": 3,
    "option one": 1, "option two": 2, "option three": 3
}

# UPDATED: Expanded confirmation vocabulary
POSITIVE_WORDS = {"confirm", "confirmed", "yes", "book", "okay", "sure", "done", "proceed", 
                 "yep", "yeah", "y", "ok", "absolutely", "aye", "roger", "positive"}
NEGATIVE_WORDS = {"cancel", "no", "exit", "quit", "goodbye", "stop", 
                 "nope", "nah", "negative", "n", "stop", "abort"}

# Database Functions
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

# Dummy Data
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

# Attractions with Fallback
def get_fake_attractions(city):
    fake_data = {
        "hyderabad": [
            "Charminar - Old City, Hyderabad",
            "Golconda Fort - Ibrahim Bagh, Hyderabad",
            "Ramoji Film City - Anaspur Village",
            "Hussain Sagar Lake - Tank Bund Road",
            "Salar Jung Museum - Darulshifa"
        ],
        "delhi": [
            "Red Fort - Netaji Subhash Marg",
            "India Gate - Rajpath",
            "Qutub Minar - Mehrauli",
            "Lotus Temple - Kalkaji",
            "Akshardham Temple - Noida Mor"
        ],
        "mumbai": [
            "Gateway of India - Apollo Bandar",
            "Marine Drive - Netaji Subhash Chandra Bose Road",
            "Elephanta Caves - Gharapuri Island",
            "Chhatrapati Shivaji Terminus - Fort Area",
            "Juhu Beach - Juhu Tara Road"
        ],
        "chennai": [
            "Marina Beach - Kamarajar Salai",
            "Kapaleeshwarar Temple - Mylapore",
            "Fort St. George - Rajaji Salai",
            "Valluvar Kottam - Nungambakkam",
            "Guindy National Park - Sardar Patel Road"
        ],
        "bangalore": [
            "Lalbagh Botanical Garden - Mavalli",
            "Bangalore Palace - Vasanth Nagar",
            "Cubbon Park - Kasturba Road",
            "Tipu Sultan's Summer Palace - Chamrajpet",
            "ISKCON Temple - Rajajinagar"
        ],
        "goa": [
            "Calangute Beach - North Goa",
            "Fort Aguada - Sinquerim",
            "Basilica of Bom Jesus - Old Goa",
            "Dudhsagar Falls - Sonaulim",
            "Anjuna Flea Market - Anjuna"
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

    if not attractions:
        attractions = get_fake_attractions(city)
        note = f"Top attractions in {city}:\n\n"
    else:
        note = f"Top attractions in {city}:\n\n"

    formatted = "\n".join([f"{i+1}. {a}" for i, a in enumerate(attractions)])
    return note + formatted

# Utility Functions
def clean_text(text):
    """Clean text by removing punctuation and extra spaces"""
    return re.sub(r'[^\w\s]', '', text).strip()

def extract_city(text):
    """Robust city extraction from user input"""
    cleaned_text = clean_text(text).lower()
    
    # If the input is just a city name, return it directly
    if len(cleaned_text.split()) == 1:
        return cleaned_text.title()
    
    # Direct patterns for city extraction
    patterns = [
        r"hotel\s+(?:in|at)\s+([\w\s]+)",
        r"flight\s+(?:to|in)\s+([\w\s]+)",
        r"weather\s+(?:in|at)\s+([\w\s]+)",
        r"attractions\s+(?:in|at)\s+([\w\s]+)",
        r"places\s+(?:in|at)\s+([\w\s]+)",
        r"route\s+from\s+[\w\s]+\s+to\s+([\w\s]+)",
        r"book\s+(?:hotel|flight)\s+(?:in|to)\s+([\w\s]+)",
        r"help\s+me\s+to\s+book\s+(?:hotel|flight)\s+(?:in|at|to)\s+([\w\s]+)",
        r"hotels?\s+in\s+([\w\s]+)",
        r"flights?\s+to\s+([\w\s]+)",
        r"weather\s+in\s+([\w\s]+)",
        r"attractions?\s+in\s+([\w\s]+)",
        r"places?\s+in\s+([\w\s]+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cleaned_text)
        if match:
            city = match.group(1).strip().title()
            if city:
                return city
    
    # Fallback: last word as city
    words = cleaned_text.split()
    if words:
        return words[-1].title()
    
    return ""

# Common city corrections
def correct_city_name(city):
    corrections = {
        "del": "Delhi",
        "hyd": "Hyderabad",
        "chen": "Chennai",
        "mum": "Mumbai",
        "beng": "Bangalore",
        "bom": "Mumbai",
        "blr": "Bangalore",
        "chn": "Chennai",
        "new": "New Delhi",
        "delhi": "Delhi",
        "hyderabad": "Hyderabad",
        "mumbai": "Mumbai",
        "chennai": "Chennai",
        "bangalore": "Bangalore",
        "kolkata": "Kolkata",
        "pune": "Pune",
        "goa": "Goa"
    }
    return corrections.get(city.lower(), city)

# Booking Context
context = {
    "current_action": None,
    "current_city": None,
    "current_options": [],
    "selected_option": None,
    "awaiting_name": False,
    "awaiting_city": False
}

def reset_context():
    global context
    context = {
        "current_action": None,
        "current_city": None,
        "current_options": [],
        "selected_option": None,
        "awaiting_name": False,
        "awaiting_city": False
    }

def list_options(options_list, item_type, city):
    """Fixed to use clean city name"""
    city = correct_city_name(clean_text(city))
    options_text = f"Here are the available {item_type} options in {city}:\n"
    for i, option in enumerate(options_list, 1):
        if item_type == "hotel":
            options_text += f"{i}. {option['name']} - {option['price']} - Rating: {option['rating']}\n"
        elif item_type == "flight":
            options_text += f"{i}. {option['airline']} - Departs at {option['departure']} for {option['price']}\n"
    options_text += f"Please say the number (1-{len(options_list)}) or 'cancel'."
    return options_text.strip()

def proceed_with_booking(item_type, item_data, city, user_name="Guest"):
    booking = {
        "id": str(uuid4())[:8].upper(),
        "type": item_type,
        "user": user_name,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }
    if item_type == "hotel":
        booking.update({"hotel": item_data['name'], "city": correct_city_name(clean_text(city))})
    elif item_type == "flight":
        booking.update({"airline": item_data['airline'], "destination": correct_city_name(clean_text(city))})
    return save_booking(booking)

def convert_to_number(word):
    """Improved number conversion with better pattern matching"""
    # Clean and normalize the input
    clean_word = re.sub(r'[^\w\s]', '', word).lower().strip()
    
    # Try direct number conversion
    if clean_word.isdigit():
        return int(clean_word)
    
    # Try word to number mapping
    if clean_word in NUMBER_WORDS:
        return NUMBER_WORDS[clean_word]
    
    # Try to extract number from phrases
    patterns = [
        r"option\s*(\d+)",
        r"number\s*(\d+)",
        r"^(\d+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, clean_word)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    
    return None

# Main Query Handler
def handle_user_query(text, is_voice=False):
    if not text:
        return "Please provide a query."
    
    # Clean input text
    cleaned_text = clean_text(text)
    normalized_text = cleaned_text.lower().strip()
    
    # Global Exit Handling
    if normalized_text in NEGATIVE_WORDS:
        reset_context()
        return "Goodbye! Exiting current task."

    # Handle city input when we're expecting it
    if context["awaiting_city"]:
        city = cleaned_text.title()
        if not city:
            return "Please specify a city name."
            
        city = correct_city_name(city)
        context["current_city"] = city
        context["awaiting_city"] = False
        
        if context["current_action"] == "hotel":
            hotels = get_hotel_options(city)
            context["current_options"] = hotels
            return list_options(hotels, "hotel", city)
        elif context["current_action"] == "flight":
            flights = get_flight_options(city)
            context["current_options"] = flights
            return list_options(flights, "flight", city)
        elif context["current_action"] == "weather":
            try:
                return get_weather(city)
            except Exception:
                return f"⚠️ Unable to fetch weather for {city}. Please try again later."
        elif context["current_action"] in ["attractions", "places"]:
            return get_attractions(city)

    # Handle single-word commands
    if len(cleaned_text.split()) == 1:
        word = cleaned_text.lower()
        if word == "hotel":
            context.update({
                "current_action": "hotel",
                "awaiting_city": True
            })
            return "Please specify a city for hotel booking. Example: 'Delhi'"
        elif word == "flight":
            context.update({
                "current_action": "flight",
                "awaiting_city": True
            })
            return "Please specify a destination city for flight booking. Example: 'Mumbai'"
        elif word == "weather":
            context.update({
                "current_action": "weather",
                "awaiting_city": True
            })
            return "Please specify a city for weather information. Example: 'Bangalore'"
        elif word in ("attractions", "places"):
            context.update({
                "current_action": "attractions",
                "awaiting_city": True
            })
            return "Please specify a city to get attractions. Example: 'Delhi'"
        elif word == "route":
            return "Please specify a route. Example: 'Route from Delhi to Hyderabad'"

    # Extract city from full commands
    city = extract_city(cleaned_text)
    if city:
        city = correct_city_name(city)

    # Weather Query
    if "weather" in normalized_text:
        if not city:
            context.update({
                "current_action": "weather",
                "awaiting_city": True
            })
            return "Please specify a city for the weather update."
        try:
            return get_weather(city)
        except Exception:
            return f"⚠️ Unable to fetch weather for {city}. Please try again later."

    # Attractions Query
    if "attractions" in normalized_text or "places" in normalized_text:
        if not city:
            context.update({
                "current_action": "attractions",
                "awaiting_city": True
            })
            return "Please specify a city to get attractions."
        return get_attractions(city)

    # Hotel Booking
    if "hotel" in normalized_text and not context["current_action"]:
        if not city:
            context.update({
                "current_action": "hotel",
                "awaiting_city": True
            })
            return "Please specify a city for the hotel booking."
        hotels = get_hotel_options(city)
        context.update({
            "current_action": "hotel",
            "current_city": city,
            "current_options": hotels,
            "selected_option": None,
            "awaiting_name": False
        })
        return list_options(hotels, "hotel", city)

    # Flight Booking
    if "flight" in normalized_text and not context["current_action"]:
        if not city:
            context.update({
                "current_action": "flight",
                "awaiting_city": True
            })
            return "Please specify a destination city for the flight booking."
        flights = get_flight_options(city)
        context.update({
            "current_action": "flight",
            "current_city": city,
            "current_options": flights,
            "selected_option": None,
            "awaiting_name": False
        })
        return list_options(flights, "flight", city)

    # Step 2: Selecting Option
    if context["current_action"] and context["current_options"] and not context["selected_option"]:
        choice_num = convert_to_number(normalized_text)
        
        # Debug output to help identify recognition issues
        print(f"User input: '{text}' → Cleaned: '{cleaned_text}' → Choice number: {choice_num}")

        if choice_num and 1 <= choice_num <= len(context["current_options"]):
            context["selected_option"] = context["current_options"][choice_num - 1]
            # UPDATED: More natural confirmation prompt
            return f"Do you want to book this {context['current_action']}? Please say 'yes' or 'no'."

        elif normalized_text in NEGATIVE_WORDS:
            reset_context()
            return "Booking cancelled."

        return f"Please say a number from 1 to {len(context['current_options'])} or 'cancel'."

    # Step 3: Confirmation
    if context["selected_option"] and not context["awaiting_name"]:
        # UPDATED: Extract first word and check against expanded vocabulary
        words = normalized_text.split()
        first_word = words[0] if words else ""
        
        if first_word in POSITIVE_WORDS:
            context["awaiting_name"] = True
            return "Great! Please say your full name for the booking."

        elif first_word in NEGATIVE_WORDS:
            reset_context()
            return "Booking cancelled."
        else:
            # UPDATED: More helpful prompt
            return "Please say 'yes' to confirm or 'no' to cancel."

    # Step 4: Name & Final Booking
    if context["awaiting_name"] and context["selected_option"]:
        user_name = cleaned_text.title()
        booking = proceed_with_booking(
            context["current_action"],
            context["selected_option"],
            context["current_city"],
            user_name
        )
        reset_context()
        return booking

    return "Sorry, I didn't understand. Please try again."

# Flask Route
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "")
        print(f"Received message: {user_message}")
        response = handle_user_query(user_message, is_voice=True)
        print(f"Sending response: {response}")
        return jsonify({"response": f"{response}"})
    except Exception as e:
        print(f"❌ Error in /chat route: {e}")
        return jsonify({"response": "Sorry, something went wrong. Please try again."})

if __name__ == "__main__":
    app.run(debug=True, threaded=True)