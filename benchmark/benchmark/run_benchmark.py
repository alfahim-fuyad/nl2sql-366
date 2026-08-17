"""
run_benchmark.py — the single entry point that runs the whole benchmark.

Usage:
    python -m benchmark.run_benchmark
    (run from the directory that CONTAINS the benchmark/ folder)
"""
import json
import os
import sys
import datetime

# Allow running this file directly (python benchmark/run_benchmark.py)
if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from benchmark import config, dataset_loader, sql_executor, model_runner, evaluator, metrics
else:
    from . import config, dataset_loader, sql_executor, model_runner, evaluator, metrics


def load_questions():
    with open(config.QUESTIONS_PATH, "r") as f:
        return json.load(f)


def run_sql_question(q):
    return sql_executor.execute_scalar(q["sql"])


def run_ml_question(q):
    if "row_index" in q:
        pred = model_runner.predict_row(q["dataset"], q["row_index"])
    else:
        _, score = model_runner.model_score(q["dataset"])
        pred = score
    if hasattr(pred, "item"):
        pred = pred.item()
    if isinstance(pred, float):
        pred = round(pred, 4)
    return pred


def run_question(q):
    if q["type"] == "sql":
        return run_sql_question(q)
    elif q["type"] == "ml":
        return run_ml_question(q)
    raise ValueError(f"Unknown question type: {q['type']}")


def main():
    print("Loading datasets into SQLite...")
    dataset_loader.load_all_to_sqlite()

    print("Loading questions...")
    questions = load_questions()
    print(f"  {len(questions)} questions loaded")

    results = []
    for q in questions:
        try:
            computed = run_question(q)
        except Exception as e:
            computed = None
            print(f"  [warn] question {q['id']} failed: {e}")
        result = evaluator.evaluate_question_result(q, computed)
        results.append(result)

    summary = metrics.compute_metrics(results)

    report = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "num_questions": len(questions),
        "summary": summary,
        "results": results,
    }

    os.makedirs(config.REPORT_DIR, exist_ok=True)
    with open(config.LATEST_REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    print("\n=== Benchmark Summary ===")
    print(f"Overall accuracy: {summary['overall']['accuracy_pct']}% "
          f"({summary['overall']['correct']}/{summary['overall']['total']})")
    print("\nBy dataset:")
    for ds, s in summary["by_dataset"].items():
        print(f"  {ds:22s} {s['accuracy_pct']:6.2f}%  ({s['correct']}/{s['total']})")
    print("\nBy type:")
    for t, s in summary["by_type"].items():
        print(f"  {t:22s} {s['accuracy_pct']:6.2f}%  ({s['correct']}/{s['total']})")
    print(f"\nFull report written to: {config.LATEST_REPORT_PATH}")


if __name__ == "__main__":
    main()
