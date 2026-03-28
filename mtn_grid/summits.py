import math
import pandas as pd
import geopandas as gpd
import polyline
from shapely.geometry import LineString


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
Take a polyline and return only peak IDs that are physically near it using GeoPandas dataframes.
"""

def find_candidate_peaks(encoded_polyline, peaks_gdf, buffer_meters=300):
    if not encoded_polyline or str(encoded_polyline) == 'nan':
        return []
    
    # 1. Decode to (lon, lat) for Shapely
    coords = polyline.decode(encoded_polyline)
    line = LineString([(lon, lat) for lat, lon in coords])
    
    # 2. Broad Phase (Fast): Envelope search
    # We use a rough degree estimate (0.005 is ~500m) just for the initial box search
    possible_matches_index = peaks_gdf.sindex.query(line.envelope.buffer(0.005), predicate="intersects")
    candidates = peaks_gdf.iloc[possible_matches_index].copy()
    
    if candidates.empty:
        return []

    # 3. Narrow Phase (The Fix): Project to Meters
    # EPSG:3857 is the "Web Mercator" used by Strava/Google. It uses meters.
    line_projected = gpd.GeoSeries([line], crs="EPSG:4326").to_crs(epsg=3857).iloc[0]
    candidates_projected = candidates.to_crs(epsg=3857)

    # 4. Precise Filter
    # Now .distance() returns actual meters!
    mask = candidates_projected.distance(line_projected) <= buffer_meters
    return candidates[mask]['peak_id'].tolist()

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

