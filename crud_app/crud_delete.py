from db_config import get_connection, sync_db_to_csv


def delete_log_record(line_id):
    """1. Deletes log from DB. 2. Auto-exports DB to CSV."""
    sql = "DELETE FROM logs WHERE line_id = ?"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (line_id,))
        conn.commit()
        success = cursor.rowcount > 0

    if success:
        print(f"✅ Line ID {line_id} deleted from DB.")
        # Auto-export updated DB state to CSV
        sync_db_to_csv()
    else:
        print(f"⚠️ Line ID {line_id} not found in DB.")

    return success