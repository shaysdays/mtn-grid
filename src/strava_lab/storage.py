import json
import pandas as pd
from .config import DATA_RAW_DIR, DATA_PROCESSED_DIR

RAW_ACTIVITIES_PATH = DATA_RAW_DIR / "activities.json"
PROCESSED_ACTIVITIES_PATH = DATA_PROCESSED_DIR / "activities.parquet"


def save_raw_activities(activities: list[dict]) -> None:
    RAW_ACTIVITIES_PATH.write_text(json.dumps(activities), encoding="utf-8")


def load_raw_activities() -> list[dict]:
    return json.loads(RAW_ACTIVITIES_PATH.read_text(encoding="utf-8"))


def save_processed_activities(df: pd.DataFrame) -> None:
    df.to_parquet(PROCESSED_ACTIVITIES_PATH, index=False)


def load_processed_activities() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_ACTIVITIES_PATH)