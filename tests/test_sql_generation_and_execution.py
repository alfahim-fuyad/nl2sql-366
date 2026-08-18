# tests/test_sql_generation_and_execution.py

from dataset_loader import load_dataset
from schema_reader import read_schema
from sql_generator import build_query, query_to_sql
from sql_executor import execute_query


def test_select_with_filters(tmp_path):
    db_path = str(tmp_path / "test.db")
    df      = load_dataset("data/sample.csv", db_path)
    schema  = read_schema(df)

    query = build_query("show female patients older than 30", schema, "SELECT")
    sql   = query_to_sql(query)

    assert '"Gender" = \'Female\'' in sql
    assert '"Age" > 30' in sql


def test_count_query(tmp_path):
    db_path = str(tmp_path / "test.db")
    df      = load_dataset("data/sample.csv", db_path)
    schema  = read_schema(df)

    query = build_query("how many patients from dhaka", schema, "COUNT")
    sql   = query_to_sql(query)

    assert sql.startswith("SELECT COUNT(*)")
    assert '"District" = \'Dhaka\'' in sql


def test_avg_query_has_agg_column(tmp_path):
    db_path = str(tmp_path / "test.db")
    df      = load_dataset("data/sample.csv", db_path)
    schema  = read_schema(df)

    query = build_query("average age", schema, "AVG")
    assert query["agg_column"] == "Age"

    sql = query_to_sql(query)
    assert sql == 'SELECT AVG("Age") FROM "data"'


def test_query_executes_and_returns_rows(tmp_path):
    db_path = str(tmp_path / "test.db")
    df      = load_dataset("data/sample.csv", db_path)
    schema  = read_schema(df)

    query   = build_query("show female patients", schema, "SELECT")
    sql     = query_to_sql(query)

    columns, rows = execute_query(sql, db_path)
    assert "Gender" in columns
    assert len(rows) > 0
    gender_index = columns.index("Gender")
    for row in rows:
        assert row[gender_index] == "Female"
