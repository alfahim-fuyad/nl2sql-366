#!/usr/bin/env python3
"""
run_benchmark.py — End-to-end NL2SQL-366 benchmark pipeline.

Benchmark configuration:
    6 unique datasets
    30 SQL queries per dataset
    180 SQL queries total

Usage:
    cd E:\\nl2sql_cse366
    python -m benchmark.run_benchmark

Pipeline:
    1. Validate benchmark configuration
    2. Load all datasets into SQLite
    3. Load benchmark questions
    4. Load NL2SQL model
    5. Run all 180 benchmark queries
    6. Compute metrics and save outputs
    7. Generate charts and terminal summary
"""

import csv
import json
import os
import sys
import sqlite3
import time
import warnings
from datetime import datetime, timezone

import pandas as pd


# ============================================================
# WARNING SUPPRESSION
# ============================================================

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

BENCHMARK_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

CORE_DIR = os.path.join(
    PROJECT_ROOT,
    "core"
)

MODELS_DIR = os.path.join(
    PROJECT_ROOT,
    "models"
)

KNOWLEDGE_DIR = os.path.join(
    PROJECT_ROOT,
    "knowledge"
)

# Actual dataset location
DATASETS_DIR = os.path.join(
    BENCHMARK_DIR,
    "benchmark",
    "datasets"
)

# Questions file
QUESTIONS_PATH = os.path.join(
    BENCHMARK_DIR,
    "benchmark",
    "questions.json"
)

# Output
OUTPUT_DIR = os.path.join(
    BENCHMARK_DIR,
    "output"
)


# ============================================================
# IMPORT PATHS
# ============================================================

sys.path.insert(0, CORE_DIR)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, BENCHMARK_DIR)

# Make project root the working directory
os.chdir(PROJECT_ROOT)


# ============================================================
# BENCHMARK CONFIGURATION
# ============================================================

EXPECTED_DATASET_COUNT = 6
EXPECTED_QUERIES_PER_DATASET = 30
EXPECTED_TOTAL_QUERIES = 180


# ============================================================
# DATASET CONFIGURATION
# ============================================================
#
# IMPORTANT:
# These names MUST match the names used in questions.json.
#
# questions.json uses:
#
#   dengue_dataset
#   ecommerce_dataset
#   employee_dataset
#   housing_dataset
#   student_performance_dataset
#   temp_and_rain_dataset
#
# ============================================================

DATASETS = {

    "dengue_dataset": {
        "csv": "dengue.csv",
        "table": "dengue",
    },

    "ecommerce_dataset": {
        "csv": "E-commerce.csv",
        "table": "ecommerce_dataset",
    },

    "employee_dataset": {
        "csv": "Employee Dataset.csv",
        "table": "employee_dataset",
    },

    "housing_dataset": {
        "csv": "Housing.csv",
        "table": "housing",
    },

    "student_performance_dataset": {
        "csv": "Student_performance.csv",
        "table": "student_performance",
    },

    "temp_and_rain_dataset": {
        "csv": "Temp_and_rain.csv",
        "table": "temp_and_rain",
    },
}


# ============================================================
# DATASET ALIASES
# ============================================================
#
# This allows old/new question files to work safely.
#
# Example:
#   dengue -> dengue_dataset
#   housing -> housing_dataset
#
# ============================================================

DATASET_ALIASES = {

    "dengue":
        "dengue_dataset",

    "dengue_dataset":
        "dengue_dataset",

    "ecommerce":
        "ecommerce_dataset",

    "ecommerce_dataset":
        "ecommerce_dataset",

    "employee":
        "employee_dataset",

    "employee_dataset":
        "employee_dataset",

    "housing":
        "housing_dataset",

    "housing_dataset":
        "housing_dataset",

    "student_performance":
        "student_performance_dataset",

    "student_performance_dataset":
        "student_performance_dataset",

    "temp_and_rain":
        "temp_and_rain_dataset",

    "temp_and_rain_dataset":
        "temp_and_rain_dataset",
}


# ============================================================
# COLUMN CLEANING
# ============================================================

def _clean_column_name(col: str) -> str:

    return (
        str(col)
        .strip()
        .replace(" ", "_")
        .replace("-", "_")
    )


# ============================================================
# DATASET KEY NORMALIZATION
# ============================================================

def normalize_dataset_key(dataset_key: str) -> str:

    if dataset_key is None:
        raise ValueError(
            "Dataset key is None"
        )

    key = str(dataset_key).strip()

    if key in DATASET_ALIASES:
        return DATASET_ALIASES[key]

    raise ValueError(
        f"Unsupported dataset '{dataset_key}'"
    )


# ============================================================
# DATASET/TABLE RESOLUTION
# ============================================================

def get_table_for_dataset(
    dataset_key: str
) -> str:

    canonical_key = normalize_dataset_key(
        dataset_key
    )

    return DATASETS[
        canonical_key
    ]["table"]


# ============================================================
# DATASET VALIDATION
# ============================================================

def validate_dataset_configuration():

    print(
        "[CONFIG] Validating benchmark configuration..."
    )

    actual_dataset_count = len(DATASETS)

    if actual_dataset_count != EXPECTED_DATASET_COUNT:

        raise RuntimeError(
            f"Expected exactly "
            f"{EXPECTED_DATASET_COUNT} datasets, "
            f"found {actual_dataset_count}."
        )

    print(
        f"       [OK] {actual_dataset_count} unique datasets"
    )

    print(
        f"       [OK] "
        f"{EXPECTED_QUERIES_PER_DATASET} queries per dataset"
    )

    print(
        f"       [OK] "
        f"{EXPECTED_TOTAL_QUERIES} total queries"
    )


# ============================================================
# LOAD ALL DATASETS
# ============================================================

