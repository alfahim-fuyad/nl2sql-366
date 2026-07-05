"""
Loads a CSV file into a pandas DataFrame and persists it to a database.

Backend selection:
    - If DATABASE_URL or NEON_DATABASE_URL is set → PostgreSQL (production)
    - Otherwise → SQLite (local development)
"""

import os
import sqlite3
import pandas as pd


def load_csv(csv_path):
    """
    Read a CSV file and return a DataFrame.

    Tries UTF-8 encoding first, then falls back to Latin-1 for files
    that use legacy encodings.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    try:
        return pd.read_csv(csv_path, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(csv_path, encoding="latin-1")


def _get_database_url():
    """Return the PostgreSQL connection URL from environment variables, or None."""
    return os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")


def save_to_postgres(df, table_name="data", database_url=None):
    """
    Persist a DataFrame to a PostgreSQL database using SQLAlchemy.

    Replaces the existing table on every upload.
    """
    from sqlalchemy import create_engine, text

    url = database_url or _get_database_url()
    if not url:
        raise RuntimeError(
            "No PostgreSQL URL found. "
            "Set DATABASE_URL or NEON_DATABASE_URL environment variable."
        )
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
    df.to_sql(table_name, engine, if_exists="replace", index=False)
    engine.dispose()


def save_to_sqlite(df, db_path, table_name="data"):
    """
    Persist a DataFrame to a local SQLite database file.

    Creates the parent directory automatically if it does not exist.
    """
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
    finally:
        conn.close()

    return db_path


def load_dataset(csv_path, db_path="data/database.db", table_name="data"):
    """
    Load a CSV file and persist it to the appropriate database backend.

    Returns the loaded DataFrame for immediate use by the pipeline.
    """
    df = load_csv(csv_path)

    database_url = _get_database_url()
    if database_url:
        save_to_postgres(df, table_name, database_url)
    else:
        save_to_sqlite(df, db_path, table_name)

    return df
