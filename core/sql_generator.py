# core/sql_generator.py

import re

from operator_detector import detect_operators
from attribute_matcher import find_columns_with_positions
from value_matcher import (
    extract_numbers,
    match_categorical_values,
)
from schema_reader import (
    get_numeric_columns,
    get_text_columns,
)


# =========================================================
# CONSTANTS
# =========================================================

_AGGREGATE_INTENTS = {
    "AVG",
    "MAX",
    "MIN",
    "SUM",
}


_AGGREGATE_KEYWORDS = {
    "avg": "AVG",
    "average": "AVG",
    "mean": "AVG",

    "max": "MAX",
    "maximum": "MAX",
    "highest": "MAX",
    "largest": "MAX",
    "biggest": "MAX",

    "min": "MIN",
    "minimum": "MIN",
    "lowest": "MIN",
    "smallest": "MIN",

    "sum": "SUM",
    "total": "SUM",
    "aggregate": "SUM",
}


_SIMPLE_OPS = {
    ">",
    "<",
    ">=",
    "<=",
    "=",
    "!=",
    "<>",
}


_BETWEEN_OPS = {
    "BETWEEN",
    "NOT BETWEEN",
}


_NULL_OPS = {
    "IS NULL",
    "IS NOT NULL",
}


_LIKE_OPS = {
    "LIKE",
}


_SKIP_OPS = {
    "IN",
    "NOT IN",
}


_TOP_PATTERN = re.compile(
    r"\btop\s+(\d+)\b",
    re.IGNORECASE,
)


_BOTTOM_PATTERN = re.compile(
    r"\b(?:bottom|lowest|least|worst|minimum)\s+(\d+)\b",
    re.IGNORECASE,
)


_RANK_WORD_PATTERN = re.compile(
    r"\b(?:highest|maximum|max|largest|biggest|"
    r"lowest|minimum|min|smallest|least)\b",
    re.IGNORECASE,
)


_LOWEST_WORD_PATTERN = re.compile(
    r"\b(?:lowest|minimum|min|smallest|least)\b",
    re.IGNORECASE,
)


# =========================================================
# IDENTIFIER
# =========================================================

def _quote_identifier(name):
    """
    Safely quote SQLite identifier.
    """

    if name is None:
        return '""'

    escaped = str(name).replace(
        '"',
        '""'
    )

    return f'"{escaped}"'


# =========================================================
# COLUMN HELPERS
# =========================================================

def _nearest_column(
    ref_pos,
    column_matches,
    allowed=None,
    exclude=None,
):
    candidates = column_matches

    if allowed is not None:
        candidates = [
            c
            for c in candidates
            if c["column"] in allowed
        ]

    if exclude:
        candidates = [
            c
            for c in candidates
            if c["column"] not in exclude
        ]

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda c: (
            abs(
                c["position"]
                - ref_pos
            ),
            -c.get("score", 0),
        ),
    )["column"]


# =========================================================
# AGGREGATE COLUMN
# =========================================================

def _find_agg_column(
    question,
    column_matches,
    numeric_columns,
):
    """
    Find numeric column for AVG/MAX/MIN/SUM.
    """

    if not numeric_columns:
        return None

    numeric_matches = [
        c
        for c in column_matches
        if c["column"] in numeric_columns
    ]

    if not numeric_matches:
        return None

    agg_keyword_pos = None

    for m in re.finditer(
        r"\S+",
        question.lower(),
    ):
        word = m.group().strip(
            ".,?!"
        )

        if word in _AGGREGATE_KEYWORDS:
            agg_keyword_pos = m.start()
            break

    # No aggregate keyword:
    # use highest confidence numeric column.
    if agg_keyword_pos is None:
        return max(
            numeric_matches,
            key=lambda c: c.get(
                "score",
                0
            ),
        )["column"]

    return min(
        numeric_matches,
        key=lambda c: (
            abs(
                c["position"]
                - agg_keyword_pos
            ),
            -c.get("score", 0),
        ),
    )["column"]


# =========================================================
# GROUP BY COLUMNS
# =========================================================