def load_all_datasets(
    db_path: str
) -> dict:

    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)

    dataframes = {}

    try:

        for dataset_key, meta in DATASETS.items():

            csv_path = os.path.join(
                DATASETS_DIR,
                meta["csv"]
            )

            print(
                f"       [OK] Loading "
                f"{dataset_key:<25} "
                f"{meta['csv']}"
            )

            if not os.path.exists(csv_path):

                raise FileNotFoundError(
                    f"Dataset not found:\n"
                    f"{csv_path}"
                )

            df = pd.read_csv(
                csv_path
            )

            # Clean columns
            df.columns = [
                _clean_column_name(c)
                for c in df.columns
            ]

            # Save dataframe
            dataframes[
                dataset_key
            ] = df

            # Main table
            df.to_sql(
                meta["table"],
                conn,
                if_exists="replace",
                index=False
            )

            # Dataset-compatible alias
            if meta["table"] != dataset_key:

                df.to_sql(
                    dataset_key,
                    conn,
                    if_exists="replace",
                    index=False
                )

            print(
                f"                 "
                f"{len(df):>6} rows -> "
                f"{meta['table']}"
            )

    finally:

        conn.close()

    return dataframes


# ============================================================
# GET DATAFRAME
# ============================================================

def get_dataframe_for_dataset(
    dataset_key: str,
    dataframes: dict
) -> pd.DataFrame:

    canonical_key = normalize_dataset_key(
        dataset_key
    )

    if canonical_key in dataframes:

        return dataframes[
            canonical_key
        ]

    meta = DATASETS[
        canonical_key
    ]

    csv_path = os.path.join(
        DATASETS_DIR,
        meta["csv"]
    )

    if not os.path.exists(csv_path):

        raise FileNotFoundError(
            f"Dataset not found: {csv_path}"
        )

    df = pd.read_csv(
        csv_path
    )

    df.columns = [
        _clean_column_name(c)
        for c in df.columns
    ]

    return df


# ============================================================
# LOAD QUESTIONS
# ============================================================

