"""
Predicts the SQL intent of a natural language question.

Loads a pre-trained Naive Bayes classifier and applies rule-based post-processing
to correct common misclassifications (e.g. "show all..." should always be SELECT).

Supported intents: SELECT, COUNT, AVG, MAX, MIN, SUM
"""

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
_RANK_TRIGGERS = re.compile(
    r"\b(top|bottom|lowest|least|worst|best)\s+\d+\b",
    re.IGNORECASE,
)


def _override_intent(text, ml_intent):
    """
    Apply rule-based corrections to the ML model's intent prediction.

    Rules:
        - "top N / bottom N" patterns → SELECT (uses ORDER BY + LIMIT)
        - "show / list / display" without count keywords → SELECT
    """
    if _RANK_TRIGGERS.search(text):
        return "SELECT"

    if _SHOW_TRIGGERS.search(text) and not _COUNT_OVERRIDES.search(text):
        return "SELECT"

    return ml_intent


def load_model(model_path="models/intent_model.pkl",
               vectorizer_path="models/vectorizer.pkl"):
    """Load and return the saved (model, vectorizer) pair."""
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(vectorizer_path, "rb") as f:
        vectorizer = pickle.load(f)
    return model, vectorizer


def predict_intent(text, model, vectorizer):
    """
    Predict the SQL intent for a natural language question.

    Returns one of: SELECT, COUNT, AVG, MAX, MIN, SUM.
    The ML prediction is post-processed by rule-based overrides.
    """
    text_vec  = vectorizer.transform([text])
    ml_intent = model.predict(text_vec)[0]
    return _override_intent(text, ml_intent)
