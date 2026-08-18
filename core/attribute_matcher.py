import os
import re
import json
from rapidfuzz import process, fuzz


def load_synonyms(path="knowledge/synonyms.json"):
    """Load column synonyms from JSON."""
    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data.pop("_comment", None)

    return data


def load_stopwords(path="knowledge/stopwords.json"):
    """Load stopwords from JSON."""
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data if isinstance(data, list) else []


def _strip_symbols(text):
    """Remove symbols and normalize whitespace."""
    text = str(text)

    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _normalize(text):
    """
    Normalize text for matching.

    Examples:
        ' Monthly Income ' -> 'monthly income'
        'Monthly_Income'  -> 'monthly income'
        'Gender'          -> 'gender'
    """
    if text is None:
        return ""

    text = str(text).strip().lower()

    # Database column underscore -> space
    text = text.replace("_", " ")

    return _strip_symbols(text)


def _clean_schema_column(col):
    """Return the actual clean schema column name."""
    return str(col).strip()


def _build_lookup(schema):
    """
    Build normalized-name -> actual-schema-name mapping.

    Example:
        Monthly_Income -> {
            'monthly_income': 'Monthly_Income',
            'monthly income': 'Monthly_Income'
        }
    """
    lookup = {}

    for col in schema.keys():

        actual_col = _clean_schema_column(col)

        if not actual_col:
            continue

        # Original lowercase
        lookup[actual_col.lower()] = actual_col

        # Normalized version
        normalized = _normalize(actual_col)

        if normalized:
            lookup[normalized] = actual_col

    return lookup


def _build_synonym_lookup(synonyms):
    """
    Normalize synonym keys.

    Supports:
        {
            "salary": "Monthly Income"
        }

    and also:
        {
            "salary": ["Monthly Income", "Monthly_Income"]
        }
    """
    lookup = {}

    if not isinstance(synonyms, dict):
        return lookup

    for key, value in synonyms.items():

        key_norm = _normalize(key)

        if not key_norm:
            continue

        lookup[key_norm] = value

    return lookup


def _resolve_synonym_target(value, schema):
    """
    Convert a synonym target into an actual schema column.

    Example:
        'Monthly Income'
             ->
        'Monthly_Income'
    """

    if value is None:
        return None

    normalized_schema = {}

    for col in schema.keys():

        actual_col = _clean_schema_column(col)
        normalized = _normalize(actual_col)

        if normalized:
            normalized_schema[normalized] = actual_col

    # Single string
    if isinstance(value, str):

        target_norm = _normalize(value)

        # Exact normalized match
        if target_norm in normalized_schema:
            return normalized_schema[target_norm]

        # Fuzzy fallback
        if normalized_schema:

            result = process.extractOne(
                target_norm,
                list(normalized_schema.keys()),
                scorer=fuzz.token_sort_ratio
            )

            if result and result[1] >= 70:
                return normalized_schema[result[0]]

        return None

    # List of possible targets
    if isinstance(value, list):

        for item in value:

            resolved = _resolve_synonym_target(item, schema)

            if resolved:
                return resolved

    return None


def match_column(
    word,
    schema,
    synonyms_path="knowledge/synonyms.json",
    threshold=70
):
    """
    Match natural-language column reference to actual schema column.

    Examples:
        salary       -> Monthly_Income
        monthly income -> Monthly_Income
        Gender       -> Gender
    """

    if not word or not schema:
        return None

    synonyms = load_synonyms(synonyms_path)
    synonym_lookup = _build_synonym_lookup(synonyms)

    word_norm = _normalize(word)

    if not word_norm:
        return None

    # ---------------------------------------------------------
    # 1. Exact normalized schema match
    # ---------------------------------------------------------

    normalized_schema = {}

    for col in schema.keys():

        actual_col = _clean_schema_column(col)
        normalized = _normalize(actual_col)

        if normalized:
            normalized_schema[normalized] = actual_col

    if word_norm in normalized_schema:
        return normalized_schema[word_norm]

    # ---------------------------------------------------------
    # 2. Synonym match
    # ---------------------------------------------------------

    if word_norm in synonym_lookup:

        target = synonym_lookup[word_norm]

        resolved = _resolve_synonym_target(
            target,
            schema
        )

        if resolved:
            return resolved

    # ---------------------------------------------------------
    # 3. Fuzzy direct schema matching
    # ---------------------------------------------------------

    if normalized_schema:

        result = process.extractOne(
            word_norm,
            list(normalized_schema.keys()),
            scorer=fuzz.token_sort_ratio
        )

        if result and result[1] >= threshold:
            return normalized_schema[result[0]]

    return None


