"""Run the reproducible 100-query evaluation and write publication tables.

Usage:
    python benchmark/run_benchmark.py

The benchmark is intentionally self-contained: it creates five deterministic
CSV fixtures, loads each into an isolated SQLite database, evaluates three
intent-routing variants, and writes JSON/Markdown artifacts under results/.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from attribute_matcher import find_columns_with_positions
from dataset_loader import save_to_sqlite
from intent_detector import load_model, predict_intent
from operator_detector import detect_operators
from schema_reader import read_schema
from sql_generator import build_query, query_to_sql
from sql_validator import validate_sql
from tokenizer import tokenize

from fixtures import DATASETS, all_cases


MODEL_PATH = ROOT / "models" / "intent_model.pkl"
VECTORIZER_PATH = ROOT / "models" / "vectorizer.pkl"
TRAINING_PATH = ROOT / "training_data" / "intent_dataset.csv"
RESULTS_DIR = ROOT / "benchmark" / "results"
DATASET_DIR = ROOT / "benchmark" / "generated_datasets"


def _rule_intent(question: str) -> str:
    """A transparent lexical baseline for intent routing."""
    text = question.lower()
    if any(word in text for word in ("average", "avg", "mean")):
        return "AVG"
    if any(word in text for word in ("how many", "count", "number of", "total number")):
        return "COUNT"
    if any(word in text for word in ("maximum", "max", "greatest", "highest")):
        return "MAX"
    if any(word in text for word in ("minimum", "min", "lowest", "least")):
        return "MIN"
    if any(word in text for word in ("sum", "total")):
        return "SUM"
    return "SELECT"


def _canonical(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float):
        return round(value, 10)
    return value


def _rows_equal(actual, expected, ordered):
    actual_rows = [tuple(_canonical(v) for v in row) for row in actual]
    expected_rows = [tuple(_canonical(v) for v in row) for row in expected]
    if ordered:
        return actual_rows == expected_rows
    return Counter(actual_rows) == Counter(expected_rows)


def _row_f1(actual, expected):
    actual_rows = Counter(tuple(_canonical(v) for v in row) for row in actual)
    expected_rows = Counter(tuple(_canonical(v) for v in row) for row in expected)
    overlap = sum((actual_rows & expected_rows).values())
    actual_count = sum(actual_rows.values())
    expected_count = sum(expected_rows.values())
    precision = overlap / actual_count if actual_count else (1.0 if not expected_count else 0.0)
    recall = overlap / expected_count if expected_count else (1.0 if not actual_count else 0.0)
    return (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )


def _sqlite_query(db_path, sql):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(sql)
        return [item[0] for item in cursor.description or []], cursor.fetchall()


def _write_fixtures():
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    paths = {}
    for domain, rows in DATASETS.items():
        path = DATASET_DIR / f"{domain}.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        paths[domain] = path
    return paths


def _load_domain(domain, csv_path):
    df = pd.read_csv(csv_path)
    db_file = tempfile.NamedTemporaryFile(prefix=f"nl2sql_{domain}_", suffix=".db", delete=False)
    db_file.close()
    save_to_sqlite(df, db_file.name, "data")
    return df, db_file.name, read_schema(df)


def _method_intent(method, question, model, vectorizer):
    if method == "rule_based":
        return _rule_intent(question)
    if method == "ml_only":
        return str(model.predict(vectorizer.transform([question]))[0])
    return str(predict_intent(question, model, vectorizer))


def _evaluate_methods(paths):
    model, vectorizer = load_model(str(MODEL_PATH), str(VECTORIZER_PATH))
    methods = ("rule_based", "ml_only", "hybrid")
    records = []

    for domain, case_id, case in all_cases():
        df, db_path, schema = _load_domain(domain, paths[domain])
        try:
            gold_columns, gold_rows = _sqlite_query(db_path, case["gold_sql"])
            ordered = "ORDER BY" in case["gold_sql"].upper()
            for method in methods:
                started = time.perf_counter_ns()
                intent = _method_intent(method, case["question"], model, vectorizer)
                intent_ns = time.perf_counter_ns() - started
                try:
                    query = build_query(case["question"], schema, intent)
                    sql = query_to_sql(query)
                    valid, validation_message = validate_sql(sql, schema)
                    generated_columns, generated_rows = (
                        _sqlite_query(db_path, sql) if valid else ([], [])
                    )
                    result_match = (
                        valid
                        and generated_columns == gold_columns
                        and _rows_equal(generated_rows, gold_rows, ordered)
                    )
                    execution_f1 = _row_f1(generated_rows, gold_rows)
                    error = None
                except Exception as exc:
                    sql = None
                    valid = False
                    validation_message = str(exc)
                    result_match = False
                    execution_f1 = 0.0
                    error = type(exc).__name__
                records.append({
                    "case_id": case_id,
                    "domain": domain,
                    "category": case["category"],
                    "question": case["question"],
                    "expected_intent": case["expected_intent"],
                    "predicted_intent": intent,
                    "intent_correct": intent == case["expected_intent"],
                    "gold_sql": case["gold_sql"],
                    "generated_sql": sql,
                    "valid_sql": bool(valid),
                    "validation_message": validation_message,
                    "execution_correct": bool(result_match),
                    "execution_f1": round(execution_f1, 6),
                    "intent_latency_ms": intent_ns / 1_000_000,
                    "error": error,
                    "method": method,
                })
        finally:
            os.unlink(db_path)
    return records


def _metrics(records):
    by_method = {}
    for method in ("rule_based", "ml_only", "hybrid"):
        subset = [record for record in records if record["method"] == method]
        by_method[method] = {
            "queries": len(subset),
            "intent_accuracy": round(
                sum(r["intent_correct"] for r in subset) / len(subset), 6
            ),
            "execution_accuracy": round(
                sum(r["execution_correct"] for r in subset) / len(subset), 6
            ),
            "valid_sql_rate": round(
                sum(r["valid_sql"] for r in subset) / len(subset), 6
            ),
            "execution_f1": round(
                sum(r["execution_f1"] for r in subset) / len(subset), 6
            ),
        }
    return by_method


def _domain_metrics(records):
    output = {}
    for domain in DATASETS:
        subset = [r for r in records if r["domain"] == domain and r["method"] == "hybrid"]
        output[domain] = {
            "queries": len(subset),
            "execution_accuracy": round(
                sum(r["execution_correct"] for r in subset) / len(subset), 6
            ),
            "execution_f1": round(
                sum(r["execution_f1"] for r in subset) / len(subset), 6
            ),
        }
    return output


def _category_metrics(records):
    output = {}
    for category in sorted({r["category"] for r in records}):
        subset = [
            r for r in records
            if r["category"] == category and r["method"] == "hybrid"
        ]
        output[category] = {
            "queries": len(subset),
            "execution_accuracy": round(
                sum(r["execution_correct"] for r in subset) / len(subset), 6
            ),
        }
    return output


def _ml_metrics():
    data = pd.read_csv(TRAINING_PATH)
    questions = data.iloc[:, 0].astype(str)
    labels = data.iloc[:, 1].astype(str).str.strip()
    x_train, x_test, y_train, y_test = train_test_split(
        questions, labels, test_size=0.2, random_state=42, stratify=labels
    )
    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    x_train_vec = vectorizer.fit_transform(x_train)
    x_test_vec = vectorizer.transform(x_test)
    model = MultinomialNB()
    model.fit(x_train_vec, y_train)
    predictions = model.predict(x_test_vec)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, predictions, average="weighted", zero_division=0
    )
    labels_order = sorted(labels.unique())
    return {
        "dataset": str(TRAINING_PATH.relative_to(ROOT)),
        "examples": len(data),
        "train_examples": len(x_train),
        "test_examples": len(x_test),
        "accuracy": round(accuracy_score(y_test, predictions), 6),
        "weighted_precision": round(precision, 6),
        "weighted_recall": round(recall, 6),
        "weighted_f1": round(f1, 6),
        "class_support": {
            label: int((labels == label).sum()) for label in labels_order
        },
        "confusion_matrix_labels": labels_order,
        "confusion_matrix": confusion_matrix(
            y_test, predictions, labels=labels_order
        ).tolist(),
        "classification_report": classification_report(
            y_test, predictions, labels=labels_order, output_dict=True,
            zero_division=0,
        ),
    }


def _security_metrics():
    df = pd.DataFrame(DATASETS["students"])
    schema = read_schema(df)
    cases = [
        ("drop_table", 'DROP TABLE "data"', False),
        ("delete", 'DELETE FROM "data"', False),
        ("update", 'UPDATE "data" SET "GPA" = 0', False),
        ("insert", 'INSERT INTO "data" ("GPA") VALUES (0)', False),
        ("unknown_column", 'SELECT * FROM "data" WHERE "Secret" = 1', False),
        ("wrong_table", 'SELECT * FROM "other"', False),
        ("multiple_statements", 'SELECT * FROM "data"; DROP TABLE "data"', False),
        ("safe_control", 'SELECT * FROM "data"', True),
    ]
    results = []
    for case_id, sql, expected_valid in cases:
        actual_valid, message = validate_sql(sql, schema)
        results.append({
            "case": case_id,
            "expected_valid": expected_valid,
            "actual_valid": actual_valid,
            "passed": actual_valid == expected_valid,
            "message": message,
        })
    return {
        "cases": len(results),
        "passed": sum(item["passed"] for item in results),
        "pass_rate": round(sum(item["passed"] for item in results) / len(results), 6),
        "results": results,
    }


def _latency_metrics(paths):
    model, vectorizer = load_model(str(MODEL_PATH), str(VECTORIZER_PATH))
    measurements = []
    for domain, _, case in all_cases():
        df, db_path, schema = _load_domain(domain, paths[domain])
        try:
            started = time.perf_counter_ns()
            tokenize(case["question"])
            tokenization_ns = time.perf_counter_ns() - started

            started = time.perf_counter_ns()
            intent = predict_intent(case["question"], model, vectorizer)
            intent_ns = time.perf_counter_ns() - started

            started = time.perf_counter_ns()
            query = build_query(case["question"], schema, intent)
            matching_ns = time.perf_counter_ns() - started

            started = time.perf_counter_ns()
            sql = query_to_sql(query)
            generation_ns = time.perf_counter_ns() - started

            started = time.perf_counter_ns()
            valid, _ = validate_sql(sql, schema)
            validation_ns = time.perf_counter_ns() - started

            started = time.perf_counter_ns()
            if valid:
                _sqlite_query(db_path, sql)
            execution_ns = time.perf_counter_ns() - started
            total_ns = (
                tokenization_ns + intent_ns + matching_ns
                + generation_ns + validation_ns + execution_ns
            )
            measurements.append({
                "tokenization": tokenization_ns / 1_000_000,
                "intent_detection": intent_ns / 1_000_000,
                "attribute_value_matching": matching_ns / 1_000_000,
                "sql_generation": generation_ns / 1_000_000,
                "validation": validation_ns / 1_000_000,
                "execution": execution_ns / 1_000_000,
                "total": total_ns / 1_000_000,
            })
        finally:
            os.unlink(db_path)

    summary = {}
    for key in measurements[0]:
        values = sorted(item[key] for item in measurements)
        summary[key] = {
            "mean_ms": round(sum(values) / len(values), 6),
            "median_ms": round(values[len(values) // 2], 6),
            "p95_ms": round(values[max(0, math.ceil(len(values) * 0.95) - 1)], 6),
        }
    return {"queries": len(measurements), "summary": summary}


def _ablation(records, paths):
    """Measure the contribution of the synonym dictionary."""
    model, vectorizer = load_model(str(MODEL_PATH), str(VECTORIZER_PATH))
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as empty:
        json.dump({}, empty)
        empty_path = empty.name
    try:
        output = {}
        for label, synonyms_path in (
            ("hybrid", "knowledge/synonyms.json"),
            ("hybrid_without_synonyms", empty_path),
        ):
            correct = 0
            for domain, _, case in all_cases():
                df, db_path, schema = _load_domain(domain, paths[domain])
                try:
                    intent = predict_intent(case["question"], model, vectorizer)
                    query = build_query(
                        case["question"], schema, intent,
                        synonyms_path=synonyms_path,
                    )
                    sql = query_to_sql(query)
                    valid, _ = validate_sql(sql, schema)
                    if valid:
                        columns, rows = _sqlite_query(db_path, sql)
                        gold_columns, gold_rows = _sqlite_query(db_path, case["gold_sql"])
                        if columns == gold_columns and _rows_equal(
                            rows, gold_rows, "ORDER BY" in case["gold_sql"].upper()
                        ):
                            correct += 1
                except Exception:
                    pass
                finally:
                    os.unlink(db_path)
            output[label] = {
                "queries": 100,
                "execution_accuracy": round(correct / 100, 6),
                "correct_queries": correct,
            }
        return output
    finally:
        os.unlink(empty_path)


def _markdown_report(result):
    methods = result["method_metrics"]
    lines = [
        "# nl2sql-366 benchmark results",
        "",
        f"Generated on **{result['generated_at']}** by `python benchmark/run_benchmark.py`.",
        "The benchmark contains 100 queries over five deterministic, previously unseen single-table schemas (20 per domain).",
        "",
        "## Method comparison",
        "",
        "| Method | Intent accuracy | Execution accuracy | Execution F1 | Valid SQL |",
        "|---|---:|---:|---:|---:|",
    ]
    names = {
        "rule_based": "Rule-based intent baseline",
        "ml_only": "TF-IDF + Naive Bayes only",
        "hybrid": "Proposed hybrid",
    }
    for key in ("rule_based", "ml_only", "hybrid"):
        metric = methods[key]
        lines.append(
            f"| {names[key]} | {metric['intent_accuracy']:.2%} | "
            f"{metric['execution_accuracy']:.2%} | {metric['execution_f1']:.3f} | "
            f"{metric['valid_sql_rate']:.2%} |"
        )
    lines += [
        "",
        "Execution accuracy requires matching the gold result columns and rows; ordering is checked for ranking queries and ignored for unordered SQL results. Execution F1 is the mean row-level F1 across queries.",
        "",
        "## Cross-domain hybrid results",
        "",
        "| Domain | Queries | Execution accuracy | Execution F1 |",
        "|---|---:|---:|---:|",
    ]
    for domain, metric in result["domain_metrics"].items():
        lines.append(
            f"| {domain.title()} | {metric['queries']} | "
            f"{metric['execution_accuracy']:.2%} | {metric['execution_f1']:.3f} |"
        )
    lines += [
        "",
        "## Query-category results",
        "",
        "| Category | Queries | Hybrid execution accuracy |",
        "|---|---:|---:|",
    ]
    for category, metric in result["category_metrics"].items():
        lines.append(
            f"| {category.replace('_', ' ').title()} | {metric['queries']} | "
            f"{metric['execution_accuracy']:.2%} |"
        )
    lines += [
        "",
        "## Final intent-classifier holdout",
        "",
        f"- Dataset: `{result['ml_metrics']['dataset']}`",
        f"- Examples: {result['ml_metrics']['examples']:,} "
        f"({result['ml_metrics']['train_examples']:,} train / {result['ml_metrics']['test_examples']:,} test)",
        f"- Accuracy: **{result['ml_metrics']['accuracy']:.2%}**",
        f"- Weighted precision: **{result['ml_metrics']['weighted_precision']:.2%}**",
        f"- Weighted recall: **{result['ml_metrics']['weighted_recall']:.2%}**",
        f"- Weighted F1: **{result['ml_metrics']['weighted_f1']:.2%}**",
        "",
        "Confusion-matrix label order: " + ", ".join(result["ml_metrics"]["confusion_matrix_labels"]),
        "",
        "## Ablation",
        "",
        "| Variant | Queries | Correct | Execution accuracy |",
        "|---|---:|---:|---:|",
    ]
    for key, metric in result["ablation"].items():
        lines.append(
            f"| {key.replace('_', ' ').title()} | {metric['queries']} | "
            f"{metric['correct_queries']} | {metric['execution_accuracy']:.2%} |"
        )
    lines += [
        "",
        "## Security validation",
        "",
        f"{result['security']['passed']}/{result['security']['cases']} validator cases passed "
        f"({result['security']['pass_rate']:.2%}). Unsafe statements, unknown columns/tables, and multiple statements are expected to be rejected; a safe SELECT is the positive control.",
        "",
        "## Latency",
        "",
        "| Stage | Mean (ms) | Median (ms) | P95 (ms) |",
        "|---|---:|---:|---:|",
    ]
    for stage, metric in result["latency"]["summary"].items():
        lines.append(
            f"| {stage.replace('_', ' ').title()} | {metric['mean_ms']:.3f} | "
            f"{metric['median_ms']:.3f} | {metric['p95_ms']:.3f} |"
        )
    lines += [
        "",
        "> These measurements are local SQLite timings on the Replit development environment; they are not a deployment or hardware-independent performance guarantee.",
        "",
    ]
    return "\n".join(lines)


def main():
    paths = _write_fixtures()
    records = _evaluate_methods(paths)
    result = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "benchmark": {
            "queries": len(list(all_cases())),
            "domains": list(DATASETS),
            "queries_per_domain": 20,
        },
        "method_metrics": _metrics(records),
        "domain_metrics": _domain_metrics(records),
        "category_metrics": _category_metrics(records),
        "ml_metrics": _ml_metrics(),
        "ablation": _ablation(records, paths),
        "security": _security_metrics(),
        "latency": _latency_metrics(paths),
        "records": records,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "latest.json").write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8"
    )
    (RESULTS_DIR / "latest.md").write_text(
        _markdown_report(result), encoding="utf-8"
    )
    print(_markdown_report(result))
    print(f"\nDetailed records: {RESULTS_DIR / 'latest.json'}")


if __name__ == "__main__":
    main()