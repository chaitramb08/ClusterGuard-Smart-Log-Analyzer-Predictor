"""
crud/delete.py
Delete operation for log entries.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from database.db_connection import get_connection


def delete_log(log_id):
    """Delete a log entry by id."""
    conn = get_connection()
    conn.execute("DELETE FROM logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()
    return True
