"""Tests for dataset loading and schema extraction."""

from dataset_loader import load_dataset
from schema_reader import read_schema, get_numeric_columns, get_text_columns


def test_load_dataset_returns_correct_rows(tmp_path):
    db_path = str(tmp_path / "test.db")
    df = load_dataset("data/sample.csv", db_path)
    assert len(df) == 10


def test_schema_has_all_columns(tmp_path):
    db_path = str(tmp_path / "test.db")
    df = load_dataset("data/sample.csv", db_path)
    schema = read_schema(df)

    assert "Age" in schema
    assert "Gender" in schema
    assert "District" in schema


def test_numeric_and_text_columns_detected(tmp_path):
    db_path = str(tmp_path / "test.db")
    df = load_dataset("data/sample.csv", db_path)
    schema = read_schema(df)

    numeric_columns = get_numeric_columns(schema)
    text_columns    = get_text_columns(schema)

    assert "Age" in numeric_columns
    assert "Gender" in text_columns