def _detect_group_by_columns(
    question,
    column_matches,
    text_columns,
):
    """
    Detect one or more GROUP BY columns.

    Examples:

        "average age by department"
            -> ["department"]

        "gender by department"
            -> ["department", "gender"]

        "count gender by department"
            -> ["department", "gender"]

        "department and gender"
            -> ["department", "gender"]
    """

    if not column_matches:
        return []

    question_lower = question.lower()

    # -----------------------------------------------------
    # UNIQUE COLUMN MATCHES
    # -----------------------------------------------------

    unique = {}

    for match in column_matches:
        column = match["column"]

        if column not in unique:
            unique[column] = match
        else:
            old = unique[column]

            if match.get("score", 0) > old.get(
                "score",
                0
            ):
                unique[column] = match

    matches = list(
        unique.values()
    )

    # -----------------------------------------------------
    # "BY <COLUMN>"
    # -----------------------------------------------------

    by_match = re.search(
        r"\bby\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        question_lower,
    )

    if by_match:

        by_position = by_match.start()

        after_by = [
            c
            for c in matches
            if c["position"] >= by_match.end()
        ]

        if after_by:

            # Prefer text/categorical column.
            text_after = [
                c
                for c in after_by
                if c["column"] in text_columns
            ]

            if text_after:
                group_col = min(
                    text_after,
                    key=lambda c: (
                        c["position"],
                        -c.get("score", 0),
                    ),
                )["column"]

            else:
                group_col = min(
                    after_by,
                    key=lambda c: (
                        c["position"],
                        -c.get("score", 0),
                    ),
                )["column"]

            # -------------------------------------------------
            # Find categorical column before "by".
            #
            # Example:
            #     gender by department
            #
            # gender = before by
            # department = after by
            #
            # For SELECT/COUNT style questions, both are
            # useful dimensions.
            # -------------------------------------------------

            before_by = [
                c
                for c in matches
                if c["position"] < by_position
                and c["column"] in text_columns
            ]

            result = [group_col]

            if before_by:

                # Ignore generic words if attribute matcher
                # accidentally matched something far away.
                nearest_before = min(
                    before_by,
                    key=lambda c: (
                        abs(
                            by_position
                            - c["position"]
                        ),
                        -c.get("score", 0),
                    ),
                )

                if (
                    nearest_before["column"]
                    != group_col
                ):
                    result.append(
                        nearest_before["column"]
                    )

            return result

    # -----------------------------------------------------
    # "EACH / EVERY / PER"
    # -----------------------------------------------------

    each_match = re.search(
        r"\b(?:each|every|per)\b",
        question_lower,
    )

    if each_match:

        candidates = [
            c
            for c in matches
            if (
                c["column"] in text_columns
                and c["position"]
                >= each_match.end()
            )
        ]

        if candidates:
            return [
                min(
                    candidates,
                    key=lambda c: (
                        c["position"],
                        -c.get("score", 0),
                    ),
                )["column"]
            ]

    # -----------------------------------------------------
    # "WHICH/WHAT <COLUMN> ..."
    # -----------------------------------------------------

    aggregate_match = re.search(
        r"\b(?:avg|average|mean|max|maximum|highest|"
        r"largest|biggest|min|minimum|lowest|smallest|"
        r"sum|total)\b",
        question_lower,
    )

    if aggregate_match:

        leading_candidates = [
            c
            for c in matches
            if (
                c["column"] in text_columns
                and c["position"]
                < aggregate_match.start()
            )
        ]

        if (
            re.search(
                r"\b(?:which|what)\b",
                question_lower,
            )
            and leading_candidates
        ):
            return [
                max(
                    leading_candidates,
                    key=lambda c: (
                        c["position"],
                        c.get("score", 0),
                    ),
                )["column"]
            ]

    # -----------------------------------------------------
    # FALLBACK
    # -----------------------------------------------------

    return []


# =========================================================
# BACKWARD COMPATIBILITY
# =========================================================

def _detect_group_by(
    question,
    column_matches,
    text_columns,
):
    """
    Backward-compatible helper.
    Returns first group column.
    """

    groups = _detect_group_by_columns(
        question,
        column_matches,
        text_columns,
    )

    return groups[0] if groups else None


# =========================================================
# ORDER + LIMIT
# =========================================================

