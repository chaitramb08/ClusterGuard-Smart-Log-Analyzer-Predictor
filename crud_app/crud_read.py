from db_config import get_connection


def read_log_records(limit=10):
    """Fetch top N log records from SQLite."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]


def read_log_by_component(component_name):
    """Search log records matching a component in SQLite."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM logs WHERE component LIKE ?",
            (f"%{component_name}%",),
        )
        return [dict(row) for row in cursor.fetchall()]