"""
crud package
Re-exports all CRUD functions from their individual files so callers
can do either:

    from crud import create_log, get_log, update_log, delete_log

or, for backward compatibility with earlier code:

    from crud import log_crud
    log_crud.get_log(1)
"""

from crud.create import create_log
from crud.read import get_log, get_all_logs, count_logs, count_by_level, top_components, next_line_id
from crud.update import update_log
from crud.delete import delete_log

__all__ = [
    "create_log",
    "get_log", "get_all_logs", "count_logs", "count_by_level", "top_components", "next_line_id",
    "update_log",
    "delete_log",
]