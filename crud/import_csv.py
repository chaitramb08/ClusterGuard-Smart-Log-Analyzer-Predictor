"""
crud/import_csv.py
Phase 1 — Bulk-loads the loghub Android_2k.log_structured.csv dataset
into the SQLite database using the CRUD create_log() function.

Run once to seed the database:
    python crud/import_csv.py
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from database.db_connection import init_db
from crud.create import create_log
from crud.read import count_logs

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "Android_2k.csv")


def import_csv(csv_path=CSV_PATH):
    init_db()
    df = pd.read_csv(csv_path)
    df = df.where(pd.notnull(df), None)  # NaN -> None for SQLite

    inserted = 0
    for _, row in df.iterrows():
        create_log(
            line_id=int(row["LineId"]),
            log_date=row["Date"],
            log_time=row["Time"],
            pid=int(row["Pid"]),
            tid=int(row["Tid"]),
            level=row["Level"],
            component=row["Component"],
            content=row["Content"],
            event_id=row["EventId"],
            event_template=row["EventTemplate"],
        )
        inserted += 1

    print(f"Imported {inserted} rows. Total rows in DB: {count_logs()}")


if __name__ == "__main__":
    import_csv()
