"""
Interactive CLI for the NL2SQL pipeline.

Loads a CSV dataset and ML model once, then accepts repeated natural language
questions until the user exits or switches to a different CSV file.
"""

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
    """Run the full NL2SQL pipeline for a single question and print the result."""
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

    csv_path = input("CSV file path (default: data/sample.csv): ").strip()
    if not csv_path:
        csv_path = "data/sample.csv"

    db_path    = "data/database.db"
    table_name = "data"

    try:
        df = load_dataset(csv_path, db_path, table_name)
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
    print("Type 'change_csv' to load a different file.\n")

    while True:
        try:
            question = input("Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue

        if question.lower() in ("exit", "quit", "q"):
            print("Goodbye!")
            break

        if question.lower() == "change_csv":
            new_csv = input("New CSV file path: ").strip()
            if new_csv:
                try:
                    df     = load_dataset(new_csv, db_path, table_name)
                    schema = read_schema(df)
                    print("Dataset updated.")
                except Exception as e:
                    print("Error loading CSV:", e)
            continue

        run_pipeline(df, schema, question, model, vectorizer, db_path, table_name)
        print("\n" + "-" * 50 + "\n")


if __name__ == "__main__":
    main()
