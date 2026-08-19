"""
metrics.py — aggregates per-question evaluation results into summary
accuracy metrics (overall, by dataset, by question type).
"""
from collections import defaultdict


def _pct(correct: int, total: int) -> float:
    return round(100.0 * correct / total, 2) if total else 0.0


def compute_metrics(results: list) -> dict:
    total = len(results)
    correct = sum(1 for r in results if r["correct"])

    by_dataset = defaultdict(lambda: {"correct": 0, "total": 0})
    by_type = defaultdict(lambda: {"correct": 0, "total": 0})

    for r in results:
        by_dataset[r["dataset"]]["total"] += 1
        by_dataset[r["dataset"]]["correct"] += int(r["correct"])
        by_type[r["type"]]["total"] += 1
        by_type[r["type"]]["correct"] += int(r["correct"])

    dataset_summary = {
        ds: {
            "correct": v["correct"],
            "total": v["total"],
            "accuracy_pct": _pct(v["correct"], v["total"]),
        }
        for ds, v in sorted(by_dataset.items())
    }
    type_summary = {
        t: {
            "correct": v["correct"],
            "total": v["total"],
            "accuracy_pct": _pct(v["correct"], v["total"]),
        }
        for t, v in sorted(by_type.items())
    }

    return {
        "overall": {
            "correct": correct,
            "total": total,
            "accuracy_pct": _pct(correct, total),
        },
        "by_dataset": dataset_summary,
        "by_type": type_summary,
    }
