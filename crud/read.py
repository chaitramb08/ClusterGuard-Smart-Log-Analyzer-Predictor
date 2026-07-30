"""
crud/read.py
Read operations for log entries — single row, filtered list, and count.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from database.db_connection import get_connection


def get_log(log_id):
    """Fetch a single log entry by id."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM logs WHERE id = ?", (log_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_logs(limit=100, offset=0, level=None, component=None):
    """Fetch logs, optionally filtered by level/component, with pagination."""
    conn = get_connection()
    query = "SELECT * FROM logs WHERE 1=1"
    params = []
    if level:
        query += " AND level = ?"
        params.append(level)
    if component:
        query += " AND component = ?"
        params.append(component)
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_logs():
    """Total number of log rows in the database."""
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
    conn.close()
    return n


def count_by_level():
    """Count of logs grouped by level — used by the dashboard summary cards."""
    conn = get_connection()
    rows = conn.execute("SELECT level, COUNT(*) as count FROM logs GROUP BY level").fetchall()
    conn.close()
    return {r["level"]: r["count"] for r in rows}


def top_components(limit=10):
    """Most frequent components — used by the dashboard."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT component, COUNT(*) as count FROM logs
        GROUP BY component ORDER BY count DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def next_line_id():
    """Smallest unused line_id greater than the current max — used to
    auto-generate line_id for logs created through the dashboard UI,
    so the user doesn't have to supply one manually."""
    conn = get_connection()
    row = conn.execute("SELECT MAX(line_id) FROM logs").fetchone()
    conn.close()
    return (row[0] or 0) + 1


if __name__ == "__main__":
    print("Total logs:", count_logs())
    print("By level:", count_by_level())