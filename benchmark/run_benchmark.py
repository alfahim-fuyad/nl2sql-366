#!/usr/bin/env python3
"""
run_benchmark.py — End-to-end NL2SQL benchmark pipeline.

Usage:
    cd /path/to/nl2sql-366
    python benchmark/run_benchmark.py

Pipeline for every SQL query:
    1. Execute reference SQL on the database → Reference Result
    2. Run NL query through NL2SQL-366 pipeline → Generated SQL
    3. Validate generated SQL
    4. Execute generated SQL → Generated Result
    5. Compare reference vs generated result (set-based, not string-based)
    6. Record all metrics
"""

import csv
import json
import os
import sys
import sqlite3
import time
import traceback
import warnings
from datetime import datetime, timezone

import pandas as pd

# Suppress sklearn version warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCHMARK_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.join(PROJECT_ROOT, "core")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
KNOWLEDGE_DIR = os.path.join(PROJECT_ROOT, "knowledge")
DATASETS_DIR = os.path.join(BENCHMARK_DIR, "benchmark", "datasets")
QUESTIONS_PATH = os.path.join(BENCHMARK_DIR, "benchmark", "questions.json")
OUTPUT_DIR = os.path.join(BENCHMARK_DIR, "output")

# Ensure core modules are importable
sys.path.insert(0, CORE_DIR)
sys.path.insert(0, PROJECT_ROOT)

