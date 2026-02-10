from mtn_grid.strava_api import fetch_activities
from mtn_grid.storage import save_raw_activities

if __name__ == '__main__':
    activities = fetch_activities()
    save_raw_activities(activities)
    print(f'Saved {len(activities)} activities to data/raw/activities.json')
    