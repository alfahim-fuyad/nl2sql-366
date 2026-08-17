"""
evaluator.py — compares a computed answer against a question's expected
answer and decides pass/fail, with tolerance for numeric answers.
"""

NUMERIC_TOLERANCE_PCT = 0.05  # 5% relative tolerance for numeric answers


def _is_number(x):
    try:
        float(x)
        return True
    except (TypeError, ValueError):
        return False


def evaluate_answer(actual, expected, tolerance_pct: float = NUMERIC_TOLERANCE_PCT):
    """
    Returns (is_correct: bool, detail: str).
    - Numeric answers are compared with a relative tolerance (handles
      float drift from model retraining / SQL rounding).
    - Everything else is compared as a normalized string.
    """
    if actual is None or expected is None:
        return actual == expected, "null comparison"

    if _is_number(actual) and _is_number(expected):
        a, e = float(actual), float(expected)
        if e == 0:
            ok = abs(a - e) < 1e-6
        else:
            ok = abs(a - e) / abs(e) <= tolerance_pct
        return ok, f"numeric diff={abs(a - e):.4f}"

    a_norm = str(actual).strip().lower()
    e_norm = str(expected).strip().lower()
    return a_norm == e_norm, "string comparison"


def evaluate_question_result(question: dict, computed_answer) -> dict:
    """
    Evaluate a single question's computed answer against its stored
    expected_answer, honoring a per-question tolerance if provided.
    """
    tol = question.get("tolerance_pct", NUMERIC_TOLERANCE_PCT)
    is_correct, detail = evaluate_answer(
        computed_answer, question.get("expected_answer"), tol
    )
    return {
        "id": question["id"],
        "dataset": question["dataset"],
        "type": question["type"],
        "question": question["question"],
        "expected_answer": question.get("expected_answer"),
        "computed_answer": computed_answer,
        "correct": bool(is_correct),
        "detail": detail,
    }
