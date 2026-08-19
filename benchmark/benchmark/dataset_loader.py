"""
dataset_loader.py — loads the CSV files in datasets/ into a single SQLite
database (benchmark.db), one table per dataset.
"""

import os
import sqlite3
import pandas as pd

from . import config


def _clean_column_name(col: str) -> str:
    """Clean CSV header for consistent SQLite/schema matching."""
    col = str(col).strip()

    # Remove extra whitespace
    col = " ".join(col.split())

    # Make SQLite-safe
    col = col.replace(" ", "_").replace("-", "_")

    return col


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean column names and string values."""

    # Clean column names
    df.columns = [_clean_column_name(c) for c in df.columns]

    # Clean string values
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].apply(
            lambda x: x.strip() if isinstance(x, str) else x
        )

    return df


def load_csv(dataset_key: str) -> pd.DataFrame:
    """Read a single dataset's CSV into a cleaned DataFrame."""

    meta = config.DATASETS[dataset_key]
    path = os.path.join(config.DATASETS_DIR, meta["csv"])

    df = pd.read_csv(path)

    # Clean headers + values
    df = _clean_dataframe(df)

    return df


def load_all_to_sqlite(db_path: str = None) -> str:
    """
    Load every dataset CSV into its own table inside a SQLite database.
    Returns the path to the database file.
    """

    db_path = db_path or config.DB_PATH

    # Start fresh each run so the benchmark is reproducible.
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)

    try:
        for key, meta in config.DATASETS.items():

            df = load_csv(key)

            print(
                f"       [OK] {key:<30} "
                f"{len(df):>6} rows -> {meta['table']}"
            )

            df.to_sql(
                meta["table"],
                conn,
                if_exists="replace",
                index=False
            )

        conn.commit()

    finally:
        conn.close()

    return db_path


def get_dataframe(dataset_key: str) -> pd.DataFrame:
    """Convenience accessor used by model_runner for training/prediction."""
    return load_csv(dataset_key)


if __name__ == "__main__":
    path = load_all_to_sqlite()
    print(f"Loaded datasets into: {path}")