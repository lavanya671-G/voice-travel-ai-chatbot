import speech_recognition as sr
import pyttsx3
import re
from uuid import uuid4
from weather import get_weather
from booking_system import save_booking, load_bookings
from places import get_top_attractions

engine = pyttsx3.init()

# Shared memory to persist context like last city mentioned
context = {
    "last_city": None
}

def speak_output(text):
    engine.say(text)
    engine.runAndWait()

def get_voice_input(prompt="Speak now...", max_attempts=2):
    recognizer = sr.Recognizer()
    for attempt in range(max_attempts):
        with sr.Microphone() as source:
            print(f"🎤 {prompt} (Attempt {attempt + 1} of {max_attempts})")
            speak_output(prompt)
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                return recognizer.recognize_google(audio)
            except sr.WaitTimeoutError:
                speak_output("Listening timed out.")
            except sr.UnknownValueError:
                speak_output("Sorry, I didn't catch that.")
            except sr.RequestError:
                speak_output("Speech service error.")
    speak_output("Voice not detected. Please type your response.")
    return input("Enter manually: ").strip()

def extract_city(text):
    if not text:
        return None
    text = text.lower()

    # Try common pattern like "weather at Hyderabad"
    text = text.lower()

# Match after "in", "at", "to", etc.
    match = re.search(r"(?:in|at|to|from|for)\s+([a-zA-Z\s]+)", text)
    if match:
        city = match.group(1)
    else:
        # fallback to finding last word
        words = text.split()
        city = words[-1] if words else None

    if city:
        # Remove common filler words
        city = re.sub(r"\b(?:is|what|the|weather|please|now|today|tomorrow|at|in|on|to|from|for|of)\b", "", city)
        city = re.sub(r"[^a-zA-Z\s]", "", city)
        city = city.strip()
        return city.title() if city else None

    return None


def get_hotel_options(city):
    return [
        {"name": f"Grand {city} Hotel", "price": "$150/night", "rating": 4.5},
        {"name": f"{city} Plaza", "price": "$200/night", "rating": 4.2},
        {"name": f"Cozy {city} Inn", "price": "$120/night", "rating": 3.9},
    ]

def get_flight_options(destination):
    return [
        {"airline": "SkyHigh Airlines", "flight_number": f"SH{100 + abs(hash(destination)) % 900}", "departure": "08:00 AM", "arrival": "11:00 AM", "price": "$250"},
        {"airline": "Global Airways", "flight_number": f"GA{200 + abs(hash(destination)) % 800}", "departure": "02:00 PM", "arrival": "06:30 PM", "price": "$320"},
    ]

def ask_for_booking(item_type, item_data, city):
    speak_output(f"Do you want to book this {item_type}? Say yes or no.")
    response = get_voice_input("Say yes to confirm booking.")
    if "yes" in response.lower():
        name = get_voice_input("Please say your name for booking.")
        booking = {
            "id": str(uuid4())[:8].upper(),
            "type": item_type,
            "user": name,
            "date": "Today",
        }
        if item_type == "hotel":
            booking.update({
                "hotel": item_data["name"],
                "city": city,
                "price": item_data.get("price", "N/A")
            })
        elif item_type == "flight":
            booking.update({
                "airline": item_data["airline"],
                "flight_number": item_data["flight_number"],
                "destination": city,
                "departure": item_data["departure"],
                "arrival": item_data["arrival"],
                "price": item_data["price"]
            })
        result = save_booking(booking)
        confirmation = f"✅ Booking confirmed!\nConfirmation ID: {booking['id']}\nName: {name}\nType: {item_type.title()}\n"
        if item_type == "hotel":
            confirmation += f"Hotel: {booking['hotel']} in {city}"
        else:
            confirmation += f"Flight: {booking['airline']} {booking['flight_number']} to {city}"
        confirmation += f"\nDate: Today\nThank you for choosing our service!"
        speak_output(confirmation)
        print(confirmation)
        return confirmation, True
    return "Booking cancelled.", False

