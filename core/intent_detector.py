# core/intent_detector.py

import re
import pickle

_SHOW_TRIGGERS = re.compile(
    r"\b(show|list|display|give me|find all|get all|fetch|retrieve|return)\b",
    re.IGNORECASE,
)
_COUNT_OVERRIDES = re.compile(
    r"\b(count|how many|number of|total number)\b",
    re.IGNORECASE,
)
_AVERAGE_OVERRIDES = re.compile(
    r"\b(avg|average|mean)\b",
    re.IGNORECASE,
)
_SUM_OVERRIDES = re.compile(
    r"\b(sum|total of|combined|total number of|add up|aggregate)\b",
    re.IGNORECASE,
)
_RANK_TRIGGERS = re.compile(
    r"\b(top|bottom|lowest|least|worst|best)\s+\d+\b",
    re.IGNORECASE,
)


def _override_intent(text, ml_intent):
    # "highest average salary" is an AVG grouped-ranking query, not MAX.
    # The classifier was trained mostly on single-operation examples and
    # otherwise gives the ranking word ("highest") too much weight.
    if _AVERAGE_OVERRIDES.search(text):
        return "AVG"

    # SUM overrides: "total parking spots" -> SUM
    if re.search(r"\b(sum|total of|combined|add up|aggregate)\b", text, re.IGNORECASE):
        return "SUM"
    if re.search(r"\btotal\b", text, re.IGNORECASE):
        # "total number of" with a numeric column name following -> SUM
        # e.g., "total number of parking spots" -> SUM(parking)
        # But "total number of houses" (COUNT target) -> COUNT
        if re.search(r"\btotal number of\b", text, re.IGNORECASE):
            return ml_intent  # Let classifier decide (usually COUNT)
        return "SUM"

    if _RANK_TRIGGERS.search(text):
        return "SELECT"

    if _SHOW_TRIGGERS.search(text) and not _COUNT_OVERRIDES.search(text):
        # Don't override to SELECT if the query has aggregate intent indicators
        # E.g., "show me the highest price" -> should stay as MAX, not become SELECT
        if not re.search(
            r"\b(highest|lowest|maximum|minimum|max|min|average|avg|mean|sum|total)\b",
            text, re.IGNORECASE
        ):
            return "SELECT"

    return ml_intent


def load_model(model_path="models/intent_model.pkl",
               vectorizer_path="models/vectorizer.pkl"):
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(vectorizer_path, "rb") as f:
        vectorizer = pickle.load(f)
    return model, vectorizer


def predict_intent(text, model, vectorizer):
    text_vec  = vectorizer.transform([text])
    ml_intent = model.predict(text_vec)[0]
    return _override_intent(text, ml_intent)
