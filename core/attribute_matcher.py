import os
import re
import json
from rapidfuzz import process, fuzz


def load_synonyms(path="knowledge/synonyms.json"):
    """Load column synonyms from JSON."""

    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    if isinstance(data, dict):
        data.pop("_comment", None)
        return data

    return {}


def load_stopwords(path="knowledge/stopwords.json"):
    """Load stopwords from JSON."""

    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []

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
    Normalize text for column matching.

    Examples:
        Monthly Income  -> monthly income
        Monthly_Income  -> monthly income
        monthly-income  -> monthly income
        Gender          -> gender
    """

    if text is None:
        return ""

    text = str(text).strip().lower()

    text = text.replace("_", " ")
    text = text.replace("-", " ")

    return _strip_symbols(text)


def _clean_schema_column(col):
    """Return the exact actual schema column name."""

    if col is None:
        return ""

    return str(col).strip()


def resolve_schema_column(column, schema):
    """
    Resolve any column representation to the exact schema name.

    Examples:

        Monthly Income -> Monthly_Income
        monthly_income -> Monthly_Income
        MONTHLY INCOME -> Monthly_Income
        Student Name   -> Student_Name
    """

    if column is None or not schema:
        return None

    column = str(column).strip()

    if not column:
        return None

    # ---------------------------------------------------------
    # 1. Exact match
    # ---------------------------------------------------------

    if column in schema:
        return column

    # ---------------------------------------------------------
    # 2. Case-insensitive exact match
    # ---------------------------------------------------------

    column_lower = column.lower()

    for raw_col in schema.keys():

        actual = _clean_schema_column(raw_col)

        if actual.lower() == column_lower:
            return actual

    # ---------------------------------------------------------
    # 3. Normalized match
    # ---------------------------------------------------------

    target_norm = _normalize(column)

    if not target_norm:
        return None

    for raw_col in schema.keys():

        actual = _clean_schema_column(raw_col)

        if not actual:
            continue

        if _normalize(actual) == target_norm:
            return actual

    return None


def _build_lookup(schema):
    """Build normalized column lookup."""

    lookup = {}

    if not schema:
        return lookup

    for col in schema.keys():

        actual_col = _clean_schema_column(col)

        if not actual_col:
            continue

        lookup[actual_col.lower()] = actual_col

        normalized = _normalize(actual_col)

        if normalized:
            lookup[normalized] = actual_col

    return lookup


def _build_synonym_lookup(synonyms):
    """Normalize synonym keys."""

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
    """Resolve synonym target to exact schema column."""

    if value is None:
        return None

    # Single target
    if isinstance(value, str):

        resolved = resolve_schema_column(
            value,
            schema
        )

        if resolved:
            return resolved

        # Fuzzy fallback
        normalized_schema = {}

        for col in schema.keys():

            actual = _clean_schema_column(col)
            normalized = _normalize(actual)

            if normalized:
                normalized_schema[normalized] = actual

        target_norm = _normalize(value)

        if normalized_schema and target_norm:

            result = process.extractOne(
                target_norm,
                list(normalized_schema.keys()),
                scorer=fuzz.token_sort_ratio
            )

            if result and result[1] >= 80:
                return normalized_schema[result[0]]

        return None

    # Multiple possible targets
    if isinstance(value, list):

        for item in value:

            resolved = _resolve_synonym_target(
                item,
                schema
            )

            if resolved:
                return resolved

    return None


def match_column(
    word,
    schema,
    synonyms_path="knowledge/synonyms.json",
    threshold=75
):
    """
    Match natural-language column reference
    to the exact schema column.
    """

    if not word or not schema:
        return None

    word_norm = _normalize(word)

    if not word_norm:
        return None

    # ---------------------------------------------------------
    # 1. Exact normalized schema match
    # ---------------------------------------------------------

    resolved = resolve_schema_column(
        word,
        schema
    )

    if resolved:
        return resolved

    # ---------------------------------------------------------
    # 2. Synonym
    # ---------------------------------------------------------

    synonyms = load_synonyms(
        synonyms_path
    )

    synonym_lookup = _build_synonym_lookup(
        synonyms
    )

    if word_norm in synonym_lookup:

        target = synonym_lookup[word_norm]

        resolved = _resolve_synonym_target(
            target,
            schema
        )

        if resolved:
            return resolved

    # ---------------------------------------------------------
    # 3. Fuzzy schema matching
    # ---------------------------------------------------------

    normalized_schema = {}

    for col in schema.keys():

        actual = _clean_schema_column(col)
        normalized = _normalize(actual)

        if normalized:
            normalized_schema[normalized] = actual

    if not normalized_schema:
        return None

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

    ALWAYS returns the exact schema column name.
    """

    if not text or not schema:
        return []

    synonyms = load_synonyms(
        synonyms_path
    )

    stopwords = {
        _normalize(x)
        for x in load_stopwords(
            stopwords_path
        )
    }

    # ---------------------------------------------------------
    # Tokenize
    # ---------------------------------------------------------

    raw_tokens = [
        {
            "word": m.group(),
            "position": m.start()
        }
        for m in re.finditer(
            r"[a-z0-9_]+",
            str(text).lower()
        )
    ]

    if not raw_tokens:
        return []

    core_tokens = [
        token
        for token in raw_tokens
        if _normalize(token["word"]) not in stopwords
    ]

    if not core_tokens:
        core_tokens = raw_tokens

    # ---------------------------------------------------------
    # Schema specifications
    # ---------------------------------------------------------

    col_specs = []

    for raw_col in schema.keys():

        actual_col = _clean_schema_column(
            raw_col
        )

        if not actual_col:
            continue

        normalized = _normalize(
            actual_col
        )

        if not normalized:
            continue

        words = normalized.split()

        core_words = [
            word
            for word in words
            if word not in stopwords
        ]

        if not core_words:
            core_words = words

        col_specs.append({
            "column": actual_col,
            "core_words": core_words,
            "core_phrase": " ".join(core_words),
        })

    if not col_specs:
        return []

    # ---------------------------------------------------------
    # Synonyms
    # ---------------------------------------------------------

    synonym_lookup = _build_synonym_lookup(
        synonyms
    )

    best_by_column = {}

    n_tokens = len(core_tokens)

    max_n = max(
        (
            len(spec["core_words"])
            for spec in col_specs
        ),
        default=1
    )

    # ---------------------------------------------------------
    # Phrase matching
    # ---------------------------------------------------------

    for n in range(
        min(max_n, n_tokens),
        0,
        -1
    ):

        cols_of_size = [
            spec
            for spec in col_specs
            if len(spec["core_words"]) == n
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
                _normalize(
                    token["word"]
                )
                for token in window
            )

            if not phrase:
                continue

            phrase_pos = window[0]["position"]

            phrase_candidates = {
                phrase
            }

            # -------------------------------------------------
            # Synonym target
            # -------------------------------------------------

            if phrase in synonym_lookup:

                target = synonym_lookup[
                    phrase
                ]

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
            # Compare
            # -------------------------------------------------

            for spec in cols_of_size:

                # Exact normalized match
                if spec["core_phrase"] in phrase_candidates:

                    score = 100

                else:

                    score = max(
                        fuzz.token_sort_ratio(
                            candidate,
                            spec["core_phrase"]
                        )
                        for candidate
                        in phrase_candidates
                    )

                if score < threshold:
                    continue

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
    # Full question fallback
    # ---------------------------------------------------------

    question_core_phrase = " ".join(
        _normalize(
            token["word"]
        )
        for token in core_tokens
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

            for column_word in spec["core_words"]:

                if fuzz.ratio(
                    token_norm,
                    column_word
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
        key=lambda result: (
            -result["score"],
            result["position"]
        )
    )


def find_columns_in_text(
    text,
    schema,
    synonyms_path="knowledge/synonyms.json"
):
    """Return only exact schema column names."""

    matches = find_columns_with_positions(
        text,
        schema,
        synonyms_path
    )

    return [
        match["column"]
        for match in matches
    ]