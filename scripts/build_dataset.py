from strava_lab.storage import load_raw_activities, save_processed_activities
from strava_lab.cleaning import normalize_activities

if __name__ == '__main__':
    activities = load_raw_activities()
    df = normalize_activities(activities)
    save_processed_activities(df)
    print(f'Saved {len(df)} rows to data/processed/activities.parquet')