import math

from config import get_max_distance_ratio
from google_maps_client import get_routes
from route_selector import compute_stress, _is_better


def _bearing_deg(lat1, lng1, lat2, lng2):
    """Initial bearing from (lat1,lng1) to (lat2,lng2) in degrees [0, 360)."""

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_lambda = math.radians(lng2 - lng1)

    y = math.sin(d_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    brng = math.degrees(math.atan2(y, x))
    return (brng + 360.0) % 360.0


def _destination_point(lat, lng, bearing_deg, distance_m):
    """Move from (lat,lng) along bearing by distance (meters) on a sphere."""
    # Spherical earth model
    R = 6371000.0
    delta = distance_m / R
    theta = math.radians(bearing_deg)

    phi1 = math.radians(lat)
    lambda1 = math.radians(lng)

    sin_phi2 = math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(theta)
    phi2 = math.asin(sin_phi2)

    y = math.sin(theta) * math.sin(delta) * math.cos(phi1)
    x = math.cos(delta) - math.sin(phi1) * math.sin(phi2)
    lambda2 = lambda1 + math.atan2(y, x)

    return math.degrees(phi2), ((math.degrees(lambda2) + 540.0) % 360.0) - 180.0


def _candidate_circle_points(origin_latlng, destination_latlng, radius_m=1000.0, num_points=12, heading_spread_deg=60.0):
    """Generate candidate waypoint points on a circle around origin.

    We bias the candidates to be roughly in the direction of the destination.
    """
    o_lat, o_lng = origin_latlng
    d_lat, d_lng = destination_latlng
    base_bearing = _bearing_deg(o_lat, o_lng, d_lat, d_lng)

    if num_points <= 1:
        bearings = [base_bearing]
    else:
        start = base_bearing - heading_spread_deg / 2.0
        step = heading_spread_deg / (num_points - 1)
        bearings = [start + i * step for i in range(num_points)]

    pts = []
    for b in bearings:
        pts.append(_destination_point(o_lat, o_lng, b, radius_m))
    return pts


def _format_latlng(lat, lng):
    # Keep as decimal degrees; Google accepts "lat,lng" strings.
    return f"{lat:.6f},{lng:.6f}"


def plan_relaxed_route_with_waypoints(
    origin,
    destination,
    origin_latlng,
    destination_latlng,
    circle_radius_m=1000.0,
    candidates_per_step=12,
    heading_spread_deg=60.0,
    max_waypoints=2,
):
    """Heuristic search for waypoints to reduce stress while staying within max distance.

    Approach:
      1) Get baseline routes (no waypoints) and choose best under distance constraint.
      2) Use the shortest baseline distance to compute the allowed max distance ratio.
      3) Greedily add up to `max_waypoints` waypoints. At each step, try candidate points
         on a circle (default 1km) around the current point, biased toward the destination.
      4) Keep the candidate route with the lowest cost, subject to the max distance.

    Notes:
      - This uses Directions API as the road-snapping / traffic oracle.
      - `origin_latlng` and `destination_latlng` are required because we don't currently
        call Geocoding API in this project.
    """

    baseline_routes = get_routes(origin, destination)
    if not baseline_routes:
        raise Exception("No baseline routes returned by Directions API")

    shortest_distance = min(r["distance"] for r in baseline_routes)
    max_allowed_distance = shortest_distance * get_max_distance_ratio(shortest_distance / 1000.0)

    def _best_under_limit(routes):
        best = None
        best_stress = float("inf")
        best_distance = float("inf")
        for r in routes:
            if r["distance"] > max_allowed_distance:
                continue
            stress = compute_stress(r["duration"], r["duration_in_traffic"])
            distance = r["distance"]
            if _is_better(stress, distance, best_stress, best_distance):
                best_stress = stress
                best_distance = distance
                best = {
                    **r,
                    "stress": stress,
                    # Keep the field name for UI compatibility.
                    "cost": stress,
                }
        return best

    current_best = _best_under_limit(baseline_routes)
    if current_best is None:
        # If nothing fits the ratio, fall back to the shortest anyway.
        r = min(baseline_routes, key=lambda x: x["distance"])
        stress = compute_stress(r["duration"], r["duration_in_traffic"])
        current_best = {**r, "stress": stress, "cost": stress}

    chosen_waypoints = []
    current_latlng = origin_latlng
    dest_latlng = destination_latlng

    for _ in range(max_waypoints):
        candidates = _candidate_circle_points(
            current_latlng,
            dest_latlng,
            radius_m=circle_radius_m,
            num_points=candidates_per_step,
            heading_spread_deg=heading_spread_deg,
        )

        improved = False
        best_candidate = None
        best_candidate_waypoints = None

        for lat, lng in candidates:
            wp = _format_latlng(lat, lng)

            # Evaluate full route with the proposed additional waypoint(s)
            trial_waypoints = chosen_waypoints + [wp]
            trial_routes = get_routes(origin, destination, waypoints=trial_waypoints)
            trial_best = _best_under_limit(trial_routes)
            if trial_best is None:
                continue

            # Stress-first improvement; use distance as tie-breaker.
            if _is_better(
                trial_best["stress"],
                trial_best["distance"],
                current_best["stress"],
                current_best["distance"],
            ):
                improved = True
                current_best = trial_best
                best_candidate = (lat, lng)
                best_candidate_waypoints = trial_waypoints

        if not improved:
            break

        chosen_waypoints = best_candidate_waypoints
        current_latlng = best_candidate

    current_best["waypoints"] = chosen_waypoints
    # Useful for debugging/printing.
    current_best["max_allowed_distance"] = max_allowed_distance
    current_best["shortest_distance"] = shortest_distance

    return current_best