def load_questions():

    if not os.path.exists(
        QUESTIONS_PATH
    ):

        raise FileNotFoundError(
            f"Questions file not found:\n"
            f"{QUESTIONS_PATH}"
        )

    with open(
        QUESTIONS_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        all_questions = json.load(f)

    sql_questions = [
        q
        for q in all_questions
        if q.get("type") == "sql"
        and "sql" in q
    ]

    print(
        f"       [OK] "
        f"{len(sql_questions)} existing SQL queries"
    )

    # --------------------------------------------------------
    # Query ID validation
    # --------------------------------------------------------

    ids = [
        q.get("id")
        for q in sql_questions
    ]

    if len(ids) != len(set(ids)):

        raise RuntimeError(
            "Duplicate query IDs found."
        )

    print(
        f"       [OK] "
        f"{len(set(ids))} unique query IDs"
    )

    # --------------------------------------------------------
    # Dataset validation + normalization
    # --------------------------------------------------------

    dataset_counts = {}

    normalized_questions = []

    for q in sql_questions:

        original_dataset = q.get(
            "dataset"
        )

        try:

            canonical_dataset = (
                normalize_dataset_key(
                    original_dataset
                )
            )

        except ValueError as e:

            raise RuntimeError(
                f"{e} "
                f"in query ID={q.get('id')}"
            )

        # Normalize dataset name
        q_copy = dict(q)

        q_copy["dataset"] = (
            canonical_dataset
        )

        normalized_questions.append(
            q_copy
        )

        dataset_counts[
            canonical_dataset
        ] = (
            dataset_counts.get(
                canonical_dataset,
                0
            ) + 1
        )

    # --------------------------------------------------------
    # Dataset count validation
    # --------------------------------------------------------

    if len(dataset_counts) != EXPECTED_DATASET_COUNT:

        raise RuntimeError(
            f"Expected exactly "
            f"{EXPECTED_DATASET_COUNT} unique datasets, "
            f"found {len(dataset_counts)}."
        )

    print(
        f"       [OK] "
        f"{len(dataset_counts)} unique datasets"
    )

    # --------------------------------------------------------
    # Per dataset query count
    # --------------------------------------------------------

    for dataset_key in DATASETS:

        count = dataset_counts.get(
            dataset_key,
            0
        )

        if count != EXPECTED_QUERIES_PER_DATASET:

            raise RuntimeError(
                f"Dataset '{dataset_key}' has "
                f"{count} queries. "
                f"Expected exactly "
                f"{EXPECTED_QUERIES_PER_DATASET}."
            )

    # --------------------------------------------------------
    # Total query count
    # --------------------------------------------------------

    total = len(normalized_questions)

    if total != EXPECTED_TOTAL_QUERIES:

        raise RuntimeError(
            f"Expected exactly "
            f"{EXPECTED_TOTAL_QUERIES} SQL queries, "
            f"found {total}."
        )

    print(
        f"       [OK] "
        f"{total} total SQL queries"
    )

    # --------------------------------------------------------
    # Dataset distribution
    # --------------------------------------------------------

    for dataset_key in sorted(
        dataset_counts
    ):

        print(
            f"       [OK] "
            f"{dataset_key:<30} "
            f"{dataset_counts[dataset_key]:>3} queries"
        )

    return normalized_questions


# ============================================================
# SQL EXECUTION
# ============================================================

def execute_sql(
    sql: str,
    db_path: str
):

    conn = sqlite3.connect(
        db_path
    )

    try:

        cur = conn.cursor()

        cur.execute(sql)

        rows = cur.fetchall()

        columns = (
            [d[0] for d in cur.description]
            if cur.description
            else []
        )

        return columns, rows

    finally:

        conn.close()


# ============================================================
# EXPECTED INTENT
# ============================================================

def extract_expected_intent(
    sql: str
) -> str:

    sql_upper = (
        sql.strip()
        .upper()
    )

    if "COUNT(" in sql_upper:
        return "COUNT"

    if "SUM(" in sql_upper:
        return "SUM"

    if "AVG(" in sql_upper:
        return "AVG"

    if "MIN(" in sql_upper:
        return "MIN"

    if "MAX(" in sql_upper:
        return "MAX"

    return "SELECT"


# ============================================================
# INTENT NORMALIZATION
# ============================================================

def normalize_intent(
    intent
):

    if intent is None:
        return None

    value = str(
        intent
    ).strip().upper()

    # Common aliases
    aliases = {

        "COUNT_ROWS":
            "COUNT",

        "COUNT_ROW":
            "COUNT",

        "COUNTS":
            "COUNT",

        "SUMMATION":
            "SUM",

        "TOTAL":
            "SUM",

        "AVERAGE":
            "AVG",

        "MEAN":
            "AVG",

        "MINIMUM":
            "MIN",

        "MAXIMUM":
            "MAX",

        "RETRIEVE":
            "SELECT",

        "QUERY":
            "SELECT",

    }

    return aliases.get(
        value,
        value
    )


# ============================================================
# NL2SQL PIPELINE
# ============================================================

def run_nl2sql_pipeline(
    question: str,
    schema: dict,
    model,
    vectorizer,
    table_name: str,
    db_path: str
):

    from intent_detector import (
        predict_intent
    )

    from sql_generator import (
        build_query,
        query_to_sql
    )

    from sql_validator import (
        validate_sql
    )

    result = {

        "predicted_intent":
            None,

        "generated_sql":
            None,

        "valid_sql":
            False,

        "validation_message":
            "",

        "gen_cols":
            None,

        "gen_rows":
            None,

        "gen_time_ms":
            0,

        "exec_time_ms":
            0,

        "execution_success":
            False,

        "error_message":
            "",
    }

    # --------------------------------------------------------
    # Intent detection
    # --------------------------------------------------------

    try:

        raw_intent = predict_intent(
            question,
            model,
            vectorizer
        )

        result[
            "predicted_intent"
        ] = normalize_intent(
            raw_intent
        )

    except Exception as e:

        result[
            "error_message"
        ] = (
            f"Intent detection failed: {e}"
        )

        return result

    # --------------------------------------------------------
    # Query building
    # --------------------------------------------------------

    try:

        query_struct = build_query(
            question,
            schema,
            result[
                "predicted_intent"
            ]
        )

    except Exception as e:

        result[
            "error_message"
        ] = (
            f"Query building failed: {e}"
        )

        return result

    # --------------------------------------------------------
    # SQL generation
    # --------------------------------------------------------

    t0 = time.perf_counter()

    try:

        sql = query_to_sql(
            query_struct,
            table_name
        )

        result[
            "generated_sql"
        ] = sql

    except Exception as e:

        result[
            "error_message"
        ] = (
            f"SQL generation failed: {e}"
        )

        return result

    finally:

        result[
            "gen_time_ms"
        ] = round(
            (
                time.perf_counter()
                - t0
            ) * 1000,
            2
        )

    # --------------------------------------------------------
    # SQL validation
    # --------------------------------------------------------

    try:

        is_valid, msg = validate_sql(
            sql,
            schema,
            table_name
        )

        result[
            "valid_sql"
        ] = bool(
            is_valid
        )

        result[
            "validation_message"
        ] = msg or ""

    except Exception as e:

        result[
            "valid_sql"
        ] = False

        result[
            "validation_message"
        ] = str(e)

    # --------------------------------------------------------
    # SQL execution
    # --------------------------------------------------------

    t0 = time.perf_counter()

    try:

        cols, rows = execute_sql(
            sql,
            db_path
        )

        result[
            "gen_cols"
        ] = cols

        result[
            "gen_rows"
        ] = rows

        result[
            "execution_success"
        ] = True

    except Exception as e:

        result[
            "execution_success"
        ] = False

        result[
            "error_message"
        ] = (
            f"Execution error: {e}"
        )

    finally:

        result[
            "exec_time_ms"
        ] = round(
            (
                time.perf_counter()
                - t0
            ) * 1000,
            2
        )

    return result


# ============================================================
# BENCHMARK SINGLE QUERY
# ============================================================

def benchmark_query(
    query_item: dict,
    db_path: str,
    dataframes: dict,
    model,
    vectorizer
):

    from schema_reader import (
        read_schema
    )

    from result_comparator import (
        compare_results,
        classify_failure
    )

    query_id = query_item[
        "id"
    ]

    question = query_item[
        "question"
    ]

    dataset_key = normalize_dataset_key(
        query_item[
            "dataset"
        ]
    )

    ref_sql = query_item[
        "sql"
    ]

    record = {

        "query_id":
            query_id,

        "question":
            question,

        "dataset":
            dataset_key,

        "reference_sql":
            ref_sql,

        "generated_sql":
            None,

        "expected_intent":
            extract_expected_intent(
                ref_sql
            ),

        "predicted_intent":
            None,

        "ref_cols":
            None,

        "ref_rows":
            None,

        "gen_cols":
            None,

        "gen_rows":
            None,

        "result_match":
            False,

        "exact_sql_match":
            False,

        "intent_match":
            False,

        "valid_sql":
            False,

        "execution_success":
            False,

        "gen_time_ms":
            0,

        "exec_time_ms":
            0,

        "error_message":
            "",

        "validation_message":
            "",

        "error_category":
            "unknown",

        "result_comparison":
            {},
    }

    # --------------------------------------------------------
    # Resolve table
    # --------------------------------------------------------

    try:

        table_name = (
            get_table_for_dataset(
                dataset_key
            )
        )

    except Exception as e:

        record[
            "error_message"
        ] = str(e)

        record[
            "error_category"
        ] = "schema_error"

        return record

    # --------------------------------------------------------
    # Reference SQL
    # --------------------------------------------------------

    try:

        ref_cols, ref_rows = execute_sql(
            ref_sql,
            db_path
        )

        record[
            "ref_cols"
        ] = ref_cols

        record[
            "ref_rows"
        ] = ref_rows

    except Exception as e:

        record[
            "error_message"
        ] = (
            f"Reference SQL execution failed: {e}"
        )

        record[
            "error_category"
        ] = "reference_error"

        return record

    # --------------------------------------------------------
    # Schema
    # --------------------------------------------------------

    try:

        df = get_dataframe_for_dataset(
            dataset_key,
            dataframes
        )

        schema = read_schema(
            df
        )

    except Exception as e:

        record[
            "error_message"
        ] = (
            f"Schema loading failed: {e}"
        )

        record[
            "error_category"
        ] = "schema_error"

        return record

    # --------------------------------------------------------
    # NL2SQL
    # --------------------------------------------------------

    nl2sql_result = run_nl2sql_pipeline(

        question=question,

        schema=schema,

        model=model,

        vectorizer=vectorizer,

        table_name=table_name,

        db_path=db_path
    )

    # --------------------------------------------------------
    # Copy results
    # --------------------------------------------------------

    for key in [

        "predicted_intent",
        "generated_sql",
        "valid_sql",
        "validation_message",
        "gen_cols",
        "gen_rows",
        "gen_time_ms",
        "exec_time_ms",
        "execution_success",
        "error_message",

    ]:

        record[key] = (
            nl2sql_result.get(key)
        )

    # --------------------------------------------------------
    # Intent match
    # --------------------------------------------------------

    expected_intent = (
        normalize_intent(
            record[
                "expected_intent"
            ]
        )
    )

    predicted_intent = (
        normalize_intent(
            record[
                "predicted_intent"
            ]
        )
    )

    record[
        "expected_intent"
    ] = expected_intent

    record[
        "predicted_intent"
    ] = predicted_intent

    record[
        "intent_match"
    ] = (
        predicted_intent is not None
        and
        predicted_intent
        == expected_intent
    )

    # --------------------------------------------------------
    # Exact SQL match
    # --------------------------------------------------------

    if record[
        "generated_sql"
    ]:

        ref_norm = " ".join(
            ref_sql
            .strip()
            .split()
        ).upper()

        gen_norm = " ".join(
            record[
                "generated_sql"
            ]
            .strip()
            .split()
        ).upper()

        record[
            "exact_sql_match"
        ] = (
            ref_norm == gen_norm
        )

    # --------------------------------------------------------
    # Result comparison
    # --------------------------------------------------------

    if (

        record[
            "ref_rows"
        ] is not None

        and

        record[
            "execution_success"
        ]

        and

        record[
            "gen_rows"
        ] is not None

    ):

        try:

            comparison = compare_results(

                record[
                    "ref_cols"
                ],

                record[
                    "ref_rows"
                ],

                record[
                    "gen_cols"
                ],

                record[
                    "gen_rows"
                ],

                ref_sql,

                record[
                    "generated_sql"
                ] or ""
            )

            record[
                "result_match"
            ] = bool(
                comparison.get(
                    "match",
                    False
                )
            )

            record[
                "result_comparison"
            ] = comparison

        except Exception as e:

            record[
                "error_message"
            ] = (
                f"Result comparison failed: {e}"
            )

            record[
                "error_category"
            ] = "comparison_error"

    # --------------------------------------------------------
    # Failure classification
    # --------------------------------------------------------

    if not record[
        "result_match"
    ]:

        try:

            record[
                "error_category"
            ] = classify_failure(
                record
            )

        except Exception:

            if not record[
                "generated_sql"
            ]:

                record[
                    "error_category"
                ] = "generation_error"

            elif not record[
                "valid_sql"
            ]:

                record[
                    "error_category"
                ] = "invalid_sql"

            elif not record[
                "execution_success"
            ]:

                record[
                    "error_category"
                ] = "execution_error"

            else:

                record[
                    "error_category"
                ] = "wrong_result"

    else:

        record[
            "error_category"
        ] = "correct"

    return record


# ============================================================
# SAVE RESULTS CSV
# ============================================================

def save_results_csv(
    results: list,
    path: str
):

    fieldnames = [

        "query_id",
        "question",
        "dataset",

        "reference_sql",
        "generated_sql",

        "expected_intent",
        "predicted_intent",
        "intent_match",

        "valid_sql",
        "execution_success",

        "result_match",
        "exact_sql_match",

        "gen_time_ms",
        "exec_time_ms",

        "error_category",
        "error_message",
    ]

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )

        writer.writeheader()

        for result in results:

            row = dict(
                result
            )

            row[
                "error_message"
            ] = (
                row.get(
                    "error_message"
                )
                or ""
            )[:500]

            writer.writerow(
                row
            )