def _detect_order_limit(
    question,
    column_matches,
    numeric_columns,
    group_by=None,
    aggregate_column=None,
):
    def _column_near(pos):

        candidates = [
            c
            for c in column_matches
            if (
                c["column"] in numeric_columns
                and c["position"] >= pos
            )
        ]

        if not candidates:
            candidates = [
                c
                for c in column_matches
                if c["column"] in numeric_columns
            ]

        if not candidates:
            return None

        return min(
            candidates,
            key=lambda c: (
                abs(
                    c["position"]
                    - pos
                ),
                -c.get("score", 0),
            ),
        )["column"]

    # -----------------------------------------------------
    # TOP N
    # -----------------------------------------------------

    top_match = _TOP_PATTERN.search(
        question
    )

    if top_match:

        order_column = _column_near(
            top_match.end()
        )

        # For aggregate queries, top N often means
        # top N aggregate results.
        if (
            group_by
            and aggregate_column
        ):
            order_column = aggregate_column

        return (
            order_column,
            "DESC",
            int(
                top_match.group(1)
            ),
        )

    # -----------------------------------------------------
    # BOTTOM N
    # -----------------------------------------------------

    bottom_match = _BOTTOM_PATTERN.search(
        question
    )

    if bottom_match:

        order_column = (
            aggregate_column
            if (
                group_by
                and aggregate_column
            )
            else _column_near(
                bottom_match.end()
            )
        )

        return (
            order_column,
            "ASC",
            int(
                bottom_match.group(1)
            ),
        )

    # -----------------------------------------------------
    # HIGHEST / LOWEST GROUP
    # -----------------------------------------------------

    if (
        group_by
        and aggregate_column
        and _RANK_WORD_PATTERN.search(
            question
        )
    ):

        direction = (
            "ASC"
            if _LOWEST_WORD_PATTERN.search(
                question
            )
            else "DESC"
        )

        return (
            aggregate_column,
            direction,
            1,
        )

    return (
        None,
        None,
        None,
    )


# =========================================================
# IMPLICIT NUMERIC FILTERS
# =========================================================

def _extract_implicit_numeric_filters(
    question,
    column_matches,
    numeric_columns,
    filtered_columns,
    all_numbers,
    used_num_ids,
):
    filters = []

    if (
        not column_matches
        or not all_numbers
    ):
        return filters

    lower_question = question.lower()

    for column_match in column_matches:

        column = column_match["column"]

        if column not in numeric_columns:
            continue

        if column in filtered_columns:
            continue

        column_pos = column_match[
            "position"
        ]

        candidates = [
            n
            for n in all_numbers
            if (
                id(n) not in used_num_ids
                and n["position"] > column_pos
            )
        ]

        if not candidates:
            continue

        number = min(
            candidates,
            key=lambda n: n["position"]
        )

        number_pos = number[
            "position"
        ]

        between_text = lower_question[
            column_pos:number_pos
        ]

        # Do not treat numbers belonging to these
        # constructs as implicit "=" filters.
        if re.search(
            r"\b(?:by|for|where|with|having)\b",
            between_text,
        ):
            continue

        if re.search(
            r"\b(?:top|bottom|lowest|highest|"
            r"least|most)\b",
            between_text,
        ):
            continue

        words_between = re.findall(
            r"[a-zA-Z_]+",
            between_text,
        )

        if len(words_between) > 4:
            continue

        filters.append({
            "column": column,
            "operator": "=",
            "value": number["value"],
        })

        filtered_columns.add(
            column
        )

        used_num_ids.add(
            id(number)
        )

    return filters


# =========================================================
# BUILD QUERY
# =========================================================

