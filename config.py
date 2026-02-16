import os

# Prefer Streamlit secrets when running inside Streamlit; fall back to env var.
try:
    import streamlit as st
    GOOGLE_MAPS_API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
except Exception:
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# Controls stress avoidance strength
LAMBDA = 3.0

# Max acceptable distance increase as a function of distance
def get_max_distance_ratio(distance):
    """
    Returns the max acceptable distance ratio based on the input distance.
    - For distance 1-5: returns 2
    - For distance >5-10: returns 1.7
    - For distance >10: returns 1.5
    """
    if distance <= 0:
        raise ValueError("Distance must be positive")
    if distance <= 5:
        return 2
    elif distance <= 10:
        return 1.7
    else:
        return 1.5

# Legacy constant for backward compatibility
MAX_DISTANCE_RATIO = 1.15

# Example usage (remove or comment out in production)
if __name__ == "__main__":
    for d in [1, 5, 7, 10, 12, 0, -3]:
        try:
            print(f"Distance: {d}, Ratio: {get_max_distance_ratio(d)}")
        except Exception as e:
            print(f"Distance: {d}, Error: {e}")
