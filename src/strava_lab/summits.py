import math
import pandas as pd
import polyline


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def count_touches_debounced(encoded_polyline, summit_lat, summit_lon,
                            enter_m=80, exit_m=120, exit_consec_points=5) -> int:
    """
    Count distinct summit 'touches' as entries into a radius,
    with hysteresis + debounced exit to avoid GPS jitter double-counting.
    """
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


def add_summit_metrics(df: pd.DataFrame, name: str, summit_lat: float, summit_lon: float,
                      enter_m=80, exit_m=120, exit_consec_points=5) -> pd.DataFrame:
    """
    Adds two columns to that:
      {name}_touches: int
      {name}_summit: bool
    """
    touches_col = f"{name}_touches"
    summit_col = f"{name}_summit"

    df = df.copy()
    df[touches_col] = df["map.summary_polyline"].apply(
        lambda p: count_touches_debounced(
            p, summit_lat, summit_lon,
            enter_m=enter_m, exit_m=exit_m,
            exit_consec_points=exit_consec_points
        )
    )
    df[summit_col] = df[touches_col] > 0
    return df