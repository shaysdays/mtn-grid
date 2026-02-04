import time
import requests
from dotenv import set_key
from .config import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN, ENV_PATH

TOKEN_URL = 'https://www.strava.com/oauth/token'
ACTIVITIES_URL = 'https://www.strava.com/api/v3/athlete/activities'

# internal mutable copy
_refresh_token = STRAVA_REFRESH_TOKEN  

def get_access_token() -> str:
    #Refresh Strava access token; persist rotated refresh token to .env safely.
    global _refresh_token

    payload = {
        'client_id': STRAVA_CLIENT_ID,
        'client_secret': STRAVA_CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': _refresh_token,
    }

    r = requests.post(TOKEN_URL, data=payload)
    if r.status_code != 200:
        raise RuntimeError(f'Token refresh failed: {r.json()}')

    data = r.json()
    access_token = data['access_token']
    new_refresh_token = data['refresh_token']

    if new_refresh_token != _refresh_token:
        set_key(str(ENV_PATH), 'STRAVA_REFRESH_TOKEN', new_refresh_token)
        _refresh_token = new_refresh_token

    return access_token


def fetch_activities(per_page: int = 200, sleep_s: float = 1.0) -> list[dict]:
    # Fetch ALL athlete activities available via paging.
    access_token = get_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}

    activities = []
    page = 1

    while True:
        r = requests.get(
            ACTIVITIES_URL,
            headers=headers,
            params={'per_page': per_page, 'page': page},
        )

        if r.status_code != 200:
            raise RuntimeError(f'Fetch activities failed: {r.json()}')

        batch = r.json()
        if not batch:
            break

        activities.extend(batch)
        page += 1
        time.sleep(sleep_s)

    return activities