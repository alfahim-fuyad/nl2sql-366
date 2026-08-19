"""
sql_executor.py — runs SQL queries against benchmark.db and returns results
in a plain, JSON-serializable form.
"""
import sqlite3
from . import config


def execute_sql(query: str, db_path: str = None):
    """
    Execute a SQL query and return (columns, rows).
    rows is a list of tuples. Raises sqlite3.Error on invalid SQL.
    """
    db_path = db_path or config.DB_PATH
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description] if cur.description else []
        return columns, rows
    finally:
        conn.close()


def execute_scalar(query: str, db_path: str = None):
    """
    Execute a query expected to return a single scalar value
    (e.g. SELECT AVG(price) FROM housing) and return that value.
    """
    columns, rows = execute_sql(query, db_path)
    if not rows or not rows[0]:
        return None
    return rows[0][0]