def build_query(
    question,
    schema,
    intent,
    operators_path="knowledge/operators.json",
    synonyms_path="knowledge/synonyms.json",
):
    """
    Convert natural language into an intermediate query object.

    Important:
        "gender by department"

    becomes approximately:

        intent = SELECT
        group_by_columns = [
            "department",
            "gender"
        ]

    which later becomes:

        SELECT "department", "gender", COUNT(*)
        FROM "data"
        GROUP BY "department", "gender"
    """

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    if not schema:
        raise ValueError(
            "Schema cannot be empty."
        )

    # -----------------------------------------------------
    # NORMALIZE INTENT
    # -----------------------------------------------------

    intent = str(
        intent or "SELECT"
    ).upper().strip()

    valid_intents = {
        "SELECT",
        "COUNT",
        "AVG",
        "MAX",
        "MIN",
        "SUM",
    }

    if intent not in valid_intents:
        intent = "SELECT"

    filters = []
    filtered_columns = set()

    # -----------------------------------------------------
    # SCHEMA TYPES
    # -----------------------------------------------------

    numeric_columns = set(
        get_numeric_columns(
            schema
        )
    )

    text_columns = set(
        get_text_columns(
            schema
        )
    )

    # -----------------------------------------------------
    # ATTRIBUTE MATCHING
    # -----------------------------------------------------

    column_matches = find_columns_with_positions(
        question,
        schema,
        synonyms_path,
    )

    matched_column_names = {
        m["column"]
        for m in column_matches
    }

    # -----------------------------------------------------
    # CATEGORICAL VALUE MATCHING
    # -----------------------------------------------------

    categorical_matches = match_categorical_values(
        question,
        schema,
        allowed_columns=matched_column_names,
        synonyms_path=synonyms_path,
    )

    for match in categorical_matches:

        col = match["column"]

        if col in filtered_columns:
            continue

        # Avoid accidental matching of a column name
        # itself as a categorical value.
        value = match.get(
            "value"
        )

        if value is None:
            continue

        filters.append({
            "column": col,
            "operator": "=",
            "value": value,
        })

        filtered_columns.add(
            col
        )

    # -----------------------------------------------------
    # OPERATORS
    # -----------------------------------------------------

    operators = detect_operators(
        question,
        operators_path,
    )

    all_numbers = extract_numbers(
        question
    )

    used_num_ids = set()

    for op in operators:

        symbol = str(
            op.get(
                "symbol",
                ""
            )
        ).upper()

        op_pos = op.get(
            "position",
            0
        )

        # -------------------------------------------------
        # SKIP IN / NOT IN
        # -------------------------------------------------

        if symbol in _SKIP_OPS:
            continue

        # -------------------------------------------------
        # NULL
        # -------------------------------------------------

        if symbol in _NULL_OPS:

            col = (
                _nearest_column(
                    op_pos,
                    column_matches,
                    exclude=filtered_columns,
                )
            )

            if (
                col
                and col not in filtered_columns
            ):

                filters.append({
                    "column": col,
                    "operator": symbol,
                })

                filtered_columns.add(
                    col
                )

            continue

        # -------------------------------------------------
        # BETWEEN
        # -------------------------------------------------

        if symbol in _BETWEEN_OPS:

            nums_after = sorted(
                [
                    n
                    for n in all_numbers
                    if (
                        n["position"] > op_pos
                        and id(n)
                        not in used_num_ids
                    )
                ],
                key=lambda n: n["position"],
            )

            if len(nums_after) >= 2:

                col = _nearest_column(
                    op_pos,
                    column_matches,
                    allowed=numeric_columns,
                    exclude=filtered_columns,
                )

                if (
                    col
                    and col not in filtered_columns
                ):

                    filters.append({
                        "column": col,
                        "operator": symbol,
                        "value": nums_after[0]["value"],
                        "value2": nums_after[1]["value"],
                    })

                    filtered_columns.add(
                        col
                    )

                    used_num_ids.update({
                        id(nums_after[0]),
                        id(nums_after[1]),
                    })

            continue

        # -------------------------------------------------
        # LIKE
        # -------------------------------------------------

        if symbol in _LIKE_OPS:

            words_after = [
                m
                for m in re.finditer(
                    r"\S+",
                    question.lower(),
                )
                if m.start() > op_pos
            ]

            if words_after:

                val = (
                    words_after[0]
                    .group()
                    .strip(
                        ".,?!"
                    )
                )

                col = (
                    _nearest_column(
                        op_pos,
                        column_matches,
                        allowed=text_columns,
                        exclude=filtered_columns,
                    )
                    or
                    _nearest_column(
                        op_pos,
                        column_matches,
                        exclude=filtered_columns,
                    )
                )

                if (
                    col
                    and col not in filtered_columns
                ):

                    filters.append({
                        "column": col,
                        "operator": "LIKE",
                        "value": f"%{val}%",
                    })

                    filtered_columns.add(
                        col
                    )

            continue

        # -------------------------------------------------
        # SIMPLE OPERATORS
        # -------------------------------------------------

        if symbol in _SIMPLE_OPS:

            nums_after = sorted(
                [
                    n
                    for n in all_numbers
                    if (
                        n["position"] > op_pos
                        and id(n)
                        not in used_num_ids
                    )
                ],
                key=lambda n: n["position"],
            )

            if not nums_after:
                continue

            nearest_num = nums_after[0]

            col = _nearest_column(
                nearest_num["position"],
                column_matches,
                allowed=numeric_columns,
                exclude=filtered_columns,
            )

            if (
                col
                and col not in filtered_columns
            ):

                filters.append({
                    "column": col,
                    "operator": symbol,
                    "value": nearest_num["value"],
                })

                filtered_columns.add(
                    col
                )

                used_num_ids.add(
                    id(nearest_num)
                )

    # -----------------------------------------------------
    # IMPLICIT NUMERIC FILTERS
    # -----------------------------------------------------

    implicit_filters = (
        _extract_implicit_numeric_filters(
            question,
            column_matches,
            numeric_columns,
            filtered_columns,
            all_numbers,
            used_num_ids,
        )
    )

    filters.extend(
        implicit_filters
    )

    # -----------------------------------------------------
    # AGGREGATE
    # -----------------------------------------------------

    agg_col = None

    if intent in _AGGREGATE_INTENTS:

        agg_col = _find_agg_column(
            question,
            column_matches,
            numeric_columns,
        )

        # -------------------------------------------------
        # IMPORTANT FALLBACK
        #
        # If classifier incorrectly predicts aggregate for
        # a categorical query such as:
        #
        # "gender by department"
        #
        # do NOT fail.
        #
        # If there is no numeric column mentioned, convert
        # it to SELECT.
        # -------------------------------------------------

        if agg_col is None:

            has_numeric_match = any(
                c["column"] in numeric_columns
                for c in column_matches
            )

            if not has_numeric_match:

                intent = "SELECT"

    # -----------------------------------------------------
    # GROUP BY
    # -----------------------------------------------------

    group_by_columns = (
        _detect_group_by_columns(
            question,
            column_matches,
            text_columns,
        )
    )

    # Remove duplicates.
    cleaned_groups = []

    for col in group_by_columns:

        if col not in cleaned_groups:
            cleaned_groups.append(
                col
            )

    group_by_columns = cleaned_groups

    # -----------------------------------------------------
    # Backward-compatible single group_by
    # -----------------------------------------------------

    group_by_col = (
        group_by_columns[0]
        if group_by_columns
        else None
    )

    # -----------------------------------------------------
    # IMPORTANT:
    #
    # "gender by department"
    #
    # should have both dimensions:
    #
    # department + gender
    #
    # But aggregate queries such as:
    #
    # "average age by department"
    #
    # should only group by department.
    # -----------------------------------------------------

    if (
        intent in _AGGREGATE_INTENTS
        and agg_col
        and len(group_by_columns) > 1
    ):

        group_by_columns = [
            col
            for col in group_by_columns
            if col != agg_col
        ]

        group_by_col = (
            group_by_columns[0]
            if group_by_columns
            else None
        )

    # -----------------------------------------------------
    # COUNT
    # -----------------------------------------------------

    if intent == "COUNT":

        # For:
        #
        # count gender by department
        #
        # keep both categorical dimensions.
        pass

    # -----------------------------------------------------
    # SELECT CATEGORICAL BY CATEGORICAL
    # -----------------------------------------------------

    if (
        intent == "SELECT"
        and len(group_by_columns) == 1
    ):

        group_column = group_by_columns[0]

        other_dimension = []

        for match in column_matches:

            col = match["column"]

            if col == group_column:
                continue

            if col not in text_columns:
                continue

            if col in filtered_columns:
                continue

            if col not in other_dimension:
                other_dimension.append(
                    col
                )

        # Example:
        #
        # gender by department
        #
        # group_by initially:
        # department, gender
        #
        # This fallback handles cases where attribute
        # matcher position information is imperfect.
        if other_dimension:

            before = [
                c
                for c in column_matches
                if (
                    c["column"]
                    in other_dimension
                    and c["position"]
                    < question.lower().find(
                        group_column.lower()
                    )
                )
            ]

            if before:

                other = max(
                    before,
                    key=lambda c: (
                        c["position"],
                        c.get("score", 0),
                    ),
                )["column"]

                if other != group_column:
                    group_by_columns = [
                        group_column,
                        other,
                    ]

    # -----------------------------------------------------
    # ORDER / LIMIT
    # -----------------------------------------------------

    order_col, order_dir, limit = (
        _detect_order_limit(
            question,
            column_matches,
            numeric_columns,
            group_by=(
                group_by_col
                or (
                    group_by_columns[0]
                    if group_by_columns
                    else None
                )
            ),
            aggregate_column=agg_col,
        )
    )

    # -----------------------------------------------------
    # RETURN
    # -----------------------------------------------------

    return {
        "intent": intent,

        "filters": filters,

        "agg_column": agg_col,

        # Backward compatible
        "group_by": group_by_col,

        # New multi-column support
        "group_by_columns": group_by_columns,

        "order_by": order_col,

        "order_dir": (
            order_dir
            or "DESC"
        ),

        "limit": limit,

        "order_by_aggregate": bool(
            agg_col
            and order_col == agg_col
            and (
                group_by_col
                or group_by_columns
            )
        ),
    }


