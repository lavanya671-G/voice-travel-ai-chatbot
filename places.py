# places.py
import requests

API_KEY = "484e5851895a4b54bcdabcb4c1f5e34d"

def get_top_attractions(city):
    try:
        # Step 1: Get coordinates of the city
        geocode_url = f"https://api.geoapify.com/v1/geocode/search?text={city}&apiKey={API_KEY}"
        geo_resp = requests.get(geocode_url).json()
        features = geo_resp.get("features", [])
        
        if not features:
            return [f"⚠️ Could not find location for '{city}'. Please check the spelling."]
        
        coords = features[0]["geometry"]["coordinates"]
        lon, lat = coords[0], coords[1]

        # Step 2: Get points of interest near the city
        pois_url = (
            f"https://api.geoapify.com/v2/places?"
            f"categories=tourism.sights&filter=circle:{lon},{lat},10000&limit=5&apiKey={API_KEY}"
        )
        pois_resp = requests.get(pois_url).json()
        places = pois_resp.get("features", [])

        if not places:
            return [f"⚠️ No attractions found in '{city}'. Try another city."]

        # Step 3: Format and return attraction details
        formatted_places = []
        for i, place in enumerate(places, start=1):
            name = place["properties"].get("name", "Unknown Place")
            address = place["properties"].get("address_line2", "No address available")
            formatted_places.append(f"{i}. {name} - 📍 {address}")

        return formatted_places

    except Exception as e:
        return [f"⚠️ Error getting attractions: {e}"]


# ✅ Test (Only when running directly)
if __name__ == "__main__":
    city_name = "Delhi"
    attractions = get_top_attractions(city_name)
    for a in attractions:
        print(a)
