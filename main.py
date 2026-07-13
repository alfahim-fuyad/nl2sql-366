# main.py

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))

from dataset_loader import load_dataset
from schema_reader import read_schema
from intent_detector import load_model, predict_intent
from sql_generator import build_query, query_to_sql
from sql_validator import validate_sql
from sql_executor import execute_query
from response import print_result


def run_pipeline(df, schema, question, model, vectorizer,
                 db_path="data/database.db", table_name="data"):
    intent = predict_intent(question, model, vectorizer)
    query  = build_query(question, schema, intent)

    try:
        sql = query_to_sql(query, table_name)
    except ValueError as e:
        print("Error:", e)
        return

    print("Detected intent :", intent)
    print("Internal query  :", query)
    print("Generated SQL   :", sql)
    print()

    is_valid, message = validate_sql(sql, schema, table_name)
    if not is_valid:
        print("SQL validation failed:", message)
        return

    try:
        columns, rows = execute_query(sql, db_path)
    except Exception as e:
        print("Execution error:", e)
        return

    print_result(columns, rows)


def main():
    print("=== NL to SQL AI — Interactive Mode ===")

    file_path = input("Dataset file path (CSV/Excel) (default: data/sample.csv): ").strip()

    if not file_path:
        file_path = "data/sample.csv"
    if not csv_path:
        csv_path = "data/sample.csv"

    db_path    = "data/database.db"
    table_name = "data"

    try:
        df = load_dataset(file_path, db_path, table_name)
    except FileNotFoundError as e:
        print("Error:", e)
        return

    schema = read_schema(df)

    try:
        model, vectorizer = load_model(
            "models/intent_model.pkl", "models/vectorizer.pkl"
        )
    except FileNotFoundError:
        print("Error: Model files not found. Train first:")
        print("  python3 models/train_intent.py")
        return

    print("\nAsk questions about your data. Type 'exit' to quit.")
    print("Type 'change_dataset' to load a different CSV or Excel file.\n")

    while True:
        try:
            question = input("Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue

        if question.lower() in ("change_dataset", "change_csv"):
            new_file = input("New dataset file path (CSV/Excel): ").strip()
            if new_file:
                try:
                    df = load_dataset(new_file, db_path, table_name)
                    schema = read_schema(df)
                    print("Dataset updated.")
                except Exception as e:
                    print("Error loading dataset:", e)
            continue

        run_pipeline(df, schema, question, model, vectorizer, db_path, table_name)
        print("\n" + "-" * 50 + "\n")


if __name__ == "__main__":
    main()
