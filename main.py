from google_maps_client import get_routes, geocode, build_shareable_directions_link
from route_selector import select_best_route
from waypoint_planner import plan_relaxed_route_with_waypoints

def meters_to_km(m):
    return m / 1000

def seconds_to_min(s):
    return s / 60

def main():

    origin = input("Enter origin: ")
    destination = input("Enter destination: ")
    mode = input("Mode: [1] normal  [2] manual-waypoints  [3] auto-waypoints : ").strip() or "1"

    if mode == "2":
        waypoints_raw = input(
            "Enter waypoints (optional, comma-separated; leave blank for none): "
        ).strip()

        waypoints = None
        if waypoints_raw:
            # Google Directions API expects waypoints separated by '|'.
            # We'll accept a friendlier comma-separated input.
            waypoints = [w.strip() for w in waypoints_raw.split(",") if w.strip()]

        routes = get_routes(origin, destination, waypoints=waypoints)
        best_route = select_best_route(routes)
        if best_route is not None:
            best_route["waypoints"] = waypoints

    elif mode == "3":
        print("Geocoding origin/destination...")
        origin_latlng = geocode(origin)
        destination_latlng = geocode(destination)

        print("Searching for stress-minimizing waypoints within max distance constraint...")
        best_route = plan_relaxed_route_with_waypoints(
            origin=origin,
            destination=destination,
            origin_latlng=origin_latlng,
            destination_latlng=destination_latlng,
            circle_radius_m=1000.0,
            candidates_per_step=12,
            heading_spread_deg=60.0,
            max_waypoints=20,
        )

        # For consistent printing below.
        routes = [best_route]

    else:
        routes = get_routes(origin, destination)
        best_route = select_best_route(routes)

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
        travelmode="bicycling",
    )
    print(f"\nShareable Google Maps Link:\n{share_url}")

if __name__ == "__main__":
    main()
