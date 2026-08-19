import os
import re
import json
from rapidfuzz import process, fuzz


# =========================================================
# LOAD SYNONYMS
# =========================================================

def load_synonyms(path="knowledge/synonyms.json"):
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
# LOAD STOPWORDS
# =========================================================

def load_stopwords(path="knowledge/stopwords.json"):
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return [
                str(x).lower().strip()
                for x in data
            ]

        return []

    except (OSError, json.JSONDecodeError):
        return []


# =========================================================
# NORMALIZATION
# =========================================================

def _strip_symbols(text):
    text = str(text)

    # Remove text inside parentheses
    text = re.sub(
        r"\([^)]*\)",
        " ",
        text
    )

    # Normalize underscores / hyphens
    text = text.replace("_", " ")
    text = text.replace("-", " ")

    # Keep alphanumeric characters
    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text.lower()
    )

    # Collapse spaces
    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


def _normalize(text):
    return _strip_symbols(text)


# =========================================================
# BUILD COLUMN LOOKUP
# =========================================================

def _build_lookup(schema):
    """
    Build several normalized representations of columns.

    Handles examples like:

        Salary
        salary
        Salary
        Department
        Marital Status
        marital_status
        " Department          "
    """

    lookup = {}

    for col in schema.keys():

        original = str(col)

        variants = {
            original.lower().strip(),
            _normalize(original),
            original.lower().replace("_", " ").strip(),
            original.lower().replace("-", " ").strip(),
        }

        for variant in variants:

            if not variant:
                continue

            lookup[variant] = col

    return lookup


# =========================================================
# MATCH SINGLE COLUMN
# =========================================================

def match_column(
    word,
    schema,
    synonyms_path="knowledge/synonyms.json",
    threshold=70
):
    if not word or not schema:
        return None

    synonyms = load_synonyms(
        synonyms_path
    )

    word_norm = _normalize(word)

    if not word_norm:
        return None

    lookup = _build_lookup(schema)

    candidates = list(
        lookup.keys()
    )

    if not candidates:
        return None

    # -----------------------------------------------------
    # 1. EXACT MATCH
    # -----------------------------------------------------

    if word_norm in lookup:
        return lookup[word_norm]

    # -----------------------------------------------------
    # 2. SYNONYM EXACT MATCH
    # -----------------------------------------------------

    if word_norm in synonyms:

        synonym_norm = _normalize(
            synonyms[word_norm]
        )

        if synonym_norm in lookup:
            return lookup[synonym_norm]

    # -----------------------------------------------------
    # 3. FUZZY DIRECT MATCH
    # -----------------------------------------------------

    result = process.extractOne(
        word_norm,
        candidates,
        scorer=fuzz.token_sort_ratio
    )

    if result:

        matched = result[0]
        score = result[1]

        if score >= threshold:
            return lookup[matched]

    # -----------------------------------------------------
    # 4. FUZZY SYNONYM MATCH
    # -----------------------------------------------------

    if word_norm in synonyms:

        synonym_norm = _normalize(
            synonyms[word_norm]
        )

        result = process.extractOne(
            synonym_norm,
            candidates,
            scorer=fuzz.token_sort_ratio
        )

        if result:

            matched = result[0]
            score = result[1]

            if score >= threshold:
                return lookup[matched]

    return None


# =========================================================
# COLUMN SPECS
# =========================================================

def _build_column_specs(
    schema,
    stopwords
):
    specs = []

    for col in schema.keys():

        original = str(col)

        normalized = _normalize(
            original
        )

        if not normalized:
            continue

        words = normalized.split()

        core_words = [
            w
            for w in words
            if w not in stopwords
        ]

        if not core_words:
            core_words = words

        specs.append({
            "column": original,
            "normalized": normalized,
            "words": words,
            "core_words": core_words,
            "core_phrase": " ".join(core_words),
        })

    return specs


# =========================================================
# FIND COLUMNS WITH POSITIONS
# =========================================================