def normalize_choice(choice):
    number_map = {"one": "1", "two": "2", "three": "3", "1": "1", "2": "2", "3": "3"}
    return number_map.get(choice.strip().lower(), choice.strip())

def handle_query(text):
    text_lower = text.lower()
    city = extract_city(text_lower)
    # Save or retrieve last known city from context
    if city:
        context["last_city"] = city
    else:
        city = context.get("last_city")

    if "weather" in text_lower:
        if not city:
            city_input = get_voice_input("Say the city for weather.")
            city = extract_city(city_input)
        if city:
            context["last_city"] = city
            return get_weather(city), False
        return "No city provided for weather.", False



    elif "hotel" in text_lower or "stay" in text_lower:
        if not city:
            city = extract_city(get_voice_input("Which city are you looking for hotels in?"))
        if not city:
            return "Please specify a city for hotels.", False
        context["last_city"] = city
        hotels = get_hotel_options(city)
        result = f"Top hotels in {city}:\n" + "\n".join(
            [f"{i+1}. {h['name']} - {h['price']} - {h['rating']}⭐" for i, h in enumerate(hotels)]
        )
        speak_output("Here are the top options.")
        print(result)
        speak_output("Say 1, 2, or 3 to book.")
        choice = get_voice_input()
        idx = normalize_choice(choice)
        try:
            idx = int(idx) - 1
            if 0 <= idx < len(hotels):
                return ask_for_booking("hotel", hotels[idx], city)
            return "Invalid selection. Booking not made.", False
        except ValueError:
            return "Invalid input. Booking not made.", False

    elif "flight" in text_lower or "fly" in text_lower:
        if not city:
            city = extract_city(get_voice_input("Where would you like to fly to?"))
        if not city:
            return "Please specify a city for flights.", False
        context["last_city"] = city
        flights = get_flight_options(city)
        result = f"Flights to {city}:\n" + "\n".join(
            [f"{i+1}. {f['airline']} {f['flight_number']} - {f['price']}" for i, f in enumerate(flights)]
        )
        speak_output("Here are your flight options.")
        print(result)
        speak_output("Say 1, 2, or 3 to book.")
        choice = get_voice_input()
        idx = normalize_choice(choice)
        try:
            idx = int(idx) - 1
            if 0 <= idx < len(flights):
                return ask_for_booking("flight", flights[idx], city)
            return "Invalid selection. Booking not made.", False
        except ValueError:
            return "Invalid input. Booking not made.", False

    elif any(word in text_lower for word in ["places", "attractions", "visit", "see"]):
        if not city:
            city = extract_city(get_voice_input("Which city would you like to explore?"))
        if not city:
            return "Please specify a city to explore.", False
        context["last_city"] = city
        places = get_top_attractions(city)
        return f"🏛️ Top attractions in {city}:\n" + "\n".join(places), False

    elif "my bookings" in text_lower or "reservations" in text_lower:
        bookings = load_bookings()
        if not bookings:
            return "You have no bookings yet.", False
        result = "Your Bookings:\n" + "=" * 50 + "\n"
        for b in bookings:
            if b['type'] == 'hotel':
                result += f"ID: {b['id']} | Hotel: {b['hotel']} in {b['city']} | Price: {b.get('price', 'N/A')}\n"
            else:
                result += f"ID: {b['id']} | Flight: {b['airline']} to {b['destination']} | Price: {b.get('price', 'N/A')}\n"
        return result, False

    return "Sorry, I didn't understand. Try saying weather, hotel, flight, or places.", False

def main():
    speak_output("Hello! I'm your voice travel assistant.")
    while True:
        spoken = get_voice_input("How can I help? Say 'exit' to quit.")
        if not spoken:
            speak_output("Please try again.")
            continue
        if "exit" in spoken.lower():
            speak_output("Goodbye! Happy travels!")
            break
        print(f"🕣️ You said: {spoken}")
        response, spoken_already = handle_query(spoken)
        if not spoken_already:
            print("💬", response)
            speak_output(response)

if __name__ == "__main__":
    main()