def find_columns_with_positions(
    text,
    schema,
    synonyms_path="knowledge/synonyms.json",
    stopwords_path="knowledge/stopwords.json",
    threshold=72
):
    """
    Find schema columns mentioned in natural-language question.

    Returns:
        [
            {
                "column": "Monthly_Income",
                "position": 25,
                "score": 100
            }
        ]
    """

    if not text or not schema:
        return []

    synonyms = load_synonyms(synonyms_path)
    stopwords = set(
        _normalize(x)
        for x in load_stopwords(stopwords_path)
    )

    # ---------------------------------------------------------
    # Tokenize question
    # ---------------------------------------------------------

    raw_tokens = [
        {
            "word": m.group(),
            "position": m.start()
        }
        for m in re.finditer(
            r"[a-z0-9_]+",
            text.lower()
        )
    ]

    if not raw_tokens:
        return []

    # Remove stopwords
    core_tokens = [
        t for t in raw_tokens
        if _normalize(t["word"]) not in stopwords
    ]

    if not core_tokens:
        core_tokens = raw_tokens

    # ---------------------------------------------------------
    # Prepare schema columns
    # ---------------------------------------------------------

    col_specs = []

    for raw_col in schema.keys():

        # IMPORTANT:
        # Always return the actual schema name.
        col = _clean_schema_column(raw_col)

        if not col:
            continue

        norm = _normalize(col)

        if not norm:
            continue

        norm_words = norm.split()

        core_words = [
            w for w in norm_words
            if w not in stopwords
        ]

        if not core_words:
            core_words = norm_words

        col_specs.append({
            "column": col,
            "core_words": core_words,
            "core_phrase": " ".join(core_words),
        })

    if not col_specs:
        return []

    # ---------------------------------------------------------
    # Build synonym lookup
    # ---------------------------------------------------------

    synonym_lookup = _build_synonym_lookup(synonyms)

    # ---------------------------------------------------------
    # Find column matches
    # ---------------------------------------------------------

    best_by_column = {}

    n_tokens = len(core_tokens)

    max_n = max(
        (
            len(spec["core_words"])
            for spec in col_specs
        ),
        default=1
    )

    for n in range(
        min(max_n, n_tokens),
        0,
        -1
    ):

        cols_of_size = [
            s for s in col_specs
            if len(s["core_words"]) == n
        ]

        if not cols_of_size:
            continue

        for i in range(
            n_tokens - n + 1
        ):

            window = core_tokens[
                i:i + n
            ]

            phrase = " ".join(
                _normalize(t["word"])
                for t in window
            )

            if not phrase:
                continue

            phrase_pos = window[0]["position"]

            phrase_candidates = {
                phrase
            }

            # -------------------------------------------------
            # Add synonym target
            # -------------------------------------------------

            if phrase in synonym_lookup:

                target = synonym_lookup[phrase]

                if isinstance(target, str):

                    phrase_candidates.add(
                        _normalize(target)
                    )

                elif isinstance(target, list):

                    for item in target:

                        phrase_candidates.add(
                            _normalize(item)
                        )

            # -------------------------------------------------
            # Compare with schema
            # -------------------------------------------------

            for spec in cols_of_size:

                score = max(
                    fuzz.token_sort_ratio(
                        candidate,
                        spec["core_phrase"]
                    )
                    for candidate in phrase_candidates
                )

                if score >= threshold:

                    previous = best_by_column.get(
                        spec["column"]
                    )

                    if (
                        previous is None
                        or score > previous["score"]
                    ):

                        best_by_column[
                            spec["column"]
                        ] = {
                            "column": spec["column"],
                            "position": phrase_pos,
                            "score": score,
                        }

    # ---------------------------------------------------------
    # Full-question fallback
    # ---------------------------------------------------------

    question_core_phrase = " ".join(
        _normalize(t["word"])
        for t in core_tokens
    )

    for spec in col_specs:

        if spec["column"] in best_by_column:
            continue

        score = fuzz.token_set_ratio(
            question_core_phrase,
            spec["core_phrase"]
        )

        if score < max(
            threshold,
            80
        ):
            continue

        position = None

        for token in core_tokens:

            token_norm = _normalize(
                token["word"]
            )

            for cw in spec["core_words"]:

                if fuzz.ratio(
                    token_norm,
                    cw
                ) >= 85:

                    position = token["position"]
                    break

            if position is not None:
                break

        if position is None:
            position = core_tokens[0]["position"]

        best_by_column[
            spec["column"]
        ] = {
            "column": spec["column"],
            "position": position,
            "score": score,
        }

    return sorted(
        best_by_column.values(),
        key=lambda r: (
            -r["score"],
            r["position"]
        )
    )


def find_columns_in_text(
    text,
    schema,
    synonyms_path="knowledge/synonyms.json"
):
    """Return only matched column names."""

    matches = find_columns_with_positions(
        text,
        schema,
        synonyms_path
    )

    return [
        m["column"]
        for m in matches
    ]