# Also ensure knowledge/ and models/ paths work for core modules
os.chdir(PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Dataset configuration — maps dataset key → (csv file, table name)
# ---------------------------------------------------------------------------

DATASETS = {
    "housing": {
        "csv": "Housing.csv",
        "table": "housing",
    },
    "dengue": {
        "csv": "dengue.csv",
        "table": "dengue",
    },
    "temp_and_rain": {
        "csv": "Temp_and_rain.csv",
        "table": "temp_and_rain",
    },
    "student_performance": {
        "csv": "Student_performance.csv",
        "table": "student_performance",
    },
    # questions.json uses 'employee_dataset' as the key
    "employee_dataset": {
        "csv": "Employee Dataset.csv",
        "table": "employee",
    },
    # Also support 'employee' key
    "employee": {
        "csv": "Employee Dataset.csv",
        "table": "employee",
    },
}


def _clean_column_name(col: str) -> str:
    return col.strip().replace(" ", "_").replace("-", "_")


# ---------------------------------------------------------------------------
# Database management
# ---------------------------------------------------------------------------

def load_all_datasets(db_path: str) -> dict:
    """
    Load all CSVs into a single SQLite database.
    Returns dict: dataset_key → table_name
    """
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    dataframes = {}
    try:
        for key, meta in DATASETS.items():
            csv_path = os.path.join(DATASETS_DIR, meta["csv"])
            if not os.path.exists(csv_path):
                continue
            df = pd.read_csv(csv_path)
            df.columns = [_clean_column_name(c) for c in df.columns]
            df.to_sql(meta["table"], conn, if_exists="replace", index=False)
            if key not in dataframes:
                dataframes[key] = df
            # Alias: some reference SQL uses 'employee_dataset' as table name
            if key == "employee_dataset":
                df.to_sql("employee_dataset", conn, if_exists="replace", index=False)
    finally:
        conn.close()

    return dataframes


def get_table_for_dataset(dataset_key: str) -> str:
    """Resolve a dataset key to its SQLite table name."""
    if dataset_key in DATASETS:
        return DATASETS[dataset_key]["table"]
    raise ValueError(f"Unknown dataset key: {dataset_key}")


def get_dataframe_for_dataset(dataset_key: str, dataframes: dict) -> pd.DataFrame:
    """Get the DataFrame for a dataset key."""
    if dataset_key in dataframes:
        return dataframes[dataset_key]
    # Fallback: try loading directly
    if dataset_key in DATASETS:
        csv_path = os.path.join(DATASETS_DIR, DATASETS[dataset_key]["csv"])
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            df.columns = [_clean_column_name(c) for c in df.columns]
            return df
    raise ValueError(f"Cannot load dataset: {dataset_key}")


# ---------------------------------------------------------------------------
# SQL execution
# ---------------------------------------------------------------------------

def execute_sql(sql: str, db_path: str):
    """Execute SQL and return (columns, rows). Raises on error."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description] if cur.description else []
        return columns, rows
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Intent extraction from reference SQL
# ---------------------------------------------------------------------------

def extract_expected_intent(sql: str) -> str:
    """Derive the expected intent from a reference SQL query."""
    sql_upper = sql.strip().upper()
    if 'COUNT(' in sql_upper:
        return 'COUNT'
    if 'SUM(' in sql_upper:
        return 'SUM'
    if 'AVG(' in sql_upper:
        return 'AVG'
    if 'MIN(' in sql_upper:
        return 'MIN'
    if 'MAX(' in sql_upper:
        return 'MAX'
    return 'SELECT'


# ---------------------------------------------------------------------------
# NL2SQL pipeline integration
# ---------------------------------------------------------------------------

def run_nl2sql_pipeline(question: str, schema: dict, model, vectorizer,
                         table_name: str, db_path: str):
    """
    Run the full NL2SQL pipeline and return a result dict.
    """
    from intent_detector import predict_intent
    from sql_generator import build_query, query_to_sql
    from sql_validator import validate_sql

    result = {
        "predicted_intent": None,
        "generated_sql": None,
        "valid_sql": False,
        "validation_message": "",
        "gen_cols": None,
        "gen_rows": None,
        "gen_time_ms": 0,
        "exec_time_ms": 0,
        "execution_success": False,
        "error_message": "",
    }

    # Step 1: Intent detection
    try:
        intent = predict_intent(question, model, vectorizer)
        result["predicted_intent"] = intent
    except Exception as e:
        result["error_message"] = f"Intent detection failed: {e}"
        return result

    # Step 2: Build query structure
    try:
        query_struct = build_query(question, schema, intent)
    except Exception as e:
        result["error_message"] = f"Query building failed: {e}"
        return result

    # Step 3: SQL generation
    t0 = time.perf_counter()
    try:
        sql = query_to_sql(query_struct, table_name)
        result["generated_sql"] = sql
    except Exception as e:
        result["error_message"] = f"SQL generation failed: {e}"
        return result
    finally:
        result["gen_time_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # Step 4: SQL validation
    try:
        is_valid, msg = validate_sql(sql, schema, table_name)
        result["valid_sql"] = is_valid
        result["validation_message"] = msg
    except Exception as e:
        result["valid_sql"] = False
        result["validation_message"] = str(e)

    # Step 5: Execute generated SQL
    t0 = time.perf_counter()
    try:
        cols, rows = execute_sql(sql, db_path)
        result["gen_cols"] = cols
        result["gen_rows"] = rows
        result["execution_success"] = True
    except Exception as e:
        result["execution_success"] = False
        result["error_message"] = f"Execution error: {e}"
    finally:
        result["exec_time_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    return result


# ---------------------------------------------------------------------------
# Per-query benchmark
# ---------------------------------------------------------------------------

def benchmark_query(query_item: dict, db_path: str, dataframes: dict,
                     model, vectorizer) -> dict:
    """
    Run a single benchmark query through the full pipeline.
    """
    from schema_reader import read_schema
    from result_comparator import compare_results, classify_failure

    query_id = query_item["id"]
    question = query_item["question"]
    dataset_key = query_item["dataset"]
    ref_sql = query_item["sql"]

    record = {
        "query_id": query_id,
        "question": question,
        "dataset": dataset_key,
        "reference_sql": ref_sql,
        "expected_intent": extract_expected_intent(ref_sql),
        "generated_sql": None,
        "ref_cols": None,
        "ref_rows": None,
        "gen_cols": None,
        "gen_rows": None,
        "result_match": False,
        "exact_sql_match": False,
        "intent_match": False,
        "valid_sql": False,
        "execution_success": False,
        "gen_time_ms": 0,
        "exec_time_ms": 0,
        "error_message": "",
        "error_category": "unknown",
        "result_comparison": {},
        "predicted_intent": None,
    }

    try:
        table_name = get_table_for_dataset(dataset_key)
    except ValueError as e:
        record["error_message"] = str(e)
        record["error_category"] = "schema_error"
        return record

    # Execute reference SQL
    try:
        ref_cols, ref_rows = execute_sql(ref_sql, db_path)
        record["ref_cols"] = ref_cols
        record["ref_rows"] = ref_rows
    except Exception as e:
        record["error_message"] = f"Reference SQL execution failed: {e}"
        record["error_category"] = "reference_error"
        return record

    # Get schema for NL2SQL pipeline
    try:
        df = get_dataframe_for_dataset(dataset_key, dataframes)
        schema = read_schema(df)
    except Exception as e:
        record["error_message"] = f"Schema loading failed: {e}"
        record["error_category"] = "schema_error"
        return record

    # Run NL2SQL pipeline
    nl2sql_result = run_nl2sql_pipeline(
        question, schema, model, vectorizer, table_name, db_path
    )

    # Populate record from NL2SQL result
    record["predicted_intent"] = nl2sql_result["predicted_intent"]
    record["generated_sql"] = nl2sql_result["generated_sql"]
    record["valid_sql"] = nl2sql_result["valid_sql"]
    record["validation_message"] = nl2sql_result["validation_message"]
    record["gen_cols"] = nl2sql_result["gen_cols"]
    record["gen_rows"] = nl2sql_result["gen_rows"]
    record["gen_time_ms"] = nl2sql_result["gen_time_ms"]
    record["exec_time_ms"] = nl2sql_result["exec_time_ms"]
    record["execution_success"] = nl2sql_result["execution_success"]
    record["error_message"] = nl2sql_result["error_message"]

    # Intent match
    record["intent_match"] = (
        record["predicted_intent"] is not None
        and record["predicted_intent"] == record["expected_intent"]
    )

    # Exact SQL match (normalized whitespace/case-insensitive)
    if record["generated_sql"]:
        ref_norm = " ".join(ref_sql.strip().split()).upper()
        gen_norm = " ".join(record["generated_sql"].strip().split()).upper()
        record["exact_sql_match"] = (ref_norm == gen_norm)

    # Result comparison (only if both executed successfully)
    if (record["ref_rows"] is not None
            and nl2sql_result["execution_success"]
            and record["gen_rows"] is not None):
        comparison = compare_results(
            record["ref_cols"], record["ref_rows"],
            record["gen_cols"], record["gen_rows"],
            ref_sql, record["generated_sql"] or ""
        )
        record["result_match"] = comparison["match"]
        record["result_comparison"] = comparison

    # Classify failure
    if not record["result_match"]:
        record["error_category"] = classify_failure(record)

    return record


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------

def save_results_csv(results: list, path: str):
    """Save per-query results as CSV."""
    fieldnames = [
        "query_id", "question", "dataset", "reference_sql", "generated_sql",
        "expected_intent", "predicted_intent", "intent_match",
        "valid_sql", "execution_success", "result_match", "exact_sql_match",
        "gen_time_ms", "exec_time_ms", "error_category", "error_message",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            row = dict(r)
            # Truncate long fields for CSV readability
            row["error_message"] = (row.get("error_message") or "")[:200]
            writer.writerow(row)


def save_queries_csv(questions: list, path: str):
    """Save benchmark queries as CSV."""
    sql_qs = [q for q in questions if q.get("type") == "sql" and "sql" in q]
    fieldnames = ["id", "dataset", "question", "sql", "expected_answer"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for q in sql_qs:
            writer.writerow(q)


def save_summary_json(metrics_dict: dict, path: str, total_runtime_s: float):
    """Save benchmark summary as JSON."""
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_runtime_seconds": round(total_runtime_s, 2),
        "metrics": metrics_dict,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Report generation (called separately or inline)
# ---------------------------------------------------------------------------

def generate_report_markdown(metrics_dict: dict, results: list,
                              total_runtime_s: float, output_path: str):
    """Generate a professional Markdown benchmark report."""
    from metrics import extract_intent_from_sql

    o = metrics_dict["overall"]
    ea = metrics_dict["error_analysis"]
    by_intent = metrics_dict["by_intent"]
    by_dataset = metrics_dict["by_dataset"]
    f1_scores = metrics_dict["f1_scores"]

    lines = []
    lines.append("# NL2SQL-366 Benchmark Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Total Runtime:** {total_runtime_s:.2f} seconds")
    lines.append("")

    # --- 1. Benchmark Overview ---
    lines.append("## 1. Benchmark Overview")
    lines.append("")
    lines.append(f"- **Total SQL Queries Evaluated:** {o['total_queries']}")

    # Count unique schemas/datasets
    unique_ds = set(r["dataset"] for r in results)
    lines.append(f"- **Number of Datasets/Schemas:** {len(unique_ds)}")
    lines.append(f"- **Datasets:** {', '.join(sorted(unique_ds))}")

    # Intent distribution
    intent_dist = {}
    for r in results:
        intent = r["expected_intent"]
        intent_dist[intent] = intent_dist.get(intent, 0) + 1
    lines.append(f"- **Intent Distribution:**")
    for intent in sorted(intent_dist):
        lines.append(f"  - {intent}: {intent_dist[intent]} queries")
    lines.append("")

    # --- 2. Overall Results ---
    lines.append("## 2. Overall Results")
    lines.append("")
    lines.append("| Metric | Score |")
    lines.append("|--------|-------|")
    lines.append(f"| Intent Accuracy | {o['intent_accuracy']:.2f}% |")
    lines.append(f"| Valid SQL | {o['valid_sql_rate']:.2f}% |")
    lines.append(f"| Execution Success | {o['execution_success_rate']:.2f}% |")
    lines.append(f"| Result Match Accuracy | {o['result_match_accuracy']:.2f}% |")
    lines.append(f"| Exact SQL Match | {o['exact_sql_match_rate']:.2f}% |")
    lines.append(f"| Macro F1 | {metrics_dict['macro_f1']:.2f}% |")
    lines.append(f"| Avg SQL Generation Time | {o['avg_generation_time_ms']:.2f} ms |")
    lines.append(f"| Avg Execution Time | {o['avg_execution_time_ms']:.2f} ms |")
    lines.append(f"| Total Passed | {o['passed']} |")
    lines.append(f"| Total Failed | {o['failed']} |")
    lines.append("")
    lines.append("![Overall Metrics](chart_overall_metrics.png)")
    lines.append("")

    # --- 2.1 Method Comparison ---
    lines.append("### 2.1 Method Comparison")
    lines.append("")
    lines.append("| Method | Description | Accuracy |")
    lines.append("|--------|-------------|----------|")
    lines.append(f"| Reference SQL | Ground-truth SQL executed directly on the database | 100.00% (by definition) |")
    lines.append(f"| NL2SQL-366 | Natural language converted to SQL by the NL2SQL-366 pipeline | {o['result_match_accuracy']:.2f}% |")
    lines.append("")
    lines.append("> The Reference SQL serves as the ground truth. NL2SQL-366 is evaluated on whether its generated SQL produces the same database result as the reference query.")
    lines.append("")
    lines.append("![Pipeline Funnel](chart_pipeline_funnel.png)")
    lines.append("")

    # --- 3. Per-Intent Results ---
    lines.append("## 3. Per-Intent Results")
    lines.append("")
    lines.append("| Intent | Queries | Intent Acc. | Result Match | Exact SQL | Valid SQL | Exec Success |")
    lines.append("|--------|---------|-------------|--------------|-----------|-----------|-------------|")
    for intent, info in by_intent.items():
        f1 = f1_scores.get(intent, {})
        lines.append(
            f"| {intent} | {info['total']} | {info['intent_accuracy']:.2f}% "
            f"| {info['result_match_accuracy']:.2f}% | {info['exact_sql_match_rate']:.2f}% "
            f"| {info['valid_sql_rate']:.2f}% | {info['execution_success_rate']:.2f}% |"
        )
    lines.append("")
    lines.append("![Intent Accuracy](chart_intent_accuracy.png)")
    lines.append("")
    lines.append("![Result Match by Intent](chart_result_match.png)")
    lines.append("")

    # --- 4. Per-Dataset Results ---
    lines.append("## 4. Per-Dataset Results")
    lines.append("")
    lines.append("| Dataset | Queries | Intent Acc. | Result Match | Exact SQL |")
    lines.append("|---------|---------|-------------|--------------|-----------|")
    for ds, info in by_dataset.items():
        lines.append(
            f"| {ds} | {info['total']} | {info['intent_accuracy']:.2f}% "
            f"| {info['result_match_accuracy']:.2f}% | {info['exact_sql_match_rate']:.2f}% |"
        )
    lines.append("")
    lines.append("![Dataset Accuracy](chart_dataset_accuracy.png)")
    lines.append("")

    # --- 5. F1 Scores ---
    lines.append("## 5. Precision, Recall, F1 by Intent")
    lines.append("")
    lines.append("| Intent | Precision | Recall | F1 | Support |")
    lines.append("|--------|-----------|--------|-----|---------|")
    for intent, f1 in sorted(f1_scores.items()):
        lines.append(
            f"| {intent} | {f1['precision']:.2f}% | {f1['recall']:.2f}% "
            f"| {f1['f1']:.2f}% | {f1['support']} |"
        )
    lines.append("")

    # --- 6. Error Analysis ---
    lines.append("## 6. Error Analysis")
    lines.append("")
    lines.append(f"**Total Failed Queries:** {ea['total_failed']}")
    lines.append("")
    if ea["categories"]:
        lines.append("**Error Distribution:**")
        lines.append("")
        lines.append("| Error Category | Count |")
        lines.append("|----------------|-------|")
        for cat, cnt in ea["categories"].items():
            lines.append(f"| {cat} | {cnt} |")
        lines.append("")
    lines.append("![Error Distribution](chart_error_distribution.png)")
    lines.append("")

    if ea["failed_queries"]:
        lines.append("**Failed Query Details:**")
        lines.append("")
        lines.append("| ID | Dataset | Question | Expected Intent | Predicted | Error |")
        lines.append("|----|---------|----------|-----------------|-----------|-------|")
        for fq in ea["failed_queries"][:50]:  # Show up to 50
            q_short = (fq["question"] or "")[:50]
            lines.append(
                f"| {fq['id']} | {fq['dataset']} | {q_short} "
                f"| {fq['expected_intent']} | {fq['predicted_intent']} "
                f"| {fq['error_category']} |"
            )
        if len(ea["failed_queries"]) > 50:
            lines.append(f"| ... | | | | | +{len(ea['failed_queries'])-50} more |")
        lines.append("")

    # --- 7. Reference vs Generated Analysis ---
    lines.append("## 7. Reference vs Generated SQL Analysis")
    lines.append("")

    # Categorize results
    exact_sql_and_result = 0
    diff_sql_same_result = 0
    valid_wrong_result = 0
    invalid_sql = 0
    exec_failed = 0

    for r in results:
        if r["exact_sql_match"] and r["result_match"]:
            exact_sql_and_result += 1
        elif not r["exact_sql_match"] and r["result_match"]:
            diff_sql_same_result += 1
        elif r["valid_sql"] and r["execution_success"] and not r["result_match"]:
            valid_wrong_result += 1
        elif not r["valid_sql"]:
            invalid_sql += 1
        elif not r["execution_success"]:
            exec_failed += 1
        else:
            valid_wrong_result += 1

    lines.append("| Category | Count | Percentage |")
    lines.append("|----------|-------|------------|")
    total = len(results) or 1
    lines.append(f"| SQL exactly identical, result correct | {exact_sql_and_result} | {_pct(exact_sql_and_result, total):.2f}% |")
    lines.append(f"| SQL different, but result identical | {diff_sql_same_result} | {_pct(diff_sql_same_result, total):.2f}% |")
    lines.append(f"| SQL valid but result incorrect | {valid_wrong_result} | {_pct(valid_wrong_result, total):.2f}% |")
    lines.append(f"| SQL invalid | {invalid_sql} | {_pct(invalid_sql, total):.2f}% |")
    lines.append(f"| SQL execution failed | {exec_failed} | {_pct(exec_failed, total):.2f}% |")
    lines.append("")

    # Examples of each category
    lines.append("### Examples")
    lines.append("")

    # Example: exact match
    for r in results:
        if r["exact_sql_match"] and r["result_match"]:
            lines.append(f"**Exact SQL + Correct Result (ID {r['query_id']}):**")
            lines.append(f"- Question: {r['question']}")
            lines.append(f"- SQL: `{r['reference_sql']}`")
            lines.append("")
            break

    # Example: different SQL, same result
    for r in results:
        if not r["exact_sql_match"] and r["result_match"]:
            lines.append(f"**Different SQL + Same Result (ID {r['query_id']}):**")
            lines.append(f"- Question: {r['question']}")
            lines.append(f"- Reference: `{r['reference_sql']}`")
            lines.append(f"- Generated: `{r['generated_sql']}`")
            lines.append("")
            break

    # Example: valid SQL, wrong result
    for r in results:
        if r["valid_sql"] and r["execution_success"] and not r["result_match"]:
            lines.append(f"**Valid SQL + Wrong Result (ID {r['query_id']}):**")
            lines.append(f"- Question: {r['question']}")
            lines.append(f"- Reference: `{r['reference_sql']}`")
            lines.append(f"- Generated: `{r['generated_sql']}`")
            lines.append(f"- Error: {r['error_category']}")
            lines.append("")
            break

    # Example: invalid SQL
    for r in results:
        if not r["valid_sql"] and r["generated_sql"]:
            lines.append(f"**Invalid SQL (ID {r['query_id']}):**")
            lines.append(f"- Question: {r['question']}")
            lines.append(f"- Generated: `{r['generated_sql']}`")
            lines.append(f"- Validation: {r.get('validation_message', 'N/A')}")
            lines.append("")
            break

    # Example: execution failure
    for r in results:
        if r["valid_sql"] and not r["execution_success"]:
            lines.append(f"**Execution Failed (ID {r['query_id']}):**")
            lines.append(f"- Question: {r['question']}")
            lines.append(f"- Generated: `{r['generated_sql']}`")
            lines.append(f"- Error: {r['error_message']}")
            lines.append("")
            break

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _pct(n, d):
    return round(100.0 * n / d, 2) if d else 0.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t_start = time.perf_counter()

    print("=" * 60)
    print("NL2SQL-366 BENCHMARK")
    print("=" * 60)
    print()

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Step 1: Load datasets
    db_path = os.path.join(OUTPUT_DIR, "benchmark.db")
    print("[1/7] Loading datasets into SQLite...")
    dataframes = load_all_datasets(db_path)
    print(f"       {len(dataframes)} datasets loaded into {db_path}")

    # Step 2: Load questions
    print("[2/7] Loading benchmark questions...")
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        all_questions = json.load(f)
    sql_questions = [q for q in all_questions if q.get("type") == "sql" and "sql" in q]
    print(f"       {len(sql_questions)} SQL queries (out of {len(all_questions)} total)")

    # Save benchmark_queries.csv
    queries_csv_path = os.path.join(OUTPUT_DIR, "benchmark_queries.csv")
    save_queries_csv(all_questions, queries_csv_path)
    print(f"       Queries saved to {queries_csv_path}")

    # Step 3: Load NL2SQL models
    print("[3/7] Loading NL2SQL models...")
    from intent_detector import load_model
    try:
        model, vectorizer = load_model(
            os.path.join(MODELS_DIR, "intent_model.pkl"),
            os.path.join(MODELS_DIR, "vectorizer.pkl"),
        )
        print(f"       Model loaded: {type(model).__name__}")
    except FileNotFoundError:
        print("       ERROR: Model files not found!")
        print("       Run 'python models/train_intent.py' first.")
        sys.exit(1)

    # Step 4: Run benchmark
    print(f"[4/7] Running benchmark on {len(sql_questions)} queries...")
    results = []
    for i, q in enumerate(sql_questions):
        qid = q["id"]
        dataset = q["dataset"]
        question_short = q["question"][:50]

        record = benchmark_query(q, db_path, dataframes, model, vectorizer)
        results.append(record)

        # Progress indicator
        status = "PASS" if record["result_match"] else "FAIL"
        intent_info = f"intent={'OK' if record['intent_match'] else 'MISS'}"
        print(f"  [{i+1:>3}/{len(sql_questions)}] ID={qid:>3} [{dataset:>20}] {status}  {intent_info}  {question_short}")

    # Step 5: Compute metrics
    print("[5/7] Computing metrics...")
    from metrics import compute_metrics, format_terminal_summary
    metrics_dict = compute_metrics(results)

    total_runtime = time.perf_counter() - t_start

    # Step 6: Save outputs
    print("[6/7] Saving outputs...")

    # CSV results
    results_csv_path = os.path.join(OUTPUT_DIR, "benchmark_results.csv")
    save_results_csv(results, results_csv_path)
    print(f"       Results CSV: {results_csv_path}")

    # JSON summary
    summary_json_path = os.path.join(OUTPUT_DIR, "benchmark_summary.json")
    save_summary_json(metrics_dict, summary_json_path, total_runtime)
    print(f"       Summary JSON: {summary_json_path}")

    # Markdown report
    report_md_path = os.path.join(OUTPUT_DIR, "benchmark_report.md")
    generate_report_markdown(metrics_dict, results, total_runtime, report_md_path)
    print(f"       Report MD: {report_md_path}")

    # Generate charts
    print("       Generating charts...")
    try:
        import importlib.util
        chart_path = os.path.join(BENCHMARK_DIR, "generate_charts.py")
        spec = importlib.util.spec_from_file_location("generate_charts", chart_path)
        chart_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(chart_mod)
        chart_mod.main()
    except Exception as e:
        print(f"       Chart generation skipped: {e}")

    # Step 7: Print summary
    print("[7/7] Benchmark complete!")
    print(format_terminal_summary(metrics_dict, total_runtime))

    # Print per-intent summary
    bi = metrics_dict["by_intent"]
    if bi:
        print()
        print("Per-Intent Breakdown:")
        print(f"  {'Intent':<10} {'Total':>6} {'Intent%':>8} {'Result%':>8} {'Exact%':>8}")
        print(f"  {'-'*10} {'-'*6} {'-'*8} {'-'*8} {'-'*8}")
        for intent, info in sorted(bi.items()):
            print(f"  {intent:<10} {info['total']:>6} "
                  f"{info['intent_accuracy']:>7.2f}% "
                  f"{info['result_match_accuracy']:>7.2f}% "
                  f"{info['exact_sql_match_rate']:>7.2f}%")

    # Print per-dataset summary
    bd = metrics_dict["by_dataset"]
    if bd:
        print()
        print("Per-Dataset Breakdown:")
        print(f"  {'Dataset':<25} {'Total':>6} {'Result%':>8} {'Exact%':>8}")
        print(f"  {'-'*25} {'-'*6} {'-'*8} {'-'*8}")
        for ds, info in sorted(bd.items()):
            print(f"  {ds:<25} {info['total']:>6} "
                  f"{info['result_match_accuracy']:>7.2f}% "
                  f"{info['exact_sql_match_rate']:>7.2f}%")

    print()
    print(f"Full outputs saved to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
