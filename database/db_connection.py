"""
database/db_connection.py
Handles SQLite database connection and schema initialization
for the Smart Log Analyzer & Failure Prediction system.

Schema matches the loghub Android_2k.log_structured.csv columns:
https://github.com/logpai/loghub/blob/master/Android/Android_2k.log_structured.csv
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "logs.db")


def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # allows dict-like row access
    return conn


def init_db():
    """Creates the logs table if it doesn't already exist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_id INTEGER,
            log_date TEXT,          -- e.g. '03-17'
            log_time TEXT,          -- e.g. '16:13:38.811'
            pid INTEGER,
            tid INTEGER,
            level TEXT NOT NULL,    -- V, D, I, W, E
            component TEXT,
            content TEXT,
            event_id TEXT,
            event_template TEXT,
            is_anomaly INTEGER DEFAULT 0,  -- filled in by Phase 3 prediction
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    init_db()
