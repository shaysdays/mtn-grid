import pandas as pd

M_TO_FT = 3.28084
M_TO_MI = 1 / 1609.344
S_TO_HR = 1 / 3600

def normalize_activities(activities: list[dict]) -> pd.DataFrame:
    df = pd.json_normalize(activities)

    # 1. Categorize Sport Type
    if 'sport_type' in df.columns:
        mapping = {
            # Cycle
            'Ride': 'Cycle', 'MountainBikeRide': 'Cycle', 'GravelRide': 'Cycle', 
            'EBikeRide': 'Cycle', 'EMountainBikeRide': 'Cycle', 'Handcycle': 'Cycle', 
            'Velomobile': 'Cycle', 'VirtualRide': 'Cycle',

            # Run
            'Run': 'Run', 'TrailRun': 'Run', 'VirtualRun': 'Run',

            # Paddlesport
            'Canoeing': 'Paddlesport', 'Kayaking': 'Paddlesport', 'Rowing': 'Paddlesport', 'VirtualRow': 'Paddlesport',

            # Ski/Snowboard
            'AlpineSki': 'Ski/Snowboard', 'BackcountrySki': 'Ski/Snowboard', 'NordicSki': 'Ski/Snowboard', 'Snowboard': 'Ski/Snowboard',

            # Gym
            'Crossfit': 'Gym', 'Elliptical': 'Gym', 'HighIntensityIntervalTraining': 'Gym', 
            'Pilates': 'Gym', 'StairStepper': 'Gym', 'WeightTraining': 'Gym', 'Workout': 'Gym',

            # Racquet
            'Tennis': 'Racquet', 'Pickleball': 'Racquet', 'Badminton': 'Racquet', 
            'Squash': 'Racquet', 'TableTennis': 'Racquet', 'Racquetball': 'Racquet',
            
            # Singles/Unique
            'Walk': 'Walk',
            'Hike': 'Hike',
            'Swim': 'Swim',
            'Snowshoe': 'Snowshoe',
            'Wheelchair': 'Wheelchair',
            'StandUpPaddling': 'Paddleboard',
            'Surfing': 'Surf',
            'Sail': 'Sail',
            'Kitesurf': 'Kitesurf',
            'Windsurf': 'Windsurf',
            'RockClimbing': 'Rock Climbing',
            'RollerSki': 'Roller Ski',
            'IceSkate': 'Ice Skate',
            'InlineSkate': 'Inline Skate',
            'Golf': 'Golf',
            'Skateboard': 'Skateboard',
            'Soccer': 'Soccer',
            'Yoga': 'Yoga'
        }
        
        # Create the clean column, falling back to the raw value if not found in mapping
        df['sport_type_clean'] = df['sport_type'].map(mapping).fillna(df['sport_type'])

    # 2. Datetimes
    if 'start_date' in df.columns:
        df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce', utc=True)

    if 'start_date_local' in df.columns:
        df['start_date_local'] = pd.to_datetime(df['start_date_local'], errors='coerce')

    # 3. Unit Conversions
    if 'distance' in df.columns:
        df = df.rename(columns={'distance': 'distance_m'})
        df['distance_mi'] = df['distance_m'] * M_TO_MI

    if 'moving_time' in df.columns:
        df = df.rename(columns={'moving_time': 'moving_time_s'})
        df['moving_time_hr'] = df['moving_time_s'] * S_TO_HR

    if 'elapsed_time' in df.columns:
        df = df.rename(columns={'elapsed_time': 'elapsed_time_s'})
        df['elapsed_time_hr'] = df['elapsed_time_s'] * S_TO_HR

    if 'total_elevation_gain' in df.columns:
        df = df.rename(columns={'total_elevation_gain': 'total_elevation_gain_m'})
        df['elevation_gain_ft'] = df['total_elevation_gain_m'] * M_TO_FT

    if 'elev_high' in df.columns:
        df = df.rename(columns={'elev_high': 'elev_high_m'})
        df['elev_high_ft'] = df['elev_high_m'] * M_TO_FT

    if 'elev_low' in df.columns:
        df = df.rename(columns={'elev_low': 'elev_low_m'})
        df['elev_low_ft'] = df['elev_low_m'] * M_TO_FT

    return df

def activities_to_daily_counts(
    df: pd.DataFrame,
    date_col: str = "start_date_local",
) -> pd.DataFrame:
    work = df[[date_col]].copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=[date_col])

    work["date"] = work[date_col].dt.date

    daily = (
        work.groupby("date", as_index=False)
            .size()
            .rename(columns={"size": "activity_count"})
    )

    # build_month_day_grid expects a date-like column
    daily[date_col] = pd.to_datetime(daily["date"])
    return daily[[date_col, "activity_count"]]