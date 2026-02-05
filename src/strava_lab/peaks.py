from __future__ import annotations

from pathlib import Path
import pandas as pd

from .config import PROJECT_ROOT

PEAKS_CSV_PATH = PROJECT_ROOT / 'data' / 'peaks.csv'

REQUIRED_COLS = {
    'peak_id',
    'peak_name',
    'latitude',
    'longitude',
    'enter_m',
    'exit_m',
    'exit_consec_points',
}

def load_peaks(path: Path = PEAKS_CSV_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f'Peaks file not found: {path}')

    # peak_id should be a STRING even if it looks numeric
    peaks = pd.read_csv(path, dtype={'peak_id': 'string'})

    missing = REQUIRED_COLS - set(peaks.columns)
    if missing:
        raise ValueError(f'peaks.csv missing required columns: {sorted(missing)}')

    # Basic cleanup
    peaks['peak_id'] = peaks['peak_id'].astype('string').str.strip()
    peaks['peak_name'] = peaks['peak_name'].astype('string').str.strip()

    # Uniqueness check
    dupes = peaks['peak_id'][peaks['peak_id'].duplicated()].unique().tolist()
    if dupes:
        raise ValueError(f'Duplicate peak_id values found: {dupes}')

    # Numeric columns
    for c in ['latitude', 'longitude', 'enter_m', 'exit_m', 'exit_consec_points']:
        peaks[c] = pd.to_numeric(peaks[c], errors='raise')

    return peaks