import logging

from google_maps_client import get_routes, geocode, build_shareable_directions_link
from route_selector import select_best_route
from waypoint_planner import plan_relaxed_route_with_waypoints

from logging_config import configure_logging, safe_text


logger = logging.getLogger(__name__)

def meters_to_km(m):
    return m / 1000

def seconds_to_min(s):
    return s / 60

def main():

    configure_logging()

    origin = input("Enter origin: ")
    destination = input("Enter destination: ")
    mode = input("Mode: [1] normal  [2] manual-waypoints  [3] auto-waypoints : ").strip() or "1"

    logger.info("CLI start mode=%s origin=%s destination=%s", mode, safe_text(origin), safe_text(destination))

    if mode == "2":
        logger.info("Mode manual waypoints")
        waypoints_raw = input(
            "Enter waypoints (optional, comma-separated; leave blank for none): "
        ).strip()

        waypoints = None
        if waypoints_raw:
            # Google Directions API expects waypoints separated by '|'.
            # We'll accept a friendlier comma-separated input.
            waypoints = [w.strip() for w in waypoints_raw.split(",") if w.strip()]

        routes = get_routes(origin, destination, waypoints=waypoints, travelmode="driving")
        best_route = select_best_route(routes)
        if best_route is not None:
            best_route["waypoints"] = waypoints

    elif mode == "3":
        logger.info("Mode auto waypoints")
        print("Geocoding origin/destination...")
        origin_latlng = geocode(origin)
        destination_latlng = geocode(destination)

        logger.info("Geocoded origin_latlng=%s destination_latlng=%s", origin_latlng, destination_latlng)

        print("Searching for stress-minimizing waypoints within max distance constraint...")
        best_route = plan_relaxed_route_with_waypoints(
            origin=origin,
            destination=destination,
            origin_latlng=origin_latlng,
            destination_latlng=destination_latlng,
            travelmode="driving",
            circle_radius_m=1000.0,
            candidates_per_step=12,
            heading_spread_deg=60.0,
            max_waypoints=20,
        )

        # For consistent printing below.
        routes = [best_route]

    else:
        logger.info("Mode normal")
        routes = get_routes(origin, destination, travelmode="driving")
        best_route = select_best_route(routes)

    logger.info(
        "Selected route distance_m=%s stress=%s waypoints=%s",
        best_route.get("distance"),
        best_route.get("stress"),
        0 if not best_route.get("waypoints") else len(best_route.get("waypoints")),
    )

    print(f"Found {len(routes)} routes\n")

    print("Best Relaxed Route Selected:\n")

    print(f"Summary: {best_route['summary']}")
    print(f"Distance: {meters_to_km(best_route['distance']):.2f} km")
    print(f"Normal Duration: {seconds_to_min(best_route['duration']):.2f} min")
    print(f"Traffic Duration: {seconds_to_min(best_route['duration_in_traffic']):.2f} min")
    print(f"Stress Score: {best_route['stress']:.2f}")
    print(f"Cost Score: {best_route['cost']:.2f}")

    if best_route.get("waypoints"):
        print(f"Waypoints Used: {best_route['waypoints']}")

    share_url = build_shareable_directions_link(
        origin=origin,
        destination=destination,
        waypoints=best_route.get("waypoints"),
        travelmode="driving",
    )
    print(f"\nShareable Google Maps Link:\n{share_url}")

if __name__ == "__main__":
    main()
