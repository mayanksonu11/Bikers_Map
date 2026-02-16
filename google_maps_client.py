import requests
from urllib.parse import urlencode
from config import GOOGLE_MAPS_API_KEY

BASE_URL = "https://maps.googleapis.com/maps/api/directions/json"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

def _serialize_waypoints(waypoints, optimize_waypoints=False):
    """Serialize waypoints for Google Directions API.

    Accepts:
      - None / empty: returns None
      - str: returned as-is (assumed already formatted as 'A|B|C')
      - list/tuple of str: joined with '|'

    If optimize_waypoints=True, prefixes with 'optimize:true|'.
    """

    if not waypoints:
        return None

    if isinstance(waypoints, str):
        serialized = waypoints.strip()
    elif isinstance(waypoints, (list, tuple)):
        cleaned = [str(w).strip() for w in waypoints if str(w).strip()]
        serialized = "|".join(cleaned)
    else:
        raise TypeError("waypoints must be a string, list/tuple of strings, or None")

    if not serialized:
        return None

    if optimize_waypoints:
        serialized = f"optimize:true|{serialized}"

    return serialized


def _sum_legs(legs):
    """Return (distance_m, duration_s, duration_in_traffic_s) summed across all legs."""

    distance = 0
    duration = 0
    duration_in_traffic = 0

    for leg in legs:
        distance += leg["distance"]["value"]
        duration += leg["duration"]["value"]
        duration_in_traffic += leg.get("duration_in_traffic", leg["duration"])["value"]

    return distance, duration, duration_in_traffic


def get_routes(origin, destination, waypoints=None, optimize_waypoints=False):
    params = {
        "origin": origin,
        "destination": destination,
        "alternatives": "true",
        "departure_time": "now",
        "traffic_model": "best_guess",
        "key": GOOGLE_MAPS_API_KEY
    }

    serialized_waypoints = _serialize_waypoints(waypoints, optimize_waypoints=optimize_waypoints)
    if serialized_waypoints:
        params["waypoints"] = serialized_waypoints

    response = requests.get(BASE_URL, params=params)

    if response.status_code != 200:
        raise Exception(f"API request failed: HTTP {response.status_code} - {response.text}")

    data = response.json()

    # Google Directions may return HTTP 200 with an error status in the payload.
    if data.get("status") not in (None, "OK"):
        raise Exception(f"Directions API error: {data.get('status')} - {data.get('error_message', '')}")

    routes = []

    for route in data.get("routes", []):
        legs = route.get("legs", [])
        if not legs:
            continue

        distance, duration, duration_in_traffic = _sum_legs(legs)

        routes.append({
            "distance": distance,
            "duration": duration,
            "duration_in_traffic": duration_in_traffic,
            "summary": route.get("summary", ""),
            "polyline": route["overview_polyline"]["points"]
        })

    return routes


def geocode(address):
    """Resolve a human-readable address/place into (lat, lng) using Google Geocoding API."""

    params = {
        "address": address,
        "key": GOOGLE_MAPS_API_KEY,
    }

    response = requests.get(GEOCODE_URL, params=params)
    if response.status_code != 200:
        raise Exception(f"Geocoding API request failed: HTTP {response.status_code} - {response.text}")

    data = response.json()
    if data.get("status") != "OK":
        raise Exception(f"Geocoding API error: {data.get('status')} - {data.get('error_message', '')}")

    results = data.get("results", [])
    if not results:
        raise Exception("Geocoding API returned no results")

    loc = results[0]["geometry"]["location"]
    return loc["lat"], loc["lng"]


def build_shareable_directions_link(origin, destination, waypoints=None, travelmode="bicycling"):
    """Build a shareable Google Maps link that includes waypoints.

    This is intended for humans to open in a browser / Google Maps app.
    """

    params = {
        "api": "1",
        "origin": origin,
        "destination": destination,
        "travelmode": travelmode,
    }

    if waypoints:
        if isinstance(waypoints, str):
            serialized = waypoints.strip()
        elif isinstance(waypoints, (list, tuple)):
            serialized = "|".join([str(w).strip() for w in waypoints if str(w).strip()])
        else:
            raise TypeError("waypoints must be a string, list/tuple of strings, or None")

        if serialized:
            # Google Maps URL parameter name is 'waypoints'
            params["waypoints"] = serialized

    # Use a safe separator for the `waypoints` parameter.
    # Google expects waypoints separated by '|'. We want to preserve the pipe character,
    # so we mark it as safe when encoding.
    return "https://www.google.com/maps/dir/?" + urlencode(params, safe="|,")
