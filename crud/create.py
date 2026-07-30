"""
crud/create.py
Create operation for log entries.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from database.db_connection import get_connection


def create_log(line_id, log_date, log_time, pid, tid, level,
                component, content, event_id, event_template):
    """Insert a new log entry. Returns the new row's id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO logs (line_id, log_date, log_time, pid, tid, level,
                           component, content, event_id, event_template)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (line_id, log_date, log_time, pid, tid, level,
          component, content, event_id, event_template))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def next_line_id():
    """Smallest unused line_id greater than the current max — used to
    auto-generate line_id for logs created through the dashboard UI,
    so the user doesn't have to supply one manually."""
    conn = get_connection()
    row = conn.execute("SELECT MAX(line_id) FROM logs").fetchone()
    conn.close()
    return (row[0] or 0) + 1

if __name__ == "__main__":
    from database.db_connection import init_db
    init_db()
    new_id = create_log(1, "03-17", "16:13:38.811", 1702, 2395, "D",
                         "WindowManager", "sample content", "E100", "sample template")
    print("Created log id:", new_id)
