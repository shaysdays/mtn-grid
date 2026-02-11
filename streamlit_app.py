import streamlit as st
import pandas as pd
import numpy as np

from mtn_grid.storage import load_processed_activities
from mtn_grid.summits import count_touches_debounced, find_candidate_peaks
from mtn_grid.cleaning import activities_to_daily_counts
from mtn_grid.peaks import load_peaks_as_gdf, PEAKS_CSV_PATH, PROCESSED_ACTIVITIES_PATH

MONTH_LABELS = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

DAYS_IN_MONTH = {
    "Jan": 31,
    "Feb": 29,
    "Mar": 31,
    "Apr": 30,
    "May": 31,
    "Jun": 30,
    "Jul": 31,
    "Aug": 31,
    "Sep": 30,
    "Oct": 31,
    "Nov": 30,
    "Dec": 31,
}


def heatmap_table(df: pd.DataFrame, vmax: int) -> "pd.io.formats.style.Styler":
    vmax = max(int(vmax), 1)
    return (
        df.style
        .format("{:d}")
        .background_gradient(axis=None, vmin=0, vmax=vmax, cmap="Greens")
    )


def build_month_day_grid(df: pd.DataFrame, touches_col: str) -> pd.DataFrame:
    """
    Builds a 12x31 grid. Dynamically handles underscored or standard column names.
    """
    # 1. Identify which columns are actually in this specific dataframe
    m_col = "_month" if "_month" in df.columns else "month"
    d_col = "_day" if "_day" in df.columns else "day"
    
    # 2. Fallback: If neither exist, try to generate them from a timestamp column
    if m_col not in df.columns:
        if "start_date_local" in df.columns:
            df = df.copy()
            df[m_col] = df["start_date_local"].dt.month
            df[d_col] = df["start_date_local"].dt.day
        else:
            raise KeyError(f"Missing date or month/day columns. Found: {df.columns.tolist()}")

    # 3. Aggregate - Sum touches by date
    agg = df.groupby([m_col, d_col], as_index=False)[touches_col].sum()
    
    # 4. Pivot - USE THE DYNAMIC NAMES HERE (The fix for your error)
    grid = agg.pivot(index=m_col, columns=d_col, values=touches_col)
    
    # 5. Reindex to 12x31 and clean up labels
    grid = (
        grid
        .reindex(index=range(1, 13), columns=range(1, 32))
        .fillna(0)
        .astype(int)
    )
    
    grid.index = grid.index.map(MONTH_LABELS)
    grid.index.name = None
    grid.columns.name = None
    return grid

def grid_stats(grid: pd.DataFrame):
    total_cells = 0
    completed_cells = 0
    total_touches = 0

    for month, row in grid.iterrows():
        max_day = DAYS_IN_MONTH[month]
        valid = row.iloc[:max_day]
        total_cells += max_day
        completed_cells += int((valid > 0).sum())
        total_touches += int(valid.sum())

    completion_pct = completed_cells / total_cells
    return total_cells, completed_cells, completion_pct, total_touches

@st.cache_data(show_spinner=True)
def load_and_compute(peaks_mtime: float, acts_mtime: float):
    # 1. Load data
    peaks_gdf = load_peaks_as_gdf()
    activities = load_processed_activities()

    # 2. Standardize Activity Columns immediately
    # Doing this here once prevents logic errors in all downstream functions
    activities["start_date_local"] = pd.to_datetime(activities["start_date_local"], errors="coerce")
    activities = activities.dropna(subset=["start_date_local"])
    activities["_month"] = activities["start_date_local"].dt.month
    activities["_day"] = activities["start_date_local"].dt.day

    # 3. Create O(1) Lookup for Peak Metadata
    peaks_lookup = peaks_gdf.set_index('peak_id').to_dict('index')

    # 4. Detection Engine
    summited_data = {}

    for _, act in activities.iterrows():
        poly = act['map.summary_polyline']
        
        # Broad Phase Filter
        candidate_ids = find_candidate_peaks(poly, peaks_gdf, buffer_meters=300)
        
        for pid in candidate_ids:
            p = peaks_lookup.get(pid)
            if not p: continue
            
            # Narrow Phase (Precise check)
            touches = count_touches_debounced(
                poly, 
                p["latitude"], 
                p["longitude"],
                enter_m=p["enter_m"],
                exit_m=p["exit_m"],
                exit_consec_points=p["exit_consec_points"],
            )
            
            if touches > 0:
                if pid not in summited_data:
                    summited_data[pid] = []
                
                # Pass the exact same columns build_month_day_grid expects
                summited_data[pid].append({
                    "_month": act["_month"],
                    "_day": act["_day"],
                    "touches": touches
                })

    # 5. Build Final Objects
    grids = {}
    peak_stats = {}

    for pid, records in summited_data.items():
        peak_hits_df = pd.DataFrame(records)
        grid = build_month_day_grid(peak_hits_df, "touches")
        grids[pid] = grid
        peak_stats[pid] = grid_stats(grid)

    return activities, peaks_gdf, grids, peak_stats

st.set_page_config(page_title="MTN GRID", layout="wide")
st.title("MTN GRID")
st.subheader("Shay Subramanian")

st.divider()

