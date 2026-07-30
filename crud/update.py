"""
crud/update.py
Update operation for log entries.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from database.db_connection import get_connection


def update_log(log_id, **fields):
    """Update arbitrary fields on a log entry. e.g. update_log(5, level='E')"""
    if not fields:
        return False
    conn = get_connection()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [log_id]
    conn.execute(f"UPDATE logs SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return True
