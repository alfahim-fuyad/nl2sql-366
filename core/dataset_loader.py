# core/dataset_loader.py

import os
import sqlite3
import pandas as pd


def load_dataset_file(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dataset file not found: {file_path}")

    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".csv":
        try:
            return pd.read_csv(file_path, encoding="utf-8")
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding="latin-1")

    elif extension in (".xlsx", ".xls"):
        return pd.read_excel(file_path)

    raise ValueError(
        "Unsupported file format. Please upload a CSV (.csv) or Excel (.xlsx, .xls) file."
    )


def _get_database_url():
    return os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")


def save_to_postgres(df, table_name="data", database_url=None):
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
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)

    try:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
    finally:
        conn.close()

    return db_path


def load_dataset(file_path, db_path="data/database.db", table_name="data"):
    df = load_dataset_file(file_path)

    database_url = _get_database_url()

    if database_url:
        save_to_postgres(df, table_name, database_url)
    else:
        save_to_sqlite(df, db_path, table_name)

    return df