# --- Custom Styling for Tags ---
st.markdown(
    """
    <style>
    [data-baseweb="tag"] { background-color: #f3f4f6 !important; color: #111827 !important; border: 1px solid #d1d5db !important; }
    [data-baseweb="tag"] * { color: #111827 !important; }
    [data-baseweb="tag"] svg { fill: #6b7280 !important; }
    [data-baseweb="tag"]:hover { background-color: #e5e7eb !important; border-color: #cbd5e1 !important; }
    [role="option"][aria-selected="true"] { background-color: #e5e7eb !important; color: #111827 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Data Loading ---
peaks_mtime = PEAKS_CSV_PATH.stat().st_mtime
acts_mtime = PROCESSED_ACTIVITIES_PATH.stat().st_mtime

with st.spinner("Loading activities and computing grids..."):
    # load_and_compute returns the processed data based on the spatial index
    df, peaks, grids, peak_stats = load_and_compute(peaks_mtime, acts_mtime)

# --- Overall Activity Heatmap ---
daily = activities_to_daily_counts(df)
overall_grid = build_month_day_grid(daily, touches_col="activity_count")

st.subheader("Overall Activity")
total_cells, active_days, pct, total_activities = grid_stats(overall_grid)
st.caption(f"Total activities: {total_activities} | Active days: {active_days}/{total_cells} ({pct:.1%})")

overall_vmax = int(np.ceil(np.quantile(overall_grid.to_numpy().ravel(), 0.95))) if overall_grid.size else 1
st.table(heatmap_table(overall_grid, vmax=max(overall_vmax, 1)))
st.divider()

# --- State & Peak Selection ---
if "state" not in peaks.columns:
    peaks = peaks.copy()
    peaks["state"] = "Unknown"

# Fast lookup for rendering
id_to_row = {str(r["peak_id"]): r for _, r in peaks.iterrows()}
states = sorted(peaks["state"].dropna().astype(str).unique().tolist())

# Default to only states where you have actually summited something
summited_states = sorted(peaks[peaks["peak_id"].isin(grids.keys())]["state"].unique().tolist())
selected_states = st.multiselect("Select States", options=states, default=summited_states)

if not selected_states:
    st.info("Select at least one state to see peaks.")
else:
    # 1. Broad Phase: Calculate Global Vmax across ALL selected peaks for consistent coloring
    all_selected_ids = []
    state_peak_map = {} # To store selected IDs per state for the rendering phase

    for state in selected_states:
        peaks_state = peaks[peaks["state"].astype(str) == str(state)].copy()
        
        # Build unique labels
        def get_label(r):
            name = str(r["peak_name"]).strip()
            return name if len(peaks_state[peaks_state["peak_name"] == name]) == 1 else f"{name} ({r['peak_id']})"
        
        peaks_state["label"] = peaks_state.apply(get_label, axis=1)
        labels = peaks_state["label"].tolist()
        label_to_id = dict(zip(peaks_state["label"], peaks_state["peak_id"].astype(str)))

        # Logic for pre-selecting only summited peaks
        summited_labels_only = [lbl for lbl in labels if label_to_id[lbl] in grids]
        state_key = f"peaks_selected__{state}"

        if state_key not in st.session_state:
            st.session_state[state_key] = summited_labels_only
        
        # We need to peek at what's in session state to calculate vmax before rendering
        current_selection = st.session_state.get(state_key, summited_labels_only)
        current_ids = [label_to_id[lbl] for lbl in current_selection if lbl in label_to_id]
        all_selected_ids.extend(current_ids)
        
        # Store metadata for the second loop
        state_peak_map[state] = {
            "labels": labels,
            "label_to_id": label_to_id,
            "state_key": state_key
        }

    # Calculate global_vmax
    if all_selected_ids:
        valid_vals = [grids[pid].to_numpy().ravel() for pid in all_selected_ids if pid in grids]
        if valid_vals:
            vals = np.concatenate(valid_vals)
            vals = vals[vals > 0]
            global_vmax = max(int(np.ceil(np.quantile(vals, 0.95))), 1) if vals.size else 1
        else:
            global_vmax = 1
    else:
        global_vmax = 1

    # 2. Narrow Phase: Rendering (Nested inside Expanders)
    for state in selected_states:
        meta = state_peak_map[state]
        
        with st.expander(f"{state}", expanded=True):
            # If the key is already in session_state, Streamlit ignores 'default'.
            # We only provide a 'default' if the key isn't in session_state yet.
            if meta["state_key"] not in st.session_state:
                st.session_state[meta["state_key"]] = summited_labels_only # your logic from earlier
            
            selected_peak_labels = st.multiselect(
                f"Peaks in {state}",
                options=meta["labels"],
                key=meta["state_key"]
                # Note: 'default' is removed here because session_state handles it
            )

            selected_ids = [meta["label_to_id"][lbl] for lbl in selected_peak_labels]

            if not selected_ids:
                st.info(f"No peaks selected for {state}.")
                continue

            # Rank selected peaks (Summited peaks first, then by completion %)
            ranked = []
            for pid in selected_ids:
                stats = peak_stats.get(pid, (365, 0, 0.0, 0))
                ranked.append((stats, pid))
            
            # Sort by completion percentage (index 2 of the stats tuple)
            ranked.sort(key=lambda x: x[0][2], reverse=True)

            # Display the Heatmaps
            for stats, pid in ranked:
                total_cells, completed, pct, touches = stats
                r = id_to_row[pid]
                grid = grids.get(pid)
                
                if grid is None:
                    # Create blank grid for unsummited peaks on the fly
                    grid = pd.DataFrame(0, index=range(1, 13), columns=range(1, 32))
                    grid.index = grid.index.map(MONTH_LABELS)

                google_maps_url = f"https://www.google.com/maps/search/?api=1&query={r['latitude']},{r['longitude']}"

                st.markdown(f"### {r['peak_name']}")
                st.caption(f"📍 [{r['latitude']:.5f}, {r['longitude']:.5f}]({google_maps_url})")
                st.caption(f"Total summits: {touches} | Days completed: {completed}/{total_cells} ({pct:.1%})")
                st.table(heatmap_table(grid, vmax=global_vmax))
                st.divider()