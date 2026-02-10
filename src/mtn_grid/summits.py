import math
import pandas as pd
import polyline

"""
Establish haversine formula to calculate distance between two lat/long points
"""

def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))

"""
Calculate a summit. This function checks each lat/long point in the polyline col of the dataframe,
then uses haversine_m() to measure distance from the summit lat/long. GPS jitters are accounted for
by enter_m, exit_m, and exit_consec_points. Enter_m defines the distance window from the summit which counts
a valid ascent, and exit_m defines the distance window for the exit (i.e. when the track is within enter_m
of summit, summit is counted. Until the track exits the distance window by exit_m for exit_consec_points, a
new summit will not e counted.)
"""

def count_touches_debounced(encoded_polyline, summit_lat, summit_lon,
                            enter_m=80, exit_m=120, exit_consec_points=5) -> int:
    if pd.isna(encoded_polyline):
        return 0

    pts = polyline.decode(encoded_polyline)
    touches = 0
    in_zone = False
    outside_streak = 0

    for lat, lon in pts:
        d = haversine_m(lat, lon, summit_lat, summit_lon)

        if not in_zone:
            if d <= enter_m:
                touches += 1
                in_zone = True
                outside_streak = 0
        else:
            if d >= exit_m:
                outside_streak += 1
                if outside_streak >= exit_consec_points:
                    in_zone = False
                    outside_streak = 0
            else:
                outside_streak = 0

    return touches

"""
Take in a summit and its lat/long, and add two cols to the dataframe - x_summit and x_touches.
x_summit is a boolean categorizing the activities as having a summit or not, and x_touches
counts the summits in the file based on count_touches_debounced().
"""

def add_summit_metrics(df: pd.DataFrame, name: str, summit_lat: float, summit_lon: float,
                      enter_m=80, exit_m=120, exit_consec_points=5) -> pd.DataFrame:
    """
    Adds two columns to that:
      {name}_touches: int
      {name}_summit: bool
    """
    touches_col = f'{name}_touches'
    summit_col = f'{name}_summit'

    df = df.copy()
    df[touches_col] = df['map.summary_polyline'].apply(
        lambda p: count_touches_debounced(
            p, summit_lat, summit_lon,
            enter_m=enter_m, exit_m=exit_m,
            exit_consec_points=exit_consec_points
        )
    )
    df[summit_col] = df[touches_col] > 0
    return df