import os
import re
import json

from rapidfuzz import process, fuzz


# =========================================================
# LOAD SYNONYMS
# =========================================================

def load_synonyms(path="knowledge/synonyms.json"):
    """
    Load word -> canonical column mappings.

    Example:
        female -> gender
        sex    -> gender
        years  -> age
        cost   -> price
    """

    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return {}

        data.pop("_comment", None)

        return {
            str(k).lower().strip(): str(v).strip()
            for k, v in data.items()
        }

    except (OSError, json.JSONDecodeError):
        return {}


# =========================================================
# NORMALIZATION
# =========================================================

def _normalize_text(text):
    """
    Normalize text for matching.
    """

    if text is None:
        return ""

    text = str(text).lower()

    text = text.replace("_", " ")

    text = re.sub(
        r"[^a-z0-9.\-\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# =========================================================
# NUMBER EXTRACTION
# =========================================================

def extract_numbers(text):
    """
    Extract integer / decimal / negative numbers
    together with their positions.
    """

    if not text:
        return []

    numbers = []

    pattern = re.compile(
        r"(?<![A-Za-z0-9])"
        r"-?\d+(?:\.\d+)?"
        r"(?![A-Za-z0-9])"
    )

    for match in pattern.finditer(str(text)):

        raw = match.group()

        try:
            if "." in raw:
                value = float(raw)
            else:
                value = int(raw)

        except ValueError:
            continue

        numbers.append({
            "value": value,
            "position": match.start(),
        })

    return numbers


# =========================================================
# VALUE NORMALIZATION
# =========================================================

def _normalize_value(value):
    """
    Normalize a dataset categorical value.
    """

    if value is None:
        return ""

    return _normalize_text(value)


# =========================================================
# GET SAMPLE / UNIQUE VALUES
# =========================================================

def _get_sample_values(info):
    """
    Safely extract sample_values from schema information.
    """

    if not isinstance(info, dict):
        return []

    values = info.get(
        "sample_values",
        []
    )

    if values is None:
        return []

    if not isinstance(values, (list, tuple, set)):
        return [values]

    return list(values)


# =========================================================
# BUILD VALUE LOOKUP
# =========================================================

def _build_value_lookup(
    schema,
    allowed_columns=None
):
    """
    Build categorical value lookup.
    """

    lookup = []

    allowed = (
        set(allowed_columns)
        if allowed_columns is not None
        else None
    )

    for column, info in schema.items():

        if allowed is not None:
            if column not in allowed:
                continue

        for value in _get_sample_values(info):

            if value is None:
                continue

            normalized = _normalize_value(
                value
            )

            if not normalized:
                continue

            lookup.append({
                "column": column,
                "value": value,
                "normalized": normalized,
            })

    return lookup


# =========================================================
# SYNONYM TARGET
# =========================================================

def _synonym_target(
    word,
    synonyms
):
    """
    Return canonical synonym target.

    Example:
        female -> gender
        sex    -> gender
        years  -> age
    """

    normalized = _normalize_text(
        word
    )

    if normalized in synonyms:
        return _normalize_text(
            synonyms[normalized]
        )

    return None


# =========================================================
# MATCH ONE CATEGORICAL VALUE
# =========================================================

def _match_one_value(
    phrase,
    value_lookup,
    synonyms,
    threshold=78,
):
    """
    Match one phrase against dataset values.
    """

    if not phrase:
        return None

    phrase_norm = _normalize_text(
        phrase
    )

    if not phrase_norm:
        return None

    candidates = [
        item["normalized"]
        for item in value_lookup
    ]

    if not candidates:
        return None

    # -----------------------------------------------------
    # EXACT MATCH FIRST
    # -----------------------------------------------------

    for item in value_lookup:

        if item["normalized"] == phrase_norm:

            return {
                "column": item["column"],
                "value": item["value"],
                "score": 100,
                "matched_text": phrase,
            }

    # -----------------------------------------------------
    # FUZZY DIRECT MATCH
    # -----------------------------------------------------

    result = process.extractOne(
        phrase_norm,
        candidates,
        scorer=fuzz.token_sort_ratio,
    )

    if result:

        matched_text = result[0]
        score = result[1]

        if score >= threshold:

            for item in value_lookup:

                if (
                    item["normalized"]
                    == matched_text
                ):

                    return {
                        "column": item["column"],
                        "value": item["value"],
                        "score": score,
                        "matched_text": phrase,
                    }

    # -----------------------------------------------------
    # SYNONYM MATCH
    # -----------------------------------------------------

    canonical = _synonym_target(
        phrase_norm,
        synonyms
    )

    if canonical:

        # First check exact canonical value.
        for item in value_lookup:

            if (
                item["normalized"]
                == canonical
            ):

                return {
                    "column": item["column"],
                    "value": item["value"],
                    "score": 100,
                    "matched_text": phrase,
                    "canonical": canonical,
                }

        # Then fuzzy canonical match.
        result = process.extractOne(
            canonical,
            candidates,
            scorer=fuzz.token_sort_ratio,
        )

        if result:

            matched_text = result[0]
            score = result[1]

            if score >= threshold:

                for item in value_lookup:

                    if (
                        item["normalized"]
                        == matched_text
                    ):

                        return {
                            "column": item["column"],
                            "value": item["value"],
                            "score": score,
                            "matched_text": phrase,
                            "canonical": canonical,
                        }

    return None


# =========================================================
# MATCH CATEGORICAL VALUES
# =========================================================

def match_categorical_values(
    question,
    schema,
    allowed_columns=None,
    synonyms_path="knowledge/synonyms.json",
    threshold=78,
):
    """
    Detect categorical values from question.

    Example:

        "how many female are there"

        female
            ↓
        gender
            ↓
        Female

    Returns:
        [
            {
                "column": "gender",
                "value": "Female",
                ...
            }
        ]
    """

    if not question or not schema:
        return []

    synonyms = load_synonyms(
        synonyms_path
    )

    # -----------------------------------------------------
    # Primary lookup
    # -----------------------------------------------------

    value_lookup = _build_value_lookup(
        schema,
        allowed_columns
    )

    # -----------------------------------------------------
    # If attribute matcher didn't find a column,
    # retry against all categorical values.
    # This is important for:
    #
    # "how many female are there"
    #
    # where attribute matcher may not return gender.
    # -----------------------------------------------------

    if not value_lookup:

        value_lookup = _build_value_lookup(
            schema,
            None
        )

    if not value_lookup:
        return []

    question_lower = str(
        question
    ).lower()

    tokens = list(
        re.finditer(
            r"[a-z0-9_]+",
            question_lower
        )
    )

    if not tokens:
        return []

    # =====================================================
    # CREATE PHRASES
    # =====================================================

    phrases = []

    # Single words
    for token in tokens:

        phrases.append({
            "text": token.group(),
            "position": token.start(),
        })

    # Two-word phrases
    for i in range(
        len(tokens) - 1
    ):

        start = tokens[i].start()
        end = tokens[i + 1].end()

        phrases.append({
            "text": question_lower[
                start:end
            ],
            "position": start,
        })

    # Three-word phrases
    for i in range(
        len(tokens) - 2
    ):

        start = tokens[i].start()
        end = tokens[i + 2].end()

        phrases.append({
            "text": question_lower[
                start:end
            ],
            "position": start,
        })

    # =====================================================
    # IGNORED WORDS
    # =====================================================

    ignored = {
        "how",
        "many",
        "much",
        "what",
        "which",
        "who",
        "where",
        "when",
        "are",
        "is",
        "was",
        "were",
        "there",
        "the",
        "all",
        "of",
        "for",
        "with",
        "by",
        "in",
        "on",
        "from",
        "show",
        "list",
        "give",
        "me",
        "find",
        "get",
        "records",
        "record",
        "rows",
        "row",
        "please",
        "can",
        "you",
        "tell",
        "display",
        "return",
        "calculate",
        "calculate",
        "number",
        "count",
    }

    phrases = [
        p
        for p in phrases
        if p["text"] not in ignored
    ]

    # =====================================================
    # MATCH PHRASES
    # =====================================================

    best_by_column = {}

    for phrase in phrases:

        text = phrase["text"]

        if len(text.split()) > 3:
            continue

        match = _match_one_value(
            text,
            value_lookup,
            synonyms,
            threshold=threshold,
        )

        if not match:
            continue

        column = match["column"]

        previous = best_by_column.get(
            column
        )

        # Prefer exact / higher-score match.
        if (
            previous is None
            or match["score"]
            > previous["score"]
        ):

            match["position"] = (
                phrase["position"]
            )

            best_by_column[column] = match

    # =====================================================
    # RETURN
    # =====================================================

    return sorted(
        best_by_column.values(),
        key=lambda x: (
            x["position"],
            -x["score"],
        )
    )


# =========================================================
# MATCH VALUE FOR SPECIFIC COLUMN
# =========================================================

def match_value_for_column(
    question,
    schema,
    column,
    synonyms_path="knowledge/synonyms.json",
    threshold=78,
):
    """
    Match value against one specific column.
    """

    results = match_categorical_values(
        question,
        schema,
        allowed_columns={column},
        synonyms_path=synonyms_path,
        threshold=threshold,
    )

    return results[0] if results else None