def find_columns_with_positions(
    text,
    schema,
    synonyms_path="knowledge/synonyms.json",
    stopwords_path="knowledge/stopwords.json",
    threshold=72
):
    """
    Find schema columns mentioned in a natural-language question.

    Returns:

        [
            {
                "column": "Salary",
                "position": 6,
                "score": 100
            }
        ]
    """

    if not text or not schema:
        return []

    text = str(text)

    synonyms = load_synonyms(
        synonyms_path
    )

    stopwords = set(
        load_stopwords(
            stopwords_path
        )
    )

    # -----------------------------------------------------
    # TOKENIZE QUESTION
    # -----------------------------------------------------

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

    # Keep original tokens too
    core_tokens = [
        token
        for token in raw_tokens
        if token["word"] not in stopwords
    ]

    if not core_tokens:
        core_tokens = raw_tokens

    # -----------------------------------------------------
    # COLUMN SPECS
    # -----------------------------------------------------

    col_specs = _build_column_specs(
        schema,
        stopwords
    )

    if not col_specs:
        return []

    best_by_column = {}

    # -----------------------------------------------------
    # DIRECT MULTI-WORD / SINGLE-WORD MATCHING
    # -----------------------------------------------------

    max_n = max(
        (
            len(spec["core_words"])
            for spec in col_specs
        ),
        default=1
    )

    max_n = min(
        max_n,
        len(core_tokens)
    )

    for n in range(
        max_n,
        0,
        -1
    ):

        columns_of_size = [
            spec
            for spec in col_specs
            if len(spec["core_words"]) == n
        ]

        if not columns_of_size:
            continue

        for i in range(
            len(core_tokens) - n + 1
        ):

            window = core_tokens[
                i:i + n
            ]

            phrase = " ".join(
                token["word"]
                for token in window
            )

            position = window[0]["position"]

            # -------------------------------------------------
            # Candidate phrases
            # -------------------------------------------------

            phrase_candidates = {
                phrase
            }

            # Single-word synonym
            if (
                n == 1
                and phrase in synonyms
            ):
                phrase_candidates.add(
                    _normalize(
                        synonyms[phrase]
                    )
                )

            # -------------------------------------------------
            # Compare against columns
            # -------------------------------------------------

            for spec in columns_of_size:

                scores = [
                    fuzz.token_sort_ratio(
                        candidate,
                        spec["core_phrase"]
                    )
                    for candidate in phrase_candidates
                ]

                score = max(
                    scores
                ) if scores else 0

                # Exact normalized match gets maximum score
                if phrase == spec["core_phrase"]:
                    score = 100

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
                        "position": position,
                        "score": score,
                    }

    # -----------------------------------------------------
    # SYNONYM-BASED SINGLE WORD MATCH
    # -----------------------------------------------------

    for token in core_tokens:

        word = token["word"]

        if word not in synonyms:
            continue

        synonym = _normalize(
            synonyms[word]
        )

        if not synonym:
            continue

        for spec in col_specs:

            score = fuzz.token_sort_ratio(
                synonym,
                spec["core_phrase"]
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
                    "position": token["position"],
                    "score": score,
                }

    # -----------------------------------------------------
    # QUESTION-WIDE FALLBACK
    # -----------------------------------------------------

    question_core_phrase = " ".join(
        token["word"]
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

            for column_word in spec["core_words"]:

                if fuzz.ratio(
                    token["word"],
                    column_word
                ) >= 85:

                    position = token[
                        "position"
                    ]
                    break

            if position is not None:
                break

        if position is None:
            position = 0

        best_by_column[
            spec["column"]
        ] = {
            "column": spec["column"],
            "position": position,
            "score": score,
        }

    # -----------------------------------------------------
    # RETURN SORTED
    # -----------------------------------------------------

    return sorted(
        best_by_column.values(),
        key=lambda item: (
            item["position"],
            -item["score"]
        )
    )


# =========================================================
# FIND COLUMNS ONLY
# =========================================================

def find_columns_in_text(
    text,
    schema,
    synonyms_path="knowledge/synonyms.json"
):
    matches = find_columns_with_positions(
        text,
        schema,
        synonyms_path
    )

    return [
        match["column"]
        for match in matches
    ]