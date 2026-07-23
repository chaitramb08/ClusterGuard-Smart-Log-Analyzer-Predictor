from db_config import get_connection, sync_db_to_csv


def update_log_level(line_id, new_level):
    """1. Updates log level in DB. 2. Auto-exports DB to CSV."""
    sql = "UPDATE logs SET level = ? WHERE line_id = ?"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (new_level, line_id))
        conn.commit()
        success = cursor.rowcount > 0

    if success:
        print(f"✅ Line ID {line_id} updated in DB.")
        # Auto-export updated DB state to CSV
        sync_db_to_csv()
    else:
        print(f"⚠️ Line ID {line_id} not found in DB.")

    return success