from config import LAMBDA, get_max_distance_ratio

def compute_stress(duration, duration_in_traffic):
    return duration_in_traffic / duration

def compute_cost(distance, stress):
    return distance * (1 + LAMBDA * (stress - 1))

def select_best_route(routes):

    shortest_distance = min(route["distance"] for route in routes)
    max_allowed_distance = shortest_distance * get_max_distance_ratio(shortest_distance / 1000.0)

    best_route = None
    best_cost = float("inf")

    for route in routes:

        distance = route["distance"]
        duration = route["duration"]
        duration_in_traffic = route["duration_in_traffic"]

        # Enforce max path length as a ratio over the shortest available route.
        if distance > max_allowed_distance:
            continue

        stress = compute_stress(duration, duration_in_traffic)

        cost = compute_cost(distance, stress)

        route["stress"] = stress
        route["cost"] = cost

        if cost < best_cost:
            best_cost = cost
            best_route = route

    return best_route
