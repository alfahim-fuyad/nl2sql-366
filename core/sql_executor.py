# core/sql_executor.py

import os
import sqlite3


def _get_database_url():
    url = os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _execute_postgres(sql, database_url):
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
    database_url = _get_database_url()
    if database_url:
        return _execute_postgres(sql, database_url)
    return _execute_sqlite(sql, db_path)
