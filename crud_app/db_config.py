import csv
import sqlite3

DB_NAME = "android_logs.db"
CSV_FILE = "exported_logs.csv"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create logs table and indexes if they don't exist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                line_id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                time TEXT,
                pid INTEGER,
                tid INTEGER,
                level TEXT NOT NULL,
                component TEXT NOT NULL,
                content TEXT NOT NULL,
                event_id TEXT,
                event_template TEXT
            )
        """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_level ON logs(level);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_component ON logs(component);"
        )
        conn.commit()


def bulk_import_android_csv(csv_filepath="Android_2k.log_structured.csv"):
    """Imports initial CSV data into SQLite if DB is empty."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM logs")
        if cursor.fetchone()[0] > 0:
            print("⚠️ Database already populated. Skipping import.")
            return

        print("⏳ Importing Android log data into database...")
        with open(csv_filepath, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            rows = [
                (
                    int(row["LineId"]),
                    row.get("Date", ""),
                    row.get("Time", ""),
                    int(row["Pid"]) if str(row.get("Pid", "")).isdigit() else 0,
                    int(row["Tid"]) if str(row.get("Tid", "")).isdigit() else 0,
                    row.get("Level", "").strip(),
                    row.get("Component", "").strip(),
                    row.get("Content", "").strip(),
                    row.get("EventId", "").strip(),
                    row.get("EventTemplate", "").strip(),
                )
                for row in reader
            ]

            cursor.executemany(
                """
                INSERT INTO logs (line_id, date, time, pid, tid, level, component, content, event_id, event_template)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                rows,
            )
            conn.commit()
        print(f"✅ Loaded {len(rows)} Android log records into database!")

    # Initial sync to exported_logs.csv
    sync_db_to_csv()


def sync_db_to_csv(output_csv=CSV_FILE):
    """Fetches all records from SQLite DB and overwrites the CSV file."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs")
        rows = cursor.fetchall()

        if not rows:
            return

        column_names = [description[0] for description in cursor.description]

        with open(output_csv, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(column_names)  # Write headers
            writer.writerows([tuple(row) for row in rows])  # Write database rows

        print(f"🔄 [AUTO-SYNC] CSV file '{output_csv}' updated from database.")