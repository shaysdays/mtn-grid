import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import date
import sys

from mtn_grid.storage import load_processed_activities
from mtn_grid.summits import count_touches_debounced, find_candidate_peaks
from mtn_grid.cleaning import activities_to_daily_counts
from mtn_grid.peaks import load_peaks_as_gdf, PEAKS_CSV_PATH, PROCESSED_ACTIVITIES_PATH

# --- CONFIGURATION & LOOKUP TABLES ---
MONTH_LABELS = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

DAYS_IN_MONTH = {
    "Jan": 31, "Feb": 29, "Mar": 31, "Apr": 30,
    "May": 31, "Jun": 30, "Jul": 31, "Aug": 31,
    "Sep": 30, "Oct": 31, "Nov": 30, "Dec": 31,
}

# --- DATA TRANSFORMATION UTILITIES ---

def build_month_day_grid(df: pd.DataFrame, touches_col: str) -> pd.DataFrame:
    """
    Transforms activity records into a 12x31 matrix for heatmap visualization.
    Handles empty dataframes and missing date columns gracefully.
    """
    m_col = "_month" if "_month" in df.columns else "month"
    d_col = "_day" if "_day" in df.columns else "day"
    
    if df.empty:
        grid = pd.DataFrame(0, index=range(1, 13), columns=range(1, 32))
        grid.index = grid.index.map(MONTH_LABELS)
        grid.index.name = None
        grid.columns.name = None
        return grid

    if m_col not in df.columns:
        if "start_date_local" in df.columns:
            df = df.copy()
            df[m_col] = df["start_date_local"].dt.month
            df[d_col] = df["start_date_local"].dt.day
        else:
            raise KeyError(f"Missing date or month/day columns. Found: {df.columns.tolist()}")

    agg = df.groupby([m_col, d_col], as_index=False)[touches_col].sum()
    grid = agg.pivot(index=m_col, columns=d_col, values=touches_col)
    
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
    """
    Calculates summary metrics for a given activity grid, 
    accounting for varying days per month.
    """
    total_cells = 0
    completed_cells = 0
    total_touches = 0

    for month, row in grid.iterrows():
        max_day = DAYS_IN_MONTH[month]
        valid = row.iloc[:max_day]
        total_cells += max_day
        completed_cells += int((valid > 0).sum())
        total_touches += int(valid.sum())

    completion_pct = completed_cells / total_cells if total_cells > 0 else 0
    return total_cells, completed_cells, completion_pct, total_touches

def grid_to_long(grid: pd.DataFrame) -> pd.DataFrame:
    """
    Melts a wide-format grid into a long-format DataFrame compatible with Altair.
    """
    long = (
        grid.reset_index(names="month")
            .melt(id_vars="month", var_name="day", value_name="value")
    )
    long["day"] = long["day"].astype(int)
    long["max_day"] = long["month"].map(DAYS_IN_MONTH)
    long = long[long["day"] <= long["max_day"]].copy()
    return long

def get_label(r, peaks_df):
    """
    Constructs unique identifiers for peaks to prevent collisions 
    between mountains with identical names.
    """
    name = str(r["peak_name"]).strip()
    if len(peaks_df[peaks_df["peak_name"] == name]) > 1:
        return f"{name} ({r['peak_id']})"
    return name

# --- VISUALIZATION ENGINE ---

