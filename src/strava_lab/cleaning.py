import pandas as pd

M_TO_FT = 3.28084
M_TO_MI = 1 / 1609.344
S_TO_HR = 1 / 3600

def normalize_activities(activities: list[dict]) -> pd.DataFrame:
    df = pd.json_normalize(activities)

    # --------------------
    # Datetimes (keep both)
    # --------------------
    if "start_date" in df.columns:
        df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce", utc=True)

    if "start_date_local" in df.columns:
        df["start_date_local"] = pd.to_datetime(df["start_date_local"], errors="coerce")

    # --------------------
    # Rename raw-unit columns (to preserve meaning)
    # Then add user-friendly derived columns
    # --------------------

    # Distance: meters -> miles
    if "distance" in df.columns:
        df = df.rename(columns={"distance": "distance_m"})
        df["distance_mi"] = df["distance_m"] * M_TO_MI

    # Times: seconds -> hours
    if "moving_time" in df.columns:
        df = df.rename(columns={"moving_time": "moving_time_s"})
        df["moving_time_hr"] = df["moving_time_s"] * S_TO_HR

    if "elapsed_time" in df.columns:
        df = df.rename(columns={"elapsed_time": "elapsed_time_s"})
        df["elapsed_time_hr"] = df["elapsed_time_s"] * S_TO_HR

    # Elevation gain + highs/lows: meters -> feet
    if "total_elevation_gain" in df.columns:
        df = df.rename(columns={"total_elevation_gain": "total_elevation_gain_m"})
        df["elevation_gain_ft"] = df["total_elevation_gain_m"] * M_TO_FT

    if "elev_high" in df.columns:
        df = df.rename(columns={"elev_high": "elev_high_m"})
        df["elev_high_ft"] = df["elev_high_m"] * M_TO_FT

    if "elev_low" in df.columns:
        df = df.rename(columns={"elev_low": "elev_low_m"})
        df["elev_low_ft"] = df["elev_low_m"] * M_TO_FT

    return df