"""
etl/etl.py
End-to-end ETL pipeline for the Smart Log Analyzer.

    EXTRACT  — read the raw loghub CSV from disk
    TRANSFORM — clean/validate rows, parse timestamps, drop bad rows,
                de-duplicate against what's already in the database
    LOAD      — insert the cleaned rows into SQLite via the CRUD layer,
                then hand off to the Phase 2/3 pipeline (feature
                engineering + model training) so the database and the
                trained model are always in sync after a run.

Run directly:
    python etl/etl.py [path/to/csv]

If no path is given, defaults to logs/Android_2k.csv.
This is also what run.bat calls to automate the whole pipeline.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from database.db_connection import init_db, get_connection
from crud.create import create_log
from crud.read import count_logs

DEFAULT_CSV = os.path.join(os.path.dirname(__file__), "..", "logs", "Android_2k.csv")

REQUIRED_COLUMNS = [
    "LineId", "Date", "Time", "Pid", "Tid", "Level",
    "Component", "Content", "EventId", "EventTemplate",
]


def extract(csv_path):
    """EXTRACT — read the raw CSV into a DataFrame."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found at {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"[EXTRACT] Read {len(df)} rows from {csv_path}")
    return df


def transform(df):
    """
    TRANSFORM — validate schema, drop rows missing required fields,
    normalize types, and skip line_ids already present in the DB
    so re-running the ETL doesn't create duplicates.
    """
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"CSV is missing expected columns: {missing_cols}")

    before = len(df)
    df = df.dropna(subset=["LineId", "Date", "Time", "Level"])
    df = df.where(pd.notnull(df), None)  # remaining NaNs -> None for SQLite
    df["LineId"] = df["LineId"].astype(int)
    df["Pid"] = df["Pid"].fillna(0).astype(int)
    df["Tid"] = df["Tid"].fillna(0).astype(int)
    dropped = before - len(df)

    # skip rows whose line_id is already loaded, so re-running is safe
    conn = get_connection()
    existing_ids = {r[0] for r in conn.execute("SELECT line_id FROM logs").fetchall()}
    conn.close()
    before_dedup = len(df)
    df = df[~df["LineId"].isin(existing_ids)]
    deduped = before_dedup - len(df)

    print(f"[TRANSFORM] Dropped {dropped} invalid rows, "
          f"skipped {deduped} already-loaded rows, {len(df)} rows ready to load")
    return df


def load(df):
    """LOAD — insert cleaned rows into the database via the CRUD create op."""
    inserted = 0
    for _, row in df.iterrows():
        create_log(
            line_id=row["LineId"],
            log_date=row["Date"],
            log_time=row["Time"],
            pid=row["Pid"],
            tid=row["Tid"],
            level=row["Level"],
            component=row["Component"],
            content=row["Content"],
            event_id=row["EventId"],
            event_template=row["EventTemplate"],
        )
        inserted += 1
    print(f"[LOAD] Inserted {inserted} rows. Total rows in DB: {count_logs()}")
    return inserted


def run_etl(csv_path=DEFAULT_CSV):
    init_db()
    df = extract(csv_path)
    df = transform(df)
    load(df)


if __name__ == "__main__":
    csv_arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
    run_etl(csv_arg)