def bubble_heatmap(grid: pd.DataFrame, vmax: int | None = None, row_step: int = 35, label: str = "Value"):
    """
    Renders a custom Altair heatmap with rounded rects and conditional text overlays.
    """
    long = grid_to_long(grid).copy()
    long["value"] = long["value"].fillna(0).astype(int)

    if vmax is None:
        vmax = int(long["value"].max()) if len(long) else 1
    vmax = max(int(vmax), 1)

    months_domain = list(MONTH_LABELS.values())
    days_domain = [str(d) for d in range(1, 32)]
    long["day"] = long["day"].astype(str)

    base = alt.Chart(long).transform_calculate(
        pretty_date="datum.month + ' ' + datum.day" 
    ).encode(
        x=alt.X(
            "day:N",
            sort=days_domain,
            axis=alt.Axis(title=None, ticks=False, domain=False, labelAngle=0, labelFontSize=12),
            scale=alt.Scale(domain=days_domain, paddingInner=0.1),
        ),
        y=alt.Y(
            "month:N",
            sort=months_domain,
            axis=alt.Axis(title=None, ticks=False, domain=False, labelFontSize=12),
            scale=alt.Scale(domain=months_domain, paddingInner=0.1),
        ),
    )

    squares = base.mark_rect(cornerRadius=4).encode(
        color=alt.Color("value:Q", scale=alt.Scale(scheme="greens", domain=[0, vmax]), legend=None),
        opacity=alt.condition(alt.datum.value > 0, alt.value(1), alt.value(0.05)),
        tooltip=[
            alt.Tooltip("pretty_date:N", title="Date"), 
            alt.Tooltip("value:Q", title=label)
        ]
    )

    text = base.mark_text(fontSize=16, fontWeight=800).encode(
        text=alt.condition(alt.datum.value > 0, alt.Text("value:Q", format="d"), alt.value("")),
        color=alt.condition(
            alt.datum.value >= int(np.ceil(vmax * 0.6)),
            alt.value("white"),
            alt.value("black"),
            tooltip=alt.value(None)
        )
    )

    chart = (
        (squares + text)
        .properties(width="container", height=alt.Step(row_step))
        .configure_view(strokeOpacity=0)
        .configure_axis(grid=False)
    )

    st.altair_chart(chart, width="stretch")

# --- CACHED COMPUTATION ENGINE ---

@st.cache_data(show_spinner=True)
def load_and_compute(peaks_mtime: float, acts_mtime: float):
    """
    Primary data processing pipeline. Handles spatial joins and debounce logic 
    to detect valid summit touches from Strava polylines. 
    Cached based on file modification times.
    """
    peaks_gdf = load_peaks_as_gdf()
    activities = load_processed_activities()

    activities["start_date_local"] = pd.to_datetime(activities["start_date_local"], errors="coerce")
    activities = activities.dropna(subset=["start_date_local"])
    activities["_month"] = activities["start_date_local"].dt.month
    activities["_day"] = activities["start_date_local"].dt.day

    peaks_lookup = peaks_gdf.set_index('peak_id').to_dict('index')
    summited_data = {}

    for _, act in activities.iterrows():
        poly = act['map.summary_polyline']
        act_year = act['start_date_local'].year 
        candidate_ids = find_candidate_peaks(poly, peaks_gdf, buffer_meters=300)
        
        for pid in candidate_ids:
            p = peaks_lookup.get(pid)
            if not p: continue
            
            touches = count_touches_debounced(
                poly, p["latitude"], p["longitude"],
                enter_m=p["enter_m"], exit_m=p["exit_m"],
                exit_consec_points=p["exit_consec_points"],
            )
            
            if touches > 0:
                if pid not in summited_data:
                    summited_data[pid] = []
                summited_data[pid].append({
                    "_month": act["_month"], "_day": act["_day"],  "_year": act_year, "touches": touches
                })

    grids = {}
    peak_stats = {}
    for pid, records in summited_data.items():
        peak_hits_df = pd.DataFrame(records)
        grid = build_month_day_grid(peak_hits_df, "touches")
        grids[pid] = grid
        peak_stats[pid] = grid_stats(grid)

    return activities, peaks_gdf, summited_data

# --- APP INITIALIZATION ---

