# tests/test_sql_generation_and_execution.py

from dataset_loader import load_dataset
from schema_reader import read_schema
from sql_generator import build_query, query_to_sql
from sql_executor import execute_query
import pandas as pd


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


def test_highest_average_by_department_groups_and_ranks_aggregate(tmp_path):
    df = pd.DataFrame({
        "Department": ["IT", "IT", "HR", "HR"],
        "Monthly_Salary": [100000, 120000, 90000, 95000],
    })
    schema = read_schema(df)

    query = build_query(
        "Which department has the highest average Monthly_Salary?",
        schema,
        "AVG",
    )
    sql = query_to_sql(query)

    assert query["group_by"] == "Department"
    assert query["agg_column"] == "Monthly_Salary"
    assert query["order_by"] == "Monthly_Salary"
    assert query["order_dir"] == "DESC"
    assert query["limit"] == 1
    assert sql == (
        'SELECT "Department", AVG("Monthly_Salary") AS "avg_monthly_salary" '
        'FROM "data" GROUP BY "Department" '
        'ORDER BY "avg_monthly_salary" DESC LIMIT 1'
    )


def test_highest_average_by_department_returns_correct_group(tmp_path):
    csv_path = tmp_path / "employees.csv"
    pd.DataFrame({
        "Department": ["IT", "IT", "HR", "HR"],
        "Monthly_Salary": [100000, 120000, 90000, 95000],
    }).to_csv(csv_path, index=False)
    db_path = str(tmp_path / "employees.db")
    df = load_dataset(str(csv_path), db_path)
    schema = read_schema(df)

    query = build_query(
        "Which department has the highest average Monthly_Salary?",
        schema,
        "AVG",
    )
    columns, rows = execute_query(query_to_sql(query), db_path)

    assert columns == ["Department", "avg_monthly_salary"]
    assert rows == [("IT", 110000.0)]


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