# ============================================================
# SAVE QUESTIONS CSV
# ============================================================

def save_queries_csv(
    questions: list,
    path: str
):

    fieldnames = [
        "id",
        "dataset",
        "question",
        "sql",
        "expected_answer",
    ]

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )

        writer.writeheader()

        for q in questions:

            if (
                q.get("type")
                == "sql"
                and
                "sql" in q
            ):

                writer.writerow(
                    q
                )


# ============================================================
# SAVE SUMMARY JSON
# ============================================================

def save_summary_json(
    metrics_dict: dict,
    path: str,
    total_runtime_s: float
):

    output = {

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "total_runtime_seconds":
            round(
                total_runtime_s,
                2
            ),

        "benchmark_configuration": {

            "datasets":
                EXPECTED_DATASET_COUNT,

            "queries_per_dataset":
                EXPECTED_QUERIES_PER_DATASET,

            "total_queries":
                EXPECTED_TOTAL_QUERIES,
        },

        "metrics":
            metrics_dict,
    }

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            indent=2,
            default=str
        )


# ============================================================
# MARKDOWN REPORT
# ============================================================

def generate_report_markdown(
    metrics_dict: dict,
    results: list,
    total_runtime_s: float,
    output_path: str
):

    o = metrics_dict[
        "overall"
    ]

    ea = metrics_dict[
        "error_analysis"
    ]

    by_intent = metrics_dict[
        "by_intent"
    ]

    by_dataset = metrics_dict[
        "by_dataset"
    ]

    f1_scores = metrics_dict[
        "f1_scores"
    ]

    lines = []

    lines.append(
        "# NL2SQL-366 Benchmark Report"
    )

    lines.append("")

    lines.append(
        f"**Generated:** "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )

    lines.append(
        f"**Total Runtime:** "
        f"{total_runtime_s:.2f} seconds"
    )

    lines.append("")

    # --------------------------------------------------------
    # Overview
    # --------------------------------------------------------

    lines.append(
        "## 1. Benchmark Overview"
    )

    lines.append("")

    lines.append(
        f"- **Total SQL Queries Evaluated:** "
        f"{o['total_queries']}"
    )

    unique_ds = sorted(
        set(
            r["dataset"]
            for r in results
        )
    )

    lines.append(
        f"- **Number of Datasets/Schemas:** "
        f"{len(unique_ds)}"
    )

    lines.append(
        f"- **Datasets:** "
        f"{', '.join(unique_ds)}"
    )

    lines.append(
        f"- **Queries per Dataset:** "
        f"{EXPECTED_QUERIES_PER_DATASET}"
    )

    intent_dist = {}

    for r in results:

        intent = r[
            "expected_intent"
        ]

        intent_dist[
            intent
        ] = (
            intent_dist.get(
                intent,
                0
            ) + 1
        )

    lines.append(
        "- **Intent Distribution:**"
    )

    for intent in sorted(
        intent_dist
    ):

        lines.append(
            f"  - {intent}: "
            f"{intent_dist[intent]} queries"
        )

    lines.append("")

    # --------------------------------------------------------
    # Overall
    # --------------------------------------------------------

    lines.append(
        "## 2. Overall Results"
    )

    lines.append("")

    lines.append(
        "| Metric | Score |"
    )

    lines.append(
        "|--------|-------|"
    )

    lines.append(
        f"| Intent Accuracy | "
        f"{o['intent_accuracy']:.2f}% |"
    )

    lines.append(
        f"| Valid SQL | "
        f"{o['valid_sql_rate']:.2f}% |"
    )

    lines.append(
        f"| Execution Success | "
        f"{o['execution_success_rate']:.2f}% |"
    )

    lines.append(
        f"| Result Match Accuracy | "
        f"{o['result_match_accuracy']:.2f}% |"
    )

    lines.append(
        f"| Exact SQL Match | "
        f"{o['exact_sql_match_rate']:.2f}% |"
    )

    lines.append(
        f"| Macro F1 | "
        f"{metrics_dict['macro_f1']:.2f}% |"
    )

    lines.append(
        f"| Avg SQL Generation Time | "
        f"{o['avg_generation_time_ms']:.2f} ms |"
    )

    lines.append(
        f"| Avg Execution Time | "
        f"{o['avg_execution_time_ms']:.2f} ms |"
    )

    lines.append(
        f"| Total Passed | "
        f"{o['passed']} |"
    )

    lines.append(
        f"| Total Failed | "
        f"{o['failed']} |"
    )

    lines.append("")

    lines.append(
        "![Overall Metrics]"
        "(chart_overall_metrics.png)"
    )

    lines.append("")

    # --------------------------------------------------------
    # Method comparison
    # --------------------------------------------------------

    lines.append(
        "### 2.1 Method Comparison"
    )

    lines.append("")

    lines.append(
        "| Method | Description | Accuracy |"
    )

    lines.append(
        "|--------|-------------|----------|"
    )

    lines.append(
        "| Reference SQL | "
        "Ground-truth SQL executed directly | "
        "100.00% |"
    )

    lines.append(
        f"| NL2SQL-366 | "
        f"Natural language to SQL pipeline | "
        f"{o['result_match_accuracy']:.2f}% |"
    )

    lines.append("")

    lines.append(
        "> Reference SQL is treated as ground truth. "
        "NL2SQL-366 is correct when generated SQL produces "
        "the same result as the reference SQL."
    )

    lines.append("")

    lines.append(
        "![Pipeline Funnel]"
        "(chart_pipeline_funnel.png)"
    )

    lines.append("")

    # --------------------------------------------------------
    # Intent
    # --------------------------------------------------------

    lines.append(
        "## 3. Per-Intent Results"
    )

    lines.append("")

    lines.append(
        "| Intent | Queries | Intent Acc. | "
        "Result Match | Exact SQL | Valid SQL | Exec Success |"
    )

    lines.append(
        "|--------|---------|-------------|--------------|"
        "-----------|-----------|-------------|"
    )

    for intent, info in sorted(
        by_intent.items()
    ):

        lines.append(
            f"| {intent} | "
            f"{info['total']} | "
            f"{info['intent_accuracy']:.2f}% | "
            f"{info['result_match_accuracy']:.2f}% | "
            f"{info['exact_sql_match_rate']:.2f}% | "
            f"{info['valid_sql_rate']:.2f}% | "
            f"{info['execution_success_rate']:.2f}% |"
        )

    lines.append("")

    lines.append(
        "![Intent Accuracy]"
        "(chart_intent_accuracy.png)"
    )

    lines.append("")

    lines.append(
        "![Result Match by Intent]"
        "(chart_result_match.png)"
    )

    lines.append("")

    # --------------------------------------------------------
    # Dataset
    # --------------------------------------------------------

    lines.append(
        "## 4. Per-Dataset Results"
    )

    lines.append("")

    lines.append(
        "| Dataset | Queries | Intent Acc. | "
        "Result Match | Exact SQL |"
    )

    lines.append(
        "|---------|---------|-------------|"
        "--------------|-----------|"
    )

    for ds, info in sorted(
        by_dataset.items()
    ):

        lines.append(
            f"| {ds} | "
            f"{info['total']} | "
            f"{info['intent_accuracy']:.2f}% | "
            f"{info['result_match_accuracy']:.2f}% | "
            f"{info['exact_sql_match_rate']:.2f}% |"
        )

    lines.append("")

    lines.append(
        "![Dataset Accuracy]"
        "(chart_dataset_accuracy.png)"
    )

    lines.append("")

    # --------------------------------------------------------
    # F1
    # --------------------------------------------------------

    lines.append(
        "## 5. Precision, Recall, F1 by Intent"
    )

    lines.append("")

    lines.append(
        "| Intent | Precision | Recall | F1 | Support |"
    )

    lines.append(
        "|--------|-----------|--------|-----|---------|"
    )

    for intent, f1 in sorted(
        f1_scores.items()
    ):

        lines.append(
            f"| {intent} | "
            f"{f1['precision']:.2f}% | "
            f"{f1['recall']:.2f}% | "
            f"{f1['f1']:.2f}% | "
            f"{f1['support']} |"
        )

    lines.append("")

    # --------------------------------------------------------
    # Errors
    # --------------------------------------------------------

    lines.append(
        "## 6. Error Analysis"
    )

    lines.append("")

    lines.append(
        f"**Total Failed Queries:** "
        f"{ea['total_failed']}"
    )

    lines.append("")

    if ea[
        "categories"
    ]:

        lines.append(
            "**Error Distribution:**"
        )

        lines.append("")

        lines.append(
            "| Error Category | Count |"
        )

        lines.append(
            "|----------------|-------|"
        )

        for cat, cnt in (
            ea[
                "categories"
            ].items()
        ):

            lines.append(
                f"| {cat} | {cnt} |"
            )

        lines.append("")

    lines.append(
        "![Error Distribution]"
        "(chart_error_distribution.png)"
    )

    lines.append("")

    # --------------------------------------------------------
    # Failed queries
    # --------------------------------------------------------

    if ea[
        "failed_queries"
    ]:

        lines.append(
            "**Failed Query Details:**"
        )

        lines.append("")

        lines.append(
            "| ID | Dataset | Question | Expected Intent | "
            "Predicted | Error |"
        )

        lines.append(
            "|----|---------|----------|-----------------|"
            "-----------|-------|"
        )

        for fq in ea[
            "failed_queries"
        ][:50]:

            q_short = (
                fq.get(
                    "question",
                    ""
                )[:50]
            )

            lines.append(
                f"| {fq['id']} | "
                f"{fq['dataset']} | "
                f"{q_short} | "
                f"{fq['expected_intent']} | "
                f"{fq['predicted_intent']} | "
                f"{fq['error_category']} |"
            )

        lines.append("")

    # --------------------------------------------------------
    # Reference vs generated
    # --------------------------------------------------------

    lines.append(
        "## 7. Reference vs Generated SQL Analysis"
    )

    lines.append("")

    exact_sql_and_result = 0
    diff_sql_same_result = 0
    valid_wrong_result = 0
    invalid_sql = 0
    exec_failed = 0

    for r in results:

        if (
            r["exact_sql_match"]
            and r["result_match"]
        ):

            exact_sql_and_result += 1

        elif (
            not r["exact_sql_match"]
            and r["result_match"]
        ):

            diff_sql_same_result += 1

        elif (
            r["valid_sql"]
            and r["execution_success"]
            and not r["result_match"]
        ):

            valid_wrong_result += 1

        elif not r["valid_sql"]:

            invalid_sql += 1

        elif not r["execution_success"]:

            exec_failed += 1

        else:

            valid_wrong_result += 1

    total = len(results) or 1

    lines.append(
        "| Category | Count | Percentage |"
    )

    lines.append(
        "|----------|-------|------------|"
    )

    lines.append(
        f"| SQL exactly identical, result correct | "
        f"{exact_sql_and_result} | "
        f"{_pct(exact_sql_and_result, total):.2f}% |"
    )

    lines.append(
        f"| SQL different, but result identical | "
        f"{diff_sql_same_result} | "
        f"{_pct(diff_sql_same_result, total):.2f}% |"
    )

    lines.append(
        f"| SQL valid but result incorrect | "
        f"{valid_wrong_result} | "
        f"{_pct(valid_wrong_result, total):.2f}% |"
    )

    lines.append(
        f"| SQL invalid | "
        f"{invalid_sql} | "
        f"{_pct(invalid_sql, total):.2f}% |"
    )

    lines.append(
        f"| SQL execution failed | "
        f"{exec_failed} | "
        f"{_pct(exec_failed, total):.2f}% |"
    )

    lines.append("")

    # --------------------------------------------------------
    # Examples
    # --------------------------------------------------------

    lines.append(
        "### Examples"
    )

    lines.append("")

    # Correct example
    for r in results:

        if (
            r["result_match"]
        ):

            lines.append(
                f"**Correct Result "
                f"(ID {r['query_id']}):**"
            )

            lines.append(
                f"- Question: {r['question']}"
            )

            lines.append(
                f"- Reference: `{r['reference_sql']}`"
            )

            lines.append(
                f"- Generated: `{r['generated_sql']}`"
            )

            lines.append("")

            break

    # Wrong result
    for r in results:

        if (
            r["valid_sql"]
            and r["execution_success"]
            and not r["result_match"]
        ):

            lines.append(
                f"**Valid SQL + Wrong Result "
                f"(ID {r['query_id']}):**"
            )

            lines.append(
                f"- Question: {r['question']}"
            )

            lines.append(
                f"- Reference: `{r['reference_sql']}`"
            )

            lines.append(
                f"- Generated: `{r['generated_sql']}`"
            )

            lines.append(
                f"- Error: {r['error_category']}"
            )

            lines.append("")

            break

    # Invalid SQL
    for r in results:

        if (
            not r["valid_sql"]
            and r["generated_sql"]
        ):

            lines.append(
                f"**Invalid SQL "
                f"(ID {r['query_id']}):**"
            )

            lines.append(
                f"- Question: {r['question']}"
            )

            lines.append(
                f"- Generated: `{r['generated_sql']}`"
            )

            lines.append(
                f"- Validation: "
                f"{r.get('validation_message', 'N/A')}"
            )

            lines.append("")

            break

    # --------------------------------------------------------
    # Write
    # --------------------------------------------------------

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(lines)
        )


