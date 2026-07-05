"""
Executes a SQL query against the configured database backend.

Backend selection:
    - DATABASE_URL or NEON_DATABASE_URL set → PostgreSQL (psycopg2)
    - Otherwise → SQLite (local development)
"""

import os
import sqlite3


def _get_database_url():
    """Return the PostgreSQL connection URL, normalising the scheme if needed."""
    url = os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _execute_postgres(sql, database_url):
    """Execute a SQL query against a PostgreSQL database and return results."""
    import psycopg2

    conn   = psycopg2.connect(database_url)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        rows         = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description] if cursor.description else []
    finally:
        cursor.close()
        conn.close()

    return column_names, rows


def _execute_sqlite(sql, db_path):
    """Execute a SQL query against a local SQLite database and return results."""
    conn   = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        rows         = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description] if cursor.description else []
    finally:
        conn.close()

    return column_names, rows


def execute_query(sql, db_path="data/database.db"):
    """
    Execute a SQL query and return (column_names, rows).

    Raises an exception on database errors; the caller is responsible
    for handling them.
    """
    database_url = _get_database_url()
    if database_url:
        return _execute_postgres(sql, database_url)
    return _execute_sqlite(sql, db_path)
