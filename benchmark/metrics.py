# metrics.py — comprehensive evaluation metrics for the NL2SQL benchmark.
#
# Computes overall, per-intent, per-dataset, and per-category metrics
# from per-query benchmark results.

from collections import defaultdict
from typing import List, Dict, Any, Optional
import math


def _pct(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 2) if denominator else 0.0


def _safe_div(num, den):
    return num / den if den else 0.0


def extract_intent_from_sql(sql: str) -> str:
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


def compute_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute all benchmark metrics from per-query results.

    Each result dict must contain:
        - intent_match: bool
        - valid_sql: bool
        - execution_success: bool
        - result_match: bool
        - exact_sql_match: bool
        - expected_intent: str
        - predicted_intent: str (or None)
        - gen_time_ms: float (SQL generation time in ms)
        - exec_time_ms: float (SQL execution time in ms)
        - error_category: str
        - dataset: str
    """
    total = len(results)
    if total == 0:
        return _empty_metrics()

    intent_match = sum(1 for r in results if r.get("intent_match", False))
    valid_sql = sum(1 for r in results if r.get("valid_sql", False))
    exec_success = sum(1 for r in results if r.get("execution_success", False))
    result_match = sum(1 for r in results if r.get("result_match", False))
    exact_match = sum(1 for r in results if r.get("exact_sql_match", False))
    failed = sum(1 for r in results if not r.get("result_match", False))

    gen_times = [r.get("gen_time_ms", 0) for r in results]
    exec_times = [r.get("exec_time_ms", 0) for r in results]

    overall = {
        "total_queries": total,
        "passed": result_match,
        "failed": failed,
        "intent_accuracy": _pct(intent_match, total),
        "valid_sql_rate": _pct(valid_sql, total),
        "execution_success_rate": _pct(exec_success, total),
        "execution_accuracy": _pct(exec_success, total),
        "result_match_accuracy": _pct(result_match, total),
        "exact_sql_match_rate": _pct(exact_match, total),
        "avg_generation_time_ms": round(sum(gen_times) / total, 2),
        "avg_execution_time_ms": round(sum(exec_times) / total, 2),
    }

    # Per-intent metrics
    by_intent = _per_intent_metrics(results)

    # Per-dataset metrics
    by_dataset = _per_dataset_metrics(results)

    # Error analysis
    error_analysis = _error_analysis(results)

    # F1 / Precision / Recall per intent (computed from raw results)
    f1_scores = _f1_per_intent(results)

    # Macro F1
    macro_f1 = _compute_macro_f1(f1_scores)

    return {
        "overall": overall,
        "by_intent": by_intent,
        "by_dataset": by_dataset,
        "error_analysis": error_analysis,
        "f1_scores": f1_scores,
        "macro_f1": macro_f1,
    }


def _per_intent_metrics(results: List[Dict]) -> Dict[str, Any]:
    intents = defaultdict(lambda: {"total": 0, "intent_match": 0,
                                   "result_match": 0, "exact_match": 0,
                                   "valid_sql": 0, "exec_success": 0})
    for r in results:
        intent = r.get("expected_intent", "UNKNOWN")
        bucket = intents[intent]
        bucket["total"] += 1
        bucket["intent_match"] += int(r.get("intent_match", False))
        bucket["result_match"] += int(r.get("result_match", False))
        bucket["exact_match"] += int(r.get("exact_sql_match", False))
        bucket["valid_sql"] += int(r.get("valid_sql", False))
        bucket["exec_success"] += int(r.get("execution_success", False))

    out = {}
    for intent in sorted(intents):
        b = intents[intent]
        out[intent] = {
            "total": b["total"],
            "intent_accuracy": _pct(b["intent_match"], b["total"]),
            "result_match_accuracy": _pct(b["result_match"], b["total"]),
            "exact_sql_match_rate": _pct(b["exact_match"], b["total"]),
            "valid_sql_rate": _pct(b["valid_sql"], b["total"]),
            "execution_success_rate": _pct(b["exec_success"], b["total"]),
        }
    return out


def _per_dataset_metrics(results: List[Dict]) -> Dict[str, Any]:
    datasets = defaultdict(lambda: {"total": 0, "result_match": 0,
                                    "intent_match": 0, "exact_match": 0})
    for r in results:
        ds = r.get("dataset", "UNKNOWN")
        bucket = datasets[ds]
        bucket["total"] += 1
        bucket["result_match"] += int(r.get("result_match", False))
        bucket["intent_match"] += int(r.get("intent_match", False))
        bucket["exact_match"] += int(r.get("exact_sql_match", False))

    out = {}
    for ds in sorted(datasets):
        b = datasets[ds]
        out[ds] = {
            "total": b["total"],
            "result_match_accuracy": _pct(b["result_match"], b["total"]),
            "intent_accuracy": _pct(b["intent_match"], b["total"]),
            "exact_sql_match_rate": _pct(b["exact_match"], b["total"]),
        }
    return out


def _error_analysis(results: List[Dict]) -> Dict[str, Any]:
    categories = defaultdict(int)
    failed_queries = []
    for r in results:
        if not r.get("result_match", False):
            cat = r.get("error_category", "unknown")
            categories[cat] += 1
            failed_queries.append({
                "id": r.get("query_id"),
                "question": r.get("question", ""),
                "dataset": r.get("dataset", ""),
                "error_category": cat,
                "expected_intent": r.get("expected_intent", ""),
                "predicted_intent": r.get("predicted_intent", ""),
                "reference_sql": r.get("reference_sql", ""),
                "generated_sql": r.get("generated_sql", ""),
                "error_message": r.get("error_message", ""),
            })

    return {
        "total_failed": len(failed_queries),
        "categories": dict(sorted(categories.items())),
        "failed_queries": failed_queries,
    }


def _f1_per_intent(results: List[Dict]) -> Dict[str, Any]:
    """
    For each intent, compute precision, recall, F1.
    Treat "result_match" as the binary outcome.
    """
    from collections import defaultdict
    intent_counts = defaultdict(lambda: {"tp": 0, "total": 0})
    for r in results:
        intent = r.get("expected_intent", "UNKNOWN")
        intent_counts[intent]["total"] += 1
        if r.get("result_match", False):
            intent_counts[intent]["tp"] += 1

    f1_out = {}
    for intent, counts in intent_counts.items():
        tp = counts["tp"]
        total = counts["total"]
        fn = total - tp
        precision = _safe_div(tp, tp) if tp > 0 else 0.0
        recall = _safe_div(tp, total)
        f1 = _safe_div(2 * precision * recall, precision + recall) if (precision + recall) > 0 else 0.0
        f1_out[intent] = {
            "precision": round(precision * 100, 2),
            "recall": round(recall * 100, 2),
            "f1": round(f1 * 100, 2),
            "support": total,
        }
    return f1_out


def _compute_macro_f1(f1_scores: Dict[str, Any]) -> float:
    if not f1_scores:
        return 0.0
    total_support = sum(v["support"] for v in f1_scores.values())
    if total_support == 0:
        return 0.0
    weighted_f1 = sum(v["f1"] * v["support"] for v in f1_scores.values())
    return round(weighted_f1 / total_support, 2)


def _empty_metrics() -> Dict[str, Any]:
    return {
        "overall": {"total_queries": 0, "passed": 0, "failed": 0,
                     "intent_accuracy": 0, "valid_sql_rate": 0,
                     "execution_success_rate": 0, "execution_accuracy": 0,
                     "result_match_accuracy": 0, "exact_sql_match_rate": 0,
                     "avg_generation_time_ms": 0, "avg_execution_time_ms": 0},
        "by_intent": {},
        "by_dataset": {},
        "error_analysis": {"total_failed": 0, "categories": {}, "failed_queries": []},
        "f1_scores": {},
        "macro_f1": 0.0,
    }


def format_terminal_summary(metrics_dict: Dict[str, Any],
                            total_runtime_s: float) -> str:
    """Format a concise terminal-friendly summary."""
    o = metrics_dict["overall"]
    lines = [
        "",
        "=" * 60,
        "NL2SQL-366 BENCHMARK RESULTS",
        "=" * 60,
        "",
        f"{'Queries:':<26}{o['total_queries']:>8}",
        f"{'Intent Accuracy:':<26}{o['intent_accuracy']:>7.2f}%",
        f"{'Valid SQL:':<26}{o['valid_sql_rate']:>7.2f}%",
        f"{'Execution Success:':<26}{o['execution_success_rate']:>7.2f}%",
        f"{'Result Match:':<26}{o['result_match_accuracy']:>7.2f}%",
        f"{'Exact SQL Match:':<26}{o['exact_sql_match_rate']:>7.2f}%",
        f"{'Macro F1:':<26}{metrics_dict['macro_f1']:>7.2f}%",
        "",
        f"{'Passed:':<26}{o['passed']:>8}",
        f"{'Failed:':<26}{o['failed']:>8}",
        "",
        f"{'Avg SQL Generation:':<26}{o['avg_generation_time_ms']:>7.2f} ms",
        f"{'Avg Execution Time:':<26}{o['avg_execution_time_ms']:>7.2f} ms",
        f"{'Total Runtime:':<26}{total_runtime_s:>7.2f} s",
        "",
        "=" * 60,
    ]
    return "\n".join(lines)
