# streamlit_app.py
import streamlit as st
import pandas as pd

from strava_lab.storage import load_processed_activities
from strava_lab.summits import add_summit_metrics

# Establish month labels
MONTH_LABELS = {
    1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
    5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug',
    9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec',
}

def heatmap_table(df: pd.DataFrame) -> 'pd.io.formats.style.Styler':
    vmax = int(df.to_numpy().max()) if df.size else 0
    vmax = max(vmax, 1)

    return (
        df.style
          .format('{:d}')
          .background_gradient(axis=None, vmin=0, vmax=vmax, cmap='Greens')
    )

"""
Build grid dataframe to be used in Streamlit. This will take in the Strava data, group by month/day,
pivot to use months as rows and days as cols, and output a completed grid.
"""

def build_month_day_grid(
    df: pd.DataFrame,
    touches_col: str,
    date_col: str = 'start_date_local',
) -> pd.DataFrame:
    work = df[[date_col, touches_col]].copy()
    work[date_col] = pd.to_datetime(work[date_col], errors='coerce')
    work = work.dropna(subset=[date_col])

    work['month'] = work[date_col].dt.month
    work['day'] = work[date_col].dt.day

    work = work[work[touches_col] > 0]

    agg = (
        work.groupby(['month', 'day'], as_index=False)[touches_col]
        .sum()
    )

    # months on rows, days on columns
    grid = agg.pivot(index='month', columns='day', values=touches_col)

    # force full 12x31 shape
    grid = (
        grid
        .reindex(index=range(1, 13), columns=range(1, 32))
        .fillna(0)
        .astype(int)
    )

    # rename month numbers to labels on the INDEX (not columns)
    grid.index = grid.index.map(MONTH_LABELS)

    grid.index.name = None
    grid.columns.name = None
    return grid

"""
Load data, add cols for peaks, and output the altered base data and grid dataframes.
"""

@st.cache_data(show_spinner=True)
def load_and_compute():
    df = load_processed_activities()

    # Add summit columns (touch count + boolean)
    df = add_summit_metrics(df, 'sanitas', 40.0344166667, -105.30525)
    df = add_summit_metrics(df, 'green', 39.98215812792686, -105.30158524126522)

    sanitas_grid = build_month_day_grid(df, 'sanitas_touches')
    green_grid = build_month_day_grid(df, 'green_touches')

    return df, sanitas_grid, green_grid

"""
Create Streamlit dashboard.
"""

st.set_page_config(page_title='Summit Grids', layout='wide')
st.title('Summit Grids')

with st.spinner('Loading activities and computing grids…'):
    df, sanitas_grid, green_grid = load_and_compute()

peak = st.selectbox('Peak', ['Mt. Sanitas', 'Green Mountain', 'Both'], index=2)

def grid_stats(grid: pd.DataFrame):
    total_cells = grid.shape[0] * grid.shape[1]
    completed_cells = int((grid.values > 0).sum())
    completion_pct = completed_cells / total_cells
    total_touches = int(grid.values.sum())
    return total_cells, completed_cells, completion_pct, total_touches

if peak in ('Mt. Sanitas', 'Both'):
    st.subheader('Mt. Sanitas')
    total_cells, completed, pct, touches = grid_stats(sanitas_grid)
    st.caption(
        f'Days completed: {completed}/{total_cells} '
        f'({pct:.1%}) • Total summits: {touches}'
    )
    st.table(heatmap_table(sanitas_grid))

    st.divider()  # visual separation

if peak in ('Green Mountain', 'Both'):
    st.subheader('Green Mountain')
    total_cells, completed, pct, touches = grid_stats(green_grid)
    st.caption(
        f'Days completed: {completed}/{total_cells} '
        f'({pct:.1%}) • Total summits: {touches}'
    )
    st.table(heatmap_table(green_grid))

