"""
data_analysis/analyze_logs.py
Phase 2 — Load logs from the database into pandas, explore them,
and engineer time-window features that Phase 3's model will train on.

The raw dataset has no explicit "failure" label, and Error-level logs
are rare (~0.15% of rows), so instead of predicting per-row, we bucket
logs into fixed time windows and compute traffic/error statistics per
window. Phase 3 then flags windows that look abnormal.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from database.db_connection import get_connection

WINDOW = "10s"  # bucket size for feature engineering — tune as needed


def load_logs_df():
    """Load the full logs table into a pandas DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM logs", conn)
    conn.close()
    return df


def basic_summary(df: pd.DataFrame):
    """Print quick summary stats."""
    print("Row count:", len(df))
    print("\nLevel distribution:\n", df["level"].value_counts())
    print("\nTop components:\n", df["component"].value_counts().head(10))
    print("\nMissing values:\n", df.isnull().sum())


def build_timestamp(df: pd.DataFrame, reference_year=2024):
    """
    Combine log_date ('03-17') + log_time ('16:13:38.811') into a real
    datetime column. The dataset has no year, so a fixed reference year
    is used — fine since we only care about relative time ordering.
    """
    df["timestamp"] = pd.to_datetime(
        str(reference_year) + "-" + df["log_date"] + " " + df["log_time"],
        format="%Y-%m-%d %H:%M:%S.%f",
        errors="coerce"
    )
    return df.dropna(subset=["timestamp"]).sort_values("timestamp")


def build_window_features(df: pd.DataFrame, window=WINDOW):
    """
    Resample logs into fixed time windows and compute per-window stats.
    This feature table is what the Phase 3 model trains on.
    """
    df = df.set_index("timestamp")

    total = df["level"].resample(window).count().rename("total_logs")
    error_count = df[df["level"] == "E"]["level"].resample(window).count().rename("error_count")
    warn_count = df[df["level"] == "W"]["level"].resample(window).count().rename("warn_count")
    distinct_events = df["event_id"].resample(window).nunique().rename("distinct_events")
    distinct_components = df["component"].resample(window).nunique().rename("distinct_components")

    features = pd.concat(
        [total, error_count, warn_count, distinct_events, distinct_components],
        axis=1
    ).fillna(0)

    # windows with zero traffic aren't useful for training
    features = features[features["total_logs"] > 0].reset_index()
    features["error_warn_ratio"] = (
        (features["error_count"] + features["warn_count"]) / features["total_logs"]
    )
    return features


if __name__ == "__main__":
    df = load_logs_df()
    if df.empty:
        print("No logs found — run crud/import_csv.py first to seed the database.")
    else:
        basic_summary(df)
        df = build_timestamp(df)
        features = build_window_features(df)
        print("\nWindow feature table (head):\n", features.head())
        print("\nWindows with highest error/warn ratio:\n",
              features.sort_values("error_warn_ratio", ascending=False).head())

        out_path = os.path.join(os.path.dirname(__file__), "window_features.csv")
        features.to_csv(out_path, index=False)
        print(f"\nSaved {out_path}")