# ============================================================
# PERCENTAGE
# ============================================================

def _pct(
    n,
    d
):

    return (
        round(
            100.0 * n / d,
            2
        )
        if d
        else 0.0
    )


# ============================================================
# MAIN
# ============================================================

def main():

    t_start = time.perf_counter()

    print("=" * 60)
    print(
        "NL2SQL-366 BENCHMARK"
    )
    print("=" * 60)
    print()

    # ========================================================
    # CONFIG
    # ========================================================

    try:

        validate_dataset_configuration()

    except Exception as e:

        print(
            f"       ERROR: {e}"
        )

        return 1

    # ========================================================
    # OUTPUT DIRECTORY
    # ========================================================

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    # ========================================================
    # STEP 1 — DATABASE
    # ========================================================

    db_path = os.path.join(
        OUTPUT_DIR,
        "benchmark.db"
    )

    print()
    print(
        "[1/7] Loading datasets into SQLite..."
    )

    try:

        dataframes = load_all_datasets(
            db_path
        )

    except Exception as e:

        print(
            f"       ERROR: Dataset loading failed: {e}"
        )

        return 1

    print(
        f"       [OK] "
        f"{len(dataframes)} datasets loaded into "
        f"{db_path}"
    )

    # ========================================================
    # STEP 2 — QUESTIONS
    # ========================================================

    print(
        "[2/7] Loading benchmark questions..."
    )

    try:

        sql_questions = load_questions()

    except Exception as e:

        print(
            f"       ERROR: Question validation failed:"
        )

        print(
            f"       {e}"
        )

        return 1

    # Save normalized questions
    queries_csv_path = os.path.join(
        OUTPUT_DIR,
        "benchmark_queries.csv"
    )

    save_queries_csv(
        sql_questions,
        queries_csv_path
    )

    print(
        f"       Queries saved to "
        f"{queries_csv_path}"
    )

    # ========================================================
    # STEP 3 — MODEL
    # ========================================================

    print(
        "[3/7] Loading NL2SQL models..."
    )

    try:

        from intent_detector import (
            load_model
        )

        model, vectorizer = load_model(

            os.path.join(
                MODELS_DIR,
                "intent_model.pkl"
            ),

            os.path.join(
                MODELS_DIR,
                "vectorizer.pkl"
            )
        )

        print(
            f"       Model loaded: "
            f"{type(model).__name__}"
        )

    except FileNotFoundError:

        print(
            "       ERROR: Model files not found!"
        )

        print(
            "       Run "
            "'python models/train_intent.py' first."
        )

        return 1

    except Exception as e:

        print(
            f"       ERROR: Model loading failed: {e}"
        )

        return 1

    # ========================================================
    # STEP 4 — RUN BENCHMARK
    # ========================================================

    print(
        f"[4/7] Running benchmark on "
        f"{len(sql_questions)} queries..."
    )

    results = []

    total_queries = len(
        sql_questions
    )

    for i, q in enumerate(
        sql_questions
    ):

        qid = q[
            "id"
        ]

        dataset = q[
            "dataset"
        ]

        question_short = (
            q[
                "question"
            ][:50]
        )

        try:

            record = benchmark_query(

                q,

                db_path,

                dataframes,

                model,

                vectorizer
            )

        except Exception as e:

            record = {

                "query_id":
                    qid,

                "question":
                    q.get(
                        "question",
                        ""
                    ),

                "dataset":
                    normalize_dataset_key(
                        dataset
                    ),

                "reference_sql":
                    q.get(
                        "sql",
                        ""
                    ),

                "generated_sql":
                    None,

                "expected_intent":
                    extract_expected_intent(
                        q.get(
                            "sql",
                            ""
                        )
                    ),

                "predicted_intent":
                    None,

                "ref_cols":
                    None,

                "ref_rows":
                    None,

                "gen_cols":
                    None,

                "gen_rows":
                    None,

                "result_match":
                    False,

                "exact_sql_match":
                    False,

                "intent_match":
                    False,

                "valid_sql":
                    False,

                "execution_success":
                    False,

                "gen_time_ms":
                    0,

                "exec_time_ms":
                    0,

                "error_message":
                    f"Unexpected benchmark error: {e}",

                "validation_message":
                    "",

                "error_category":
                    "benchmark_error",

                "result_comparison":
                    {},
            }

            print()
            print(
                f"       WARNING: Query ID={qid} "
                f"failed unexpectedly:"
            )

            print(
                f"       {e}"
            )

        results.append(
            record
        )

        status = (
            "PASS"
            if record[
                "result_match"
            ]
            else "FAIL"
        )

        intent_info = (
            "OK"
            if record[
                "intent_match"
            ]
            else "MISS"
        )

        print(
            f"  [{i + 1:>3}/{total_queries}] "
            f"ID={qid:>3} "
            f"[{dataset:>30}] "
            f"{status}  "
            f"intent={intent_info}  "
            f"{question_short}"
        )

    # ========================================================
    # STEP 5 — METRICS
    # ========================================================

    print(
        "[5/7] Computing metrics..."
    )

    try:

        from metrics import (
            compute_metrics,
            format_terminal_summary
        )

        metrics_dict = compute_metrics(
            results
        )

    except Exception as e:

        print(
            f"       ERROR: Metrics computation failed: {e}"
        )

        return 1

    total_runtime = (
        time.perf_counter()
        - t_start
    )

    # ========================================================
    # STEP 6 — SAVE OUTPUTS
    # ========================================================

    print(
        "[6/7] Saving outputs..."
    )

    # --------------------------------------------------------
    # Results CSV
    # --------------------------------------------------------

    results_csv_path = os.path.join(
        OUTPUT_DIR,
        "benchmark_results.csv"
    )

    save_results_csv(
        results,
        results_csv_path
    )

    print(
        f"       Results CSV: "
        f"{results_csv_path}"
    )

    # --------------------------------------------------------
    # Summary JSON
    # --------------------------------------------------------

    summary_json_path = os.path.join(
        OUTPUT_DIR,
        "benchmark_summary.json"
    )

    save_summary_json(
        metrics_dict,
        summary_json_path,
        total_runtime
    )

    print(
        f"       Summary JSON: "
        f"{summary_json_path}"
    )

    # --------------------------------------------------------
    # Markdown report
    # --------------------------------------------------------

    report_md_path = os.path.join(
        OUTPUT_DIR,
        "benchmark_report.md"
    )

    generate_report_markdown(
        metrics_dict,
        results,
        total_runtime,
        report_md_path
    )

    print(
        f"       Report MD: "
        f"{report_md_path}"
    )

    # --------------------------------------------------------
    # Charts
    # --------------------------------------------------------

    print(
        "       Generating charts..."
    )

    try:

        import importlib.util

        chart_path = os.path.join(
            BENCHMARK_DIR,
            "generate_charts.py"
        )

        if os.path.exists(
            chart_path
        ):

            spec = (
                importlib.util.spec_from_file_location(
                    "generate_charts",
                    chart_path
                )
            )

            chart_mod = (
                importlib.util.module_from_spec(
                    spec
                )
            )

            spec.loader.exec_module(
                chart_mod
            )

            chart_mod.main()

        else:

            print(
                "       Chart generator not found."
            )

    except Exception as e:

        print(
            f"       Chart generation skipped: {e}"
        )

    # ========================================================
    # STEP 7 — COMPLETE
    # ========================================================

    print(
        "[7/7] Benchmark complete!"
    )

    print()

    try:

        print(
            format_terminal_summary(
                metrics_dict,
                total_runtime
            )
        )

    except Exception as e:

        print(
            f"Summary formatting error: {e}"
        )

    # ========================================================
    # PER INTENT
    # ========================================================

    bi = metrics_dict.get(
        "by_intent",
        {}
    )

    if bi:

        print()
        print(
            "Per-Intent Breakdown:"
        )

        print(
            f"  {'Intent':<10} "
            f"{'Total':>6} "
            f"{'Intent%':>8} "
            f"{'Result%':>8} "
            f"{'Exact%':>8}"
        )

        print(
            f"  {'-' * 10} "
            f"{'-' * 6} "
            f"{'-' * 8} "
            f"{'-' * 8} "
            f"{'-' * 8}"
        )

        for intent, info in sorted(
            bi.items()
        ):

            print(
                f"  {intent:<10} "
                f"{info['total']:>6} "
                f"{info['intent_accuracy']:>7.2f}% "
                f"{info['result_match_accuracy']:>7.2f}% "
                f"{info['exact_sql_match_rate']:>7.2f}%"
            )

    # ========================================================
    # PER DATASET
    # ========================================================

    bd = metrics_dict.get(
        "by_dataset",
        {}
    )

    if bd:

        print()
        print(
            "Per-Dataset Breakdown:"
        )

        print(
            f"  {'Dataset':<30} "
            f"{'Total':>6} "
            f"{'Result%':>8} "
            f"{'Exact%':>8}"
        )

        print(
            f"  {'-' * 30} "
            f"{'-' * 6} "
            f"{'-' * 8} "
            f"{'-' * 8}"
        )

        for ds, info in sorted(
            bd.items()
        ):

            print(
                f"  {ds:<30} "
                f"{info['total']:>6} "
                f"{info['result_match_accuracy']:>7.2f}% "
                f"{info['exact_sql_match_rate']:>7.2f}%"
            )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    print()

    print(
        "=" * 60
    )

    print(
        "BENCHMARK CONFIGURATION CHECK"
    )

    print(
        "=" * 60
    )

    print(
        f"Datasets:             "
        f"{len(set(r['dataset'] for r in results))}"
    )

    print(
        f"Queries per dataset:  "
        f"{EXPECTED_QUERIES_PER_DATASET}"
    )

    print(
        f"Total queries:        "
        f"{len(results)}"
    )

    if (
        len(results)
        == EXPECTED_TOTAL_QUERIES
    ):

        print(
            "[OK] 180-query benchmark completed."
        )

    else:

        print(
            f"[WARNING] Expected "
            f"{EXPECTED_TOTAL_QUERIES}, "
            f"got {len(results)}."
        )

    print()

    print(
        f"Full outputs saved to: "
        f"{OUTPUT_DIR}/"
    )

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    sys.exit(
        main()
    )