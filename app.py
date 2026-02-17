import streamlit as st

from logging_config import configure_logging, safe_text

import logging

from config import GOOGLE_MAPS_API_KEY
from google_maps_client import build_shareable_directions_link, geocode, get_routes
from route_selector import select_best_route
from waypoint_planner import plan_relaxed_route_with_waypoints


logger = logging.getLogger(__name__)


def _meters_to_km(m):
    return m / 1000.0


def _seconds_to_min(s):
    return s / 60.0


def _parse_waypoints_csv(raw: str):
    """Parse user-entered waypoints.

    Accepts comma-separated items. Each item can be a place/address string OR "lat,lng".
    """

    raw = (raw or "").strip()
    if not raw:
        return None

    # NOTE: We accept comma-separated values for UX simplicity. This does mean that
    # an individual "lat,lng" waypoint should be entered without extra commas beyond
    # the single pair, e.g. "28.613939,77.209021".
    # If users need more complex formatting, they can enter an address instead.
    items = [w.strip() for w in raw.split(",") if w.strip()]
    return items or None


def _render_route(route: dict, origin: str, destination: str):
    st.subheader("Selected route")
    st.write(f"**Summary:** {route.get('summary', '')}")
    st.write(f"**Distance:** {_meters_to_km(route['distance']):.2f} km")
    st.write(f"**Normal duration:** {_seconds_to_min(route['duration']):.1f} min")
    st.write(f"**Traffic duration:** {_seconds_to_min(route['duration_in_traffic']):.1f} min")
    st.write(f"**Stress score:** {route.get('stress', 0.0):.3f}")
    st.write(f"**Cost score:** {route.get('cost', 0.0):.3f}")

    waypoints = route.get("waypoints") or None
    if waypoints:
        st.write("**Waypoints used:**")
        st.code("\n".join(waypoints))

    share_url = build_shareable_directions_link(
        origin=origin,
        destination=destination,
        waypoints=waypoints,
        travelmode="driving",
    )

    st.write("**Google Maps link (opens in browser / Maps app):**")
    st.link_button("Open route in Google Maps", share_url)
    st.code(share_url)


def main():
    configure_logging()
    st.set_page_config(page_title="Biker relaxed routing", layout="centered")
    st.title("Biker Relaxed Routing")

    api_key_present = bool(GOOGLE_MAPS_API_KEY)
    if not api_key_present:
        st.warning("GOOGLE_MAPS_API_KEY is not set. Add it to Streamlit secrets or set the environment variable before running.")

    origin = st.text_input("Source (origin)", placeholder="e.g. Connaught Place, Delhi")
    destination = st.text_input("Destination", placeholder="e.g. India Gate, Delhi")

    logger.info("UI inputs updated origin=%s destination=%s", safe_text(origin), safe_text(destination))

    mode = st.radio(
        "Mode",
        options=["Normal", "Manual waypoints", "Auto (relaxed) waypoints"],
        horizontal=True,
    )

    manual_waypoints_raw = ""
    auto_params = None

    if mode == "Manual waypoints":
        manual_waypoints_raw = st.text_area(
            "Waypoints (comma-separated)",
            placeholder="Waypoint 1, Waypoint 2, 28.613939,77.209021",
            help="Enter comma-separated waypoints. Each waypoint can be an address/place or a 'lat,lng' pair.",
        )

    if mode == "Auto (relaxed) waypoints":
        with st.expander("Auto-waypoint tuning", expanded=False):
            circle_radius_m = st.slider("Search radius per step (meters)", 250, 5000, 1000, step=50)
            candidates_per_step = st.slider("Candidates per step", 4, 24, 12)
            heading_spread_deg = st.slider("Heading spread (degrees)", 10, 180, 60)
            max_waypoints = st.slider("Max waypoints", 0, 20, 5)
            auto_params = {
                "circle_radius_m": float(circle_radius_m),
                "candidates_per_step": int(candidates_per_step),
                "heading_spread_deg": float(heading_spread_deg),
                "max_waypoints": int(max_waypoints),
            }

    generate = st.button(
        "Generate Google Maps link",
        type="primary",
        disabled=not (origin.strip() and destination.strip()),
    )

    if not generate:
        st.caption("Enter a source and destination, then click 'Generate Google Maps link'.")
        return

    try:
        if mode == "Normal":
            logger.info("Mode normal")
            routes = get_routes(origin, destination, travelmode="driving")
            best_route = select_best_route(routes)
            if not best_route:
                raise Exception("No route found")

        elif mode == "Manual waypoints":
            logger.info("Mode manual waypoints")
            waypoints = _parse_waypoints_csv(manual_waypoints_raw)
            logger.info("Manual waypoints count=%s", 0 if not waypoints else len(waypoints))
            routes = get_routes(origin, destination, waypoints=waypoints, travelmode="driving")
            best_route = select_best_route(routes)
            if not best_route:
                raise Exception("No route found")
            best_route["waypoints"] = waypoints

        else:  # Auto (relaxed) waypoints
            logger.info("Mode auto waypoints")
            with st.spinner("Geocoding origin/destination..."):
                origin_latlng = geocode(origin)
                destination_latlng = geocode(destination)

            logger.info(
                "Geocoded origin_latlng=%s destination_latlng=%s",
                origin_latlng,
                destination_latlng,
            )

            with st.spinner("Searching for relaxed waypoints..."):
                best_route = plan_relaxed_route_with_waypoints(
                    origin=origin,
                    destination=destination,
                    origin_latlng=origin_latlng,
                    destination_latlng=destination_latlng,
                    travelmode="driving",
                    **(auto_params or {}),
                )

            logger.info(
                "Auto search done waypoints=%s distance_m=%s stress=%s",
                0 if not best_route.get("waypoints") else len(best_route["waypoints"]),
                best_route.get("distance"),
                best_route.get("stress"),
            )

            # Guardrail: Google Maps share URLs can get very long with many waypoints.
            # We warn, but still show the link.
            if (best_route.get("waypoints") or []) and len(best_route["waypoints"]) > 20:
                st.warning("This route has many waypoints; the shareable URL may be too long for some apps.")

        _render_route(best_route, origin=origin, destination=destination)

    except Exception as e:
        logger.exception("Route generation failed")
        st.error(str(e))


if __name__ == "__main__":
    main()
