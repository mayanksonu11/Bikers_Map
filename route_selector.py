from config import get_max_distance_ratio


# When comparing routes, we prioritize stress (a proxy for discomfort) and use distance
# only as a tie-breaker among similarly-stressed routes.
STRESS_EPSILON = 1e-3

def compute_stress(duration, duration_in_traffic):
    return duration_in_traffic / duration

def compute_cost(distance, stress):
    """Legacy helper.

    Historically we used a distance-weighted cost. The project now selects routes
    lexicographically by (stress, distance) under a max-distance constraint.

    We keep this function for backward compatibility with any downstream imports.
    """
    return stress


def _is_better(stress_a, distance_a, stress_b, distance_b, eps=STRESS_EPSILON):
    """Return True if (a) is better than (b) using stress-first comparison."""

    if stress_a < stress_b - eps:
        return True
    if abs(stress_a - stress_b) <= eps and distance_a < distance_b:
        return True
    return False

def select_best_route(routes):

    shortest_distance = min(route["distance"] for route in routes)
    max_allowed_distance = shortest_distance * get_max_distance_ratio(shortest_distance / 1000.0)

    best_route = None
    best_stress = float("inf")
    best_distance = float("inf")

    for route in routes:

        distance = route["distance"]
        duration = route["duration"]
        duration_in_traffic = route["duration_in_traffic"]

        # Enforce max path length as a ratio over the shortest available route.
        if distance > max_allowed_distance:
            continue

        stress = compute_stress(duration, duration_in_traffic)

        # Expose values for UI/debugging.
        route["stress"] = stress
        route["cost"] = stress  # kept for UI display; no longer distance-weighted

        if _is_better(stress, distance, best_stress, best_distance):
            best_stress = stress
            best_distance = distance
            best_route = route

    return best_route