# =========================================================
# SQL VALUE
# =========================================================

def _is_numeric_value(value):

    if value is None:
        return False

    value = str(
        value
    ).strip()

    if not value:
        return False

    return bool(
        re.fullmatch(
            r"-?\d+(?:\.\d+)?",
            value,
        )
    )


def _sql_value(value):
    """
    Convert Python value to safe SQL literal.
    """

    if value is None:
        return "NULL"

    value_str = str(
        value
    ).strip()

    if _is_numeric_value(
        value_str
    ):
        return value_str

    safe = value_str.replace(
        "'",
        "''"
    )

    return f"'{safe}'"


# =========================================================
# QUERY TO SQL
# =========================================================

def query_to_sql(
    query,
    table_name="data",
):
    """
    Convert intermediate query object into SQLite SQL.
    """

    if not query:
        raise ValueError(
            "Query object is empty."
        )

    intent = str(
        query.get(
            "intent",
            "SELECT"
        )
    ).upper()

    filters = query.get(
        "filters",
        []
    )

    agg_column = query.get(
        "agg_column"
    )

    # -----------------------------------------------------
    # GROUP COLUMNS
    # -----------------------------------------------------

    group_by_columns = query.get(
        "group_by_columns"
    )

    if not group_by_columns:

        old_group = query.get(
            "group_by"
        )

        if old_group:
            group_by_columns = [
                old_group
            ]

        else:
            group_by_columns = []

    # Remove duplicates.
    clean_groups = []

    for col in group_by_columns:

        if col and col not in clean_groups:
            clean_groups.append(
                col
            )

    group_by_columns = clean_groups

    order_by = query.get(
        "order_by"
    )

    order_dir = str(
        query.get(
            "order_dir",
            "DESC"
        )
    ).upper()

    if order_dir not in {
        "ASC",
        "DESC",
    }:
        order_dir = "DESC"

    limit = query.get(
        "limit"
    )

    tbl = _quote_identifier(
        table_name
    )

    aggregate_alias = None

    # -----------------------------------------------------
    # TOP/BOTTOM OVERRIDE
    # -----------------------------------------------------

    agg_overridden = (
        limit is not None
        and not group_by_columns
        and intent in _AGGREGATE_INTENTS
    )

    # =====================================================
    # SELECT
    # =====================================================

    if (
        intent == "SELECT"
        and len(group_by_columns) >= 2
    ):

        select_columns = [
            _quote_identifier(
                col
            )
            for col in group_by_columns
        ]

        select_columns.append(
            "COUNT(*)"
        )

        select_part = (
            "SELECT "
            + ", ".join(
                select_columns
            )
        )

    elif (
        intent == "SELECT"
        and len(group_by_columns) == 1
    ):

        select_part = (
            "SELECT "
            + _quote_identifier(
                group_by_columns[0]
            )
            + ", COUNT(*)"
        )

    elif (
        intent == "SELECT"
        or agg_overridden
    ):

        select_part = "SELECT *"

    # =====================================================
    # COUNT
    # =====================================================

    elif intent == "COUNT":

        if group_by_columns:

            select_columns = [
                _quote_identifier(
                    col
                )
                for col in group_by_columns
            ]

            select_columns.append(
                "COUNT(*)"
            )

            select_part = (
                "SELECT "
                + ", ".join(
                    select_columns
                )
            )

        else:

            select_part = (
                "SELECT COUNT(*)"
            )

    # =====================================================
    # AVG / MAX / MIN / SUM
    # =====================================================

    elif intent in _AGGREGATE_INTENTS:

        if not agg_column:

            raise ValueError(
                f"Could not determine which "
                f"column to apply '{intent}' to."
            )

        col = _quote_identifier(
            agg_column
        )

        # -------------------------------------------------
        # Aggregate + GROUP BY
        # -------------------------------------------------

        if group_by_columns:

            alias_base = re.sub(
                r"[^a-zA-Z0-9]+",
                "_",
                str(
                    agg_column
                ),
            ).strip(
                "_"
            ).lower()

            aggregate_alias = (
                f"{intent.lower()}_"
                f"{alias_base}"
            )

            group_parts = [
                _quote_identifier(
                    g
                )
                for g in group_by_columns
            ]

            group_parts.append(
                f"{intent}({col}) AS "
                f"{_quote_identifier(aggregate_alias)}"
            )

            select_part = (
                "SELECT "
                + ", ".join(
                    group_parts
                )
            )

        # -------------------------------------------------
        # Normal aggregate
        # -------------------------------------------------

        else:

            select_part = (
                f"SELECT "
                f"{intent}({col})"
            )

    # =====================================================
    # FALLBACK
    # =====================================================

    else:

        select_part = "SELECT *"

    # =====================================================
    # FROM
    # =====================================================

    sql = (
        f"{select_part} "
        f"FROM {tbl}"
    )

    # =====================================================
    # WHERE
    # =====================================================

    if filters:

        conditions = []

        for f in filters:

            if not isinstance(
                f,
                dict
            ):
                continue

            column = f.get(
                "column"
            )

            if not column:
                continue

            col_q = _quote_identifier(
                column
            )

            operator = str(
                f.get(
                    "operator",
                    "="
                )
            ).upper().strip()

            # -------------------------------------------------
            # NULL
            # -------------------------------------------------

            if operator in _NULL_OPS:

                conditions.append(
                    f"{col_q} {operator}"
                )

            # -------------------------------------------------
            # BETWEEN
            # -------------------------------------------------

            elif operator in _BETWEEN_OPS:

                v1 = _sql_value(
                    f.get(
                        "value"
                    )
                )

                v2 = _sql_value(
                    f.get(
                        "value2"
                    )
                )

                conditions.append(
                    f"{col_q} "
                    f"{operator} "
                    f"{v1} AND {v2}"
                )

            # -------------------------------------------------
            # NORMAL
            # -------------------------------------------------

            else:

                value = f.get(
                    "value",
                    ""
                )

                conditions.append(
                    f"{col_q} "
                    f"{operator} "
                    f"{_sql_value(value)}"
                )

        if conditions:

            sql += (
                " WHERE "
                + " AND ".join(
                    conditions
                )
            )

    # =====================================================
    # GROUP BY
    # =====================================================

    if group_by_columns:

        group_parts = [
            _quote_identifier(
                col
            )
            for col in group_by_columns
        ]

        sql += (
            " GROUP BY "
            + ", ".join(
                group_parts
            )
        )

    # =====================================================
    # ORDER BY
    # =====================================================

    if order_by:

        if (
            query.get(
                "order_by_aggregate"
            )
            and aggregate_alias
        ):

            order_expression = (
                _quote_identifier(
                    aggregate_alias
                )
            )

        else:

            order_expression = (
                _quote_identifier(
                    order_by
                )
            )

        sql += (
            " ORDER BY "
            + order_expression
            + " "
            + order_dir
        )

    # =====================================================
    # LIMIT
    # =====================================================

    if limit is not None:

        try:
            limit_value = int(
                limit
            )

            if limit_value > 0:

                sql += (
                    f" LIMIT "
                    f"{limit_value}"
                )

        except (
            TypeError,
            ValueError,
        ):
            pass

    return sql