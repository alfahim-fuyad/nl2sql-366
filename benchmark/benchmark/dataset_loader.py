"""
dataset_loader.py — loads the CSV files in datasets/ into a single SQLite
database (benchmark.db), one table per dataset.
"""
import os
import sqlite3
import pandas as pd

from . import config


def _clean_column_name(col: str) -> str:
    """Make a CSV header safe to use as a SQLite column name."""
    return col.strip().replace(" ", "_").replace("-", "_")


def load_csv(dataset_key: str) -> pd.DataFrame:
    """Read a single dataset's CSV into a DataFrame with cleaned column names."""
    meta = config.DATASETS[dataset_key]
    path = os.path.join(config.DATASETS_DIR, meta["csv"])
    df = pd.read_csv(path)
    df.columns = [_clean_column_name(c) for c in df.columns]
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
            df.to_sql(meta["table"], conn, if_exists="replace", index=False)
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