st.set_page_config(page_title="🏔️ MTN GRID", layout="wide")
st.title("🏔️ MTN GRID")
st.subheader("Shay Subramanian")
st.markdown(
    """
    <p style="font-size:20px; color:#4B5563; margin-top:-10px;">
        A spatial analytics engine that detects summit touches from Strava polylines
        and visualizes year-long mountain activity grids.
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown("""
    <style>
    [data-baseweb="tag"] { background-color: #f3f4f6 !important; color: #111827 !important; border: 1px solid #d1d5db !important; }
    [data-baseweb="tag"] * { color: #111827 !important; }
    </style>
    """, unsafe_allow_html=True)

peaks_mtime = PEAKS_CSV_PATH.stat().st_mtime
acts_mtime = PROCESSED_ACTIVITIES_PATH.stat().st_mtime

with st.spinner("Loading activities and computing grids..."):
    df, peaks, summited_data = load_and_compute(peaks_mtime, acts_mtime)

id_to_row = {str(r["peak_id"]): r for _, r in peaks.iterrows()}

# --- UI INTERACTION CALLBACKS ---

def sort_years():
    years = list(st.session_state.selected_years_key)
    years.sort(reverse=True)
    st.session_state.selected_years_key = years

def sort_types():
    types = list(st.session_state.selected_types_key)
    types.sort()
    st.session_state.selected_types_key = types

def sort_states():
    states = list(st.session_state.selected_states_key)
    states.sort()
    st.session_state.selected_states_key = states

def sort_peaks(state_key):
    peaks_list = list(st.session_state[state_key])
    peaks_list.sort()
    st.session_state[state_key] = peaks_list

# --- SIDEBAR CONTROL PANEL ---

with st.sidebar:
    st.title("Global Filters")
    
    if st.button("Reset", width="stretch"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.divider()

    available_years = sorted(df['start_date_local'].dt.year.unique().tolist(), reverse=True)
    if 'selected_years_key' not in st.session_state:
        st.session_state.selected_years_key = available_years

    with st.expander("Years", expanded=False):
        st.multiselect(
            "Select Years", 
            options=available_years, 
            key="selected_years_key",
            on_change=sort_years,
            label_visibility="collapsed"
        )
    
    selected_years = st.session_state.selected_years_key
    if not selected_years:
        st.warning("Select at least one year.")
        st.stop()
    
    df = df[df['start_date_local'].dt.year.isin(selected_years)].copy()
    
    states = sorted(peaks["state"].dropna().astype(str).unique().tolist())
    summited_states = sorted(peaks[peaks["peak_id"].isin(summited_data.keys())]["state"].unique().tolist())
    
    if 'selected_states_key' not in st.session_state:
        st.session_state.selected_states_key = summited_states

    with st.expander("States", expanded=False):
        st.multiselect(
            "Select States", 
            options=states, 
            key="selected_states_key",
            on_change=sort_states,
            label_visibility="collapsed"
        )
    selected_states = st.session_state.selected_states_key

    st.divider()

    state_peak_map = {}
    if selected_states:
        st.caption("Specific Peak Selection")

        min_summits = st.slider(
            "Summit Threshold",
            min_value=1,
            max_value=20,
            value=1,
            help="Only show peaks with at least this many total recorded summits."
        )

        for state in sorted(selected_states):
            with st.expander(f"{state}", expanded=False):
                peaks_state = peaks[peaks["state"] == state].copy()
                peaks_state["label"] = peaks_state.apply(lambda r: get_label(r, peaks_state), axis=1)
                labels = sorted(peaks_state["label"].tolist()) 
                label_to_id = dict(zip(peaks_state["label"], peaks_state["peak_id"].astype(str)))
                
                state_key = f"sidebar_peaks_selected__{state}"
                if state_key not in st.session_state:
                    st.session_state[state_key] = sorted([lbl for lbl in labels if label_to_id[lbl] in summited_data])
                
                st.multiselect(
                    f"Pick {state} peaks", 
                    options=labels, 
                    key=state_key, 
                    on_change=sort_peaks,
                    args=(state_key,),
                    label_visibility="collapsed"
                )
                
                state_peak_map[state] = sorted([
                    label_to_id[lbl] for lbl in st.session_state[state_key] 
                    if sum(rec['touches'] for rec in summited_data.get(label_to_id[lbl], [])) >= min_summits
                ])

# --- MAIN DASHBOARD: OVERALL ACTIVITY ---

st.subheader("Overall Activity")

if 'sport_type_clean' in df.columns:
    available_types = sorted(df['sport_type_clean'].unique().tolist())
    
    if 'selected_types_key' not in st.session_state:
        st.session_state.selected_types_key = available_types

    st.multiselect(
        "Select Types",
        options=available_types, 
        key="selected_types_key",
        on_change=sort_types,
        label_visibility="visible",
        help="Filter the overall grid by activity category (Run, Cycle, Gym, etc.)."
    )
    
    df_filtered = df[df['sport_type_clean'].isin(st.session_state.selected_types_key)]
else:
    df_filtered = df.copy()

daily = activities_to_daily_counts(df_filtered)
overall_grid = build_month_day_grid(daily, touches_col="activity_count")
total_cells, active_days, pct, total_activities = grid_stats(overall_grid)

st.caption(f"Total activities: {total_activities} | Active days: {active_days}/{total_cells} ({pct:.1%})")

overall_vmax = int(overall_grid.to_numpy().max()) if overall_grid.size else 1
bubble_heatmap(overall_grid, vmax=overall_vmax, row_step=40, label="Activities")

# --- HISTORICAL TIMELINE BAR CHART ---

year = date.today().year
date_range = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31")
chart_df = pd.DataFrame({"Date": date_range})

def get_count(row):
    m_name = row["Date"].strftime("%b")
    d_num = row["Date"].day
    try: return overall_grid.loc[m_name, d_num]
    except KeyError: return 0

chart_df["Activities"] = chart_df.apply(get_count, axis=1)

timeline_chart = (
    alt.Chart(chart_df).mark_bar(size=4, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("Date:T", axis=alt.Axis(format="%b", labelFlush=False, grid=False, labelColor="gray", tickCount="month"), title=None),
        y=alt.Y("Activities:Q", axis=None),
        color=alt.Color("Activities:Q", scale=alt.Scale(scheme="greens", domain=[0, overall_vmax]), legend=None),
        tooltip=[alt.Tooltip("Date:T", title="Date", format="%B %e"), alt.Tooltip("Activities:Q", title="Activities")]
    ).properties(height=150).configure_view(strokeOpacity=0)
)
st.altair_chart(timeline_chart, width="stretch")
st.divider()

# --- MAIN DASHBOARD: PEAK-SPECIFIC GRIDS ---

st.subheader(
    "Peak Grids", 
    help="Detection based on GNIS database cross-referencing."
)

for state, selected_ids in state_peak_map.items():
    if not selected_ids:
        continue
        
    with st.expander(f"{state}", expanded=True):
        ranked = []
        for pid in selected_ids:
            recs = summited_data.get(pid, [])
            year_recs = [r for r in recs if r["_year"] in selected_years]
            
            all_time_touches = sum(r["touches"] for r in recs)
            year_touches = sum(r["touches"] for r in year_recs)
            
            ranked.append((year_touches, all_time_touches, pid, year_recs, recs))
        
        ranked.sort(key=lambda x: x[0], reverse=True)

        for year_touches, all_touches, pid, year_recs, all_recs in ranked:
            r = id_to_row[pid]
            
            peak_hits_df = pd.DataFrame(year_recs)
            grid = build_month_day_grid(peak_hits_df, "touches")
            _, year_completed, year_pct, _ = grid_stats(grid)

            all_hits_df = pd.DataFrame(all_recs)
            all_grid = build_month_day_grid(all_hits_df, "touches")
            total_cells, all_completed, all_pct, _ = grid_stats(all_grid)

            st.markdown(f"### {r['peak_name']}")
            st.caption(f"📍 [{r['latitude']:.5f}, {r['longitude']:.5f}](https://www.google.com/maps/search/?api=1&query={r['latitude']},{r['longitude']})")
            
            st.caption(f"**All Time:** {all_touches} Summits | Days completed: {all_completed}/{total_cells} ({all_pct:.1%})")
            
            year_display_label = "All Years" if len(selected_years) == len(available_years) else ", ".join(map(str, sorted(selected_years)))
            st.caption(f"**Selected ({year_display_label}):** {year_touches} Summits | Days completed: {year_completed}/{total_cells} ({year_pct:.1%})")
            
            if year_touches > 0:
                local_vmax = int(grid.to_numpy().max()) if grid.size else 1
                bubble_heatmap(grid, vmax=local_vmax, row_step=35, label="Summits")
            else:
                st.info(f"No summits recorded for {r['peak_name']} in the selected years.")
            
            st.divider()