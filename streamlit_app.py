import streamlit as st
import pandas as pd
import numpy as np

from strava_lab.storage import load_processed_activities
from strava_lab.summits import add_summit_metrics
from strava_lab.cleaning import activities_to_daily_counts
from strava_lab.peaks import load_peaks, PEAKS_CSV_PATH, PROCESSED_ACTIVITIES_PATH

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


def build_month_day_grid(
    df: pd.DataFrame,
    touches_col: str,
    date_col: str = "start_date_local",
) -> pd.DataFrame:
    if "_month" in df.columns and "_day" in df.columns:
        work = df[["_month", "_day", touches_col]].copy()
        work = work.dropna(subset=["_month", "_day"])
        work["_month"] = work["_month"].astype(int)
        work["_day"] = work["_day"].astype(int)
        month_col = "_month"
        day_col = "_day"
    else:
        work = df[[date_col, touches_col]].copy()
        work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
        work = work.dropna(subset=[date_col])
        work["month"] = work[date_col].dt.month
        work["day"] = work[date_col].dt.day
        month_col = "month"
        day_col = "day"

    work = work[work[touches_col] > 0]

    agg = work.groupby([month_col, day_col], as_index=False)[touches_col].sum()

    grid = agg.pivot(index=month_col, columns=day_col, values=touches_col)

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
    df = load_processed_activities()

    df["start_date_local"] = pd.to_datetime(df["start_date_local"], errors="coerce")
    df = df.dropna(subset=["start_date_local"])
    df["_month"] = df["start_date_local"].dt.month
    df["_day"] = df["start_date_local"].dt.day

    peaks = load_peaks()

    grids: dict[str, pd.DataFrame] = {}

    for _, p in peaks.iterrows():
        pid = str(p["peak_id"])
        df = add_summit_metrics(
            df,
            pid,
            float(p["latitude"]),
            float(p["longitude"]),
            enter_m=int(p["enter_m"]),
            exit_m=int(p["exit_m"]),
            exit_consec_points=int(p["exit_consec_points"]),
        )
        grids[pid] = build_month_day_grid(df, f"{pid}_touches")

    peak_stats: dict[str, tuple[int, int, float, int]] = {
        pid: grid_stats(grid) for pid, grid in grids.items()
    }

    return df, peaks, grids, peak_stats


st.set_page_config(page_title="Summit Grids", layout="wide")
st.title("Summit Grids")
st.subheader("Shay Subramanian")

st.divider()

st.markdown(
    """
    <style>
    [data-baseweb="tag"] {
        background-color: #f3f4f6 !important;
        color: #111827 !important;
        border: 1px solid #d1d5db !important;
    }
    [data-baseweb="tag"] * {
        color: #111827 !important;
    }
    [data-baseweb="tag"] svg {
        fill: #6b7280 !important;
    }
    [data-baseweb="tag"]:hover {
        background-color: #e5e7eb !important;
        border-color: #cbd5e1 !important;
    }
    [role="option"][aria-selected="true"] {
        background-color: #e5e7eb !important;
        color: #111827 !important;
    }
    [role="option"][aria-selected="true"] * {
        color: #111827 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

peaks_mtime = PEAKS_CSV_PATH.stat().st_mtime
acts_mtime = PROCESSED_ACTIVITIES_PATH.stat().st_mtime

with st.spinner("Loading activities and computing grids…"):
    df, peaks, grids, peak_stats = load_and_compute(peaks_mtime, acts_mtime)

daily = activities_to_daily_counts(df)
overall_grid = build_month_day_grid(daily, touches_col="activity_count")

st.subheader("Overall Activity")
total_cells, active_days, pct, total_activities = grid_stats(overall_grid)
st.caption(f"Total activities: {total_activities}")
st.caption(f"Active days: {active_days}/{total_cells} ({pct:.1%})")

overall_vmax = int(np.ceil(np.quantile(overall_grid.to_numpy().ravel(), 0.95))) if overall_grid.size else 1
overall_vmax = max(overall_vmax, 1)

st.table(heatmap_table(overall_grid, vmax=overall_vmax))
st.divider()

if "state" not in peaks.columns:
    peaks = peaks.copy()
    peaks["state"] = "Unknown"

id_to_row = {str(r["peak_id"]): r for _, r in peaks.iterrows()}

states = sorted(peaks["state"].dropna().astype(str).unique().tolist())
selected_states = st.multiselect("State", options=states, default=states)

if not selected_states:
    st.info("Select at least one state to see peaks.")
else:
    state_payload = {}
    all_selected_ids = []

    for state in selected_states:
        peaks_state = peaks[peaks["state"].astype(str) == str(state)].copy()

        def peak_label_in_state(r) -> str:
            return str(r["peak_name"]).strip()

        labels = [peak_label_in_state(r) for _, r in peaks_state.iterrows()]

        if len(set(labels)) != len(labels):
            def peak_label_in_state(r) -> str:
                return f"{str(r['peak_name']).strip()} — {str(r['peak_id'])}"
            labels = [peak_label_in_state(r) for _, r in peaks_state.iterrows()]

        label_to_id = {peak_label_in_state(r): str(r["peak_id"]) for _, r in peaks_state.iterrows()}

        state_key = f"peaks_selected__{state}"

        default_labels = []
        for lbl in labels:
            pid = label_to_id[lbl]
            stats = peak_stats.get(pid)
            if not stats:
                continue
            _, _, _, touches = stats
            if touches > 0:
                default_labels.append(lbl)

        if not default_labels:
            default_labels = labels

        if state_key not in st.session_state:
            st.session_state[state_key] = default_labels
        else:
            st.session_state[state_key] = [x for x in st.session_state[state_key] if x in labels]
            if not st.session_state[state_key]:
                st.session_state[state_key] = default_labels

        selected_peak_labels = st.session_state[state_key]
        selected_ids = [label_to_id[lbl] for lbl in selected_peak_labels] if selected_peak_labels else []

        state_payload[state] = {
            "labels": labels,
            "label_to_id": label_to_id,
            "state_key": state_key,
            "selected_ids": selected_ids,
        }

        all_selected_ids.extend(selected_ids)

    if all_selected_ids:
        vals = np.concatenate([grids[pid].to_numpy().ravel() for pid in all_selected_ids])
        vals = vals[vals > 0]
        global_vmax = int(np.ceil(np.quantile(vals, 0.95))) if vals.size else 1
        global_vmax = max(global_vmax, 1)
    else:
        global_vmax = 1

    for state in selected_states:
        payload = state_payload[state]
        labels = payload["labels"]
        label_to_id = payload["label_to_id"]
        state_key = payload["state_key"]

        with st.expander(f"{state}", expanded=True):
            selected_peak_labels = st.multiselect(
                "Peaks",
                options=labels,
                key=state_key,
                disabled=(len(labels) == 0),
            )

            selected_ids = [label_to_id[lbl] for lbl in selected_peak_labels] if selected_peak_labels else []

            if not selected_ids:
                st.info("Select at least one peak.")
                continue

            ranked = []
            for pid in selected_ids:
                total_cells, completed, pct, touches = peak_stats[pid]
                ranked.append((pct, pid, total_cells, completed, touches))

            ranked.sort(reverse=True, key=lambda x: x[0])

            for pct, pid, total_cells, completed, touches in ranked:
                r = id_to_row[pid]
                grid = grids[pid]

                st.markdown(f"### {r['peak_name']}")
                st.caption(f"Total summits: {touches}")
                st.caption(f"Days completed: {completed}/{total_cells} ({pct:.1%})")
                st.table(heatmap_table(grid, vmax=global_vmax))
                st.divider()