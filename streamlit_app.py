# streamlit_app.py
import streamlit as st
import pandas as pd

from strava_lab.storage import load_processed_activities
from strava_lab.summits import add_summit_metrics

# We'll create this function in Phase A (or you can inline pivot logic for now)
# from strava_lab.grids import build_month_day_grid

MONTH_LABELS = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

def heatmap_table(df: pd.DataFrame) -> "pd.io.formats.style.Styler":
    # If your max is large, heatmaps can look “all dark”.
    # This keeps it readable and formats as ints.
    vmax = int(df.to_numpy().max()) if df.size else 0
    vmax = max(vmax, 1)

    return (
        df.style
          .format("{:d}")
          .background_gradient(axis=None, vmin=0, vmax=vmax, cmap="Greens")
    )

def build_month_day_grid(df: pd.DataFrame, touches_col: str, date_col="start_date_local") -> pd.DataFrame:
    work = df[[date_col, touches_col]].copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=[date_col])
    work["month"] = work[date_col].dt.month
    work["day"] = work[date_col].dt.day

    work = work[work[touches_col] > 0]

    agg = (
        work.groupby(["day", "month"], as_index=False)[touches_col]
        .sum()
    )
    grid = agg.pivot(index="month", columns="day", values=touches_col)
    grid = grid.reindex(index=range(1, 13), columns=range(1, 32)).fillna(0).astype(int)
    grid = grid.rename(columns=MONTH_LABELS)
    grid.index.name = None
    grid.columns.name = None
    return grid

@st.cache_data(show_spinner=True)
def load_and_compute():
    df = load_processed_activities()

    # Add summit columns (touch count + boolean)
    df = add_summit_metrics(df, "sanitas", 40.0344166667, -105.30525)
    df = add_summit_metrics(df, "green", 39.98215812792686, -105.30158524126522)

    sanitas_grid = build_month_day_grid(df, "sanitas_touches")
    green_grid = build_month_day_grid(df, "green_touches")

    return df, sanitas_grid, green_grid


st.set_page_config(page_title="Summit Grids", layout="wide")
st.title("Summit Grids")

with st.spinner("Loading activities and computing grids…"):
    df, sanitas_grid, green_grid = load_and_compute()

peak = st.selectbox("Peak", ["Mt. Sanitas", "Green Mountain", "Both"], index=2)

def grid_stats(grid: pd.DataFrame):
    total_cells = grid.shape[0] * grid.shape[1]
    completed_cells = int((grid.values > 0).sum())
    completion_pct = completed_cells / total_cells
    total_touches = int(grid.values.sum())
    return total_cells, completed_cells, completion_pct, total_touches

if peak in ("Sanitas", "Both"):
    st.subheader("Mt. Sanitas")
    total_cells, completed, pct, touches = grid_stats(sanitas_grid)
    st.caption(
        f"Days completed: {completed}/{total_cells} "
        f"({pct:.1%}) • Total summits: {touches}"
    )
    st.table(heatmap_table(sanitas_grid))

    st.divider()  # visual separation

if peak in ("Green", "Both"):
    st.subheader("Green Mountain")
    total_cells, completed, pct, touches = grid_stats(green_grid)
    st.caption(
        f"Days completed: {completed}/{total_cells} "
        f"({pct:.1%}) • Total summits: {touches}"
    )
    st.table(heatmap_table(green_grid))

