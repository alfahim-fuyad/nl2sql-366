"""
Matches natural language phrases to dataset column names.

Uses a combination of fuzzy string matching (RapidFuzz), synonym lookup, and
sliding-window phrase detection to handle multi-word column names, synonyms,
and variations in spacing or punctuation.
"""

import os
import re
import json
from rapidfuzz import process, fuzz


def load_synonyms(path="knowledge/synonyms.json"):
    """Load the synonym dictionary. Returns an empty dict if the file is missing."""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.pop("_comment", None)
    return data


def load_stopwords(path="knowledge/stopwords.json"):
    """Load the stopword list. Returns an empty list if the file is missing."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _strip_symbols(text):
    """
    Remove parenthetical content and non-alphanumeric characters.

    Examples:
        "(min)"  → ""
        "($)"    → ""
        "1-5"    → "1 5"
    """
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize(text):
    """
    Lowercase, replace underscores with spaces, and strip symbols.

    Examples:
        "credit_score"            → "credit score"
        "Purchase Amount ($)"     → "purchase amount"
        "Time Spent on Website (min)" → "time spent on website"
    """
    text = text.lower().replace("_", " ")
    return _strip_symbols(text)


def _build_lookup(schema):
    """
    Build a normalized-name → original-name mapping from the schema.

    Both the original lowercase form and the underscore-normalized form
    are stored to support column names with underscores or special characters.
    """
    lookup = {}
    for col in schema.keys():
        lookup[col.lower()] = col
        normalized = _normalize(col)
        if normalized not in lookup:
            lookup[normalized] = col
    return lookup


def match_column(word, schema, synonyms_path="knowledge/synonyms.json", threshold=70):
    """
    Match a single word or phrase to a column name from the schema.

    Returns the best-matching column name, or None if no match exceeds
    the similarity threshold.

    Matching strategy:
        1. Direct fuzzy match of the normalized word against all column names.
        2. Synonym lookup followed by a fuzzy match of the canonical term.
    """
    if not word or not schema:
        return None

    synonyms = load_synonyms(synonyms_path)
    word_norm = _normalize(word)

    lower_to_original = _build_lookup(schema)
    lower_columns = list(lower_to_original.keys())

    result = process.extractOne(
        word_norm, lower_columns, scorer=fuzz.token_sort_ratio
    )
    if result and result[1] >= threshold:
        return lower_to_original[result[0]]

    if word_norm in synonyms:
        synonym_norm = _normalize(synonyms[word_norm])
        result = process.extractOne(
            synonym_norm, lower_columns, scorer=fuzz.token_sort_ratio
        )
        if result and result[1] >= threshold:
            return lower_to_original[result[0]]

    word_lower = word.lower().strip()
    if word_lower in synonyms:
        synonym_norm = _normalize(synonyms[word_lower])
        result = process.extractOne(
            synonym_norm, lower_columns, scorer=fuzz.token_sort_ratio
        )
        if result and result[1] >= threshold:
            return lower_to_original[result[0]]

    return None


def find_columns_with_positions(text, schema,
                                 synonyms_path="knowledge/synonyms.json",
                                 stopwords_path="knowledge/stopwords.json",
                                 threshold=72):
    """
    Find all matching columns in the question, with their positions and scores.

    Uses a sliding-window approach that matches entire multi-word column phrases
    at once rather than single tokens, which prevents incorrect column selection
    when column names share common words.

    Algorithm:
        1. Strip stopwords from both the question and each column name to get
           "core" tokens.
        2. For each column, slide a window of the same size as the column's core
           phrase across the question's core tokens and compute a fuzzy score.
        3. If no window matches, fall back to a full-question token-set ratio
           for columns not yet matched (handles partial references).

    Returns:
        List of dicts: [{"column": str, "position": int, "score": int}, ...]
        Sorted by descending score then ascending position.
    """
    if not text or not schema:
        return []

    synonyms  = load_synonyms(synonyms_path)
    stopwords = set(load_stopwords(stopwords_path))

    raw_tokens = [
        {"word": m.group(), "position": m.start()}
        for m in re.finditer(r"[a-z0-9]+", text.lower())
    ]
    if not raw_tokens:
        return []

    core_tokens = [t for t in raw_tokens if t["word"] not in stopwords] or raw_tokens

    col_specs = []
    for col in schema.keys():
        norm = _normalize(col)
        if not norm:
            continue
        norm_words  = norm.split()
        core_words  = [w for w in norm_words if w not in stopwords] or norm_words
        col_specs.append({
            "column":      col,
            "core_words":  core_words,
            "core_phrase": " ".join(core_words),
        })

    best_by_column = {}
    n_tokens = len(core_tokens)
    max_n    = max((len(spec["core_words"]) for spec in col_specs), default=1)

    # Primary pass: exact-length sliding window match
    for n in range(min(max_n, n_tokens), 0, -1):
        cols_of_size = [s for s in col_specs if len(s["core_words"]) == n]
        if not cols_of_size:
            continue

        for i in range(n_tokens - n + 1):
            window     = core_tokens[i:i + n]
            phrase     = " ".join(t["word"] for t in window)
            phrase_pos = window[0]["position"]

            phrase_candidates = {phrase}
            if n == 1 and phrase in synonyms:
                phrase_candidates.add(_normalize(synonyms[phrase]))

            for spec in cols_of_size:
                score = max(
                    fuzz.token_sort_ratio(cand, spec["core_phrase"])
                    for cand in phrase_candidates
                )
                if score >= threshold:
                    prev = best_by_column.get(spec["column"])
                    if prev is None or score > prev["score"]:
                        best_by_column[spec["column"]] = {
                            "column":   spec["column"],
                            "position": phrase_pos,
                            "score":    score,
                        }

    # Fallback: partial-phrase match for columns not matched in the primary pass
    question_core_phrase = " ".join(t["word"] for t in core_tokens)
    for spec in col_specs:
        if spec["column"] in best_by_column:
            continue
        score = fuzz.token_set_ratio(question_core_phrase, spec["core_phrase"])
        if score < max(threshold, 80):
            continue

        position = None
        for token in core_tokens:
            for cw in spec["core_words"]:
                if fuzz.ratio(token["word"], cw) >= 85:
                    position = token["position"]
                    break
            if position is not None:
                break
        if position is None:
            position = core_tokens[0]["position"]

        best_by_column[spec["column"]] = {
            "column":   spec["column"],
            "position": position,
            "score":    score,
        }

    return sorted(best_by_column.values(), key=lambda r: (-r["score"], r["position"]))


def find_columns_in_text(text, schema, synonyms_path="knowledge/synonyms.json"):
    """
    Return a deduplicated list of column names matched in the given text.

    Delegates to find_columns_with_positions for the actual matching logic.
    """
    matches = find_columns_with_positions(text, schema, synonyms_path)
    return [m["column"] for m in matches]
