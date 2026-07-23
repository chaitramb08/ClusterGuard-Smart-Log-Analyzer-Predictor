from db_config import get_connection, sync_db_to_csv


def create_log_record(date, time_val, pid, tid, level, component, content):
    """1. Inserts log into SQLite DB. 2. Auto-exports DB to CSV."""
    sql = """
        INSERT INTO logs (date, time, pid, tid, level, component, content, event_id, event_template)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'E0', 'Manual Entry')
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            sql, (date, time_val, pid, tid, level, component, content)
        )
        conn.commit()
        new_id = cursor.lastrowid

    print(f"✅ Record saved to DB with line_id: {new_id}")

    # Auto-export updated DB state to CSV
    sync_db_to_csv()
    return new_id