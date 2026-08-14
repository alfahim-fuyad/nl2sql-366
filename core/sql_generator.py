# core/sql_generator.py

import re

from operator_detector import detect_operators
from attribute_matcher import find_columns_with_positions
from value_matcher import extract_numbers, match_categorical_values
from schema_reader import get_numeric_columns, get_text_columns


# =========================================================
# AGGREGATE INTENTS
# =========================================================

_AGGREGATE_INTENTS = {"AVG", "MAX", "MIN", "SUM"}

_AGGREGATE_KEYWORDS = {
    "avg": "AVG",
    "average": "AVG",
    "mean": "AVG",

    "max": "MAX",
    "maximum": "MAX",
    "highest": "MAX",
    "largest": "MAX",
    "biggest": "MAX",
    "top": "MAX",

    "min": "MIN",
    "minimum": "MIN",
    "lowest": "MIN",
    "smallest": "MIN",

    "sum": "SUM",
    "total": "SUM",
    "aggregate": "SUM",
}


# =========================================================
# OPERATORS
# =========================================================

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


# =========================================================
# REGEX PATTERNS
# =========================================================

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
# COLUMN COUNT PATTERN
# =========================================================

_COLUMN_COUNT_PATTERN = re.compile(
    r"\b(?:"
    r"how\s+many\s+columns?|"
    r"how\s+many\s+column|"
    r"number\s+of\s+columns?|"
    r"count\s+of\s+columns?|"
    r"total\s+columns?|"
    r"how\s+many\s+fields?|"
    r"number\s+of\s+fields?|"
    r"count\s+of\s+fields?"
    r")\b",
    re.IGNORECASE,
)


# =========================================================
# QUOTE SQL IDENTIFIER
# =========================================================

def _quote_identifier(name):
    """
    Safely quote SQLite identifiers.
    """
    return f'"{name.replace(chr(34), chr(34) + chr(34))}"'


# =========================================================
# FIND NEAREST COLUMN
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
            abs(c["position"] - ref_pos),
            -c["score"],
        ),
    )["column"]


# =========================================================
# FIND AGGREGATE COLUMN
# =========================================================

def _find_agg_column(
    question,
    column_matches,
    numeric_columns,
):
    if not numeric_columns:
        return None

    agg_keyword_pos = None

    for m in re.finditer(
        r"\S+",
        question.lower(),
    ):
        if m.group() in _AGGREGATE_KEYWORDS:
            agg_keyword_pos = m.start()
            break

    numeric_matches = [
        c
        for c in column_matches
        if c["column"] in numeric_columns
    ]

    if not numeric_matches:
        return None

    # No aggregate keyword:
    # choose highest-scoring numeric column.
    if agg_keyword_pos is None:
        return max(
            numeric_matches,
            key=lambda c: c["score"],
        )["column"]

    # Aggregate keyword exists:
    # choose nearest numeric column.
    return min(
        numeric_matches,
        key=lambda c: (
            abs(
                c["position"]
                - agg_keyword_pos
            ),
            -c["score"],
        ),
    )["column"]


# =========================================================
# DETECT GROUP BY
# =========================================================

def _detect_group_by(
    question,
    column_matches,
    text_columns,
):

    m = re.search(
        r"\bby\b",
        question,
        re.IGNORECASE,
    )

    if not m:

        # -------------------------------------------------
        # Example:
        #
        # Which department has the highest average salary?
        # -------------------------------------------------

        aggregate_match = re.search(
            r"\b(?:avg|average|mean|max|maximum|highest|"
            r"largest|biggest|min|minimum|lowest|smallest|"
            r"sum|total)\b",
            question,
            re.IGNORECASE,
        )

        if not aggregate_match:
            return None

        leading_candidates = [
            c
            for c in column_matches
            if (
                c["column"] in text_columns
                and c["position"]
                < aggregate_match.start()
            )
        ]

        if (
            re.search(
                r"\b(?:which|what)\b",
                question,
                re.IGNORECASE,
            )
            and leading_candidates
        ):
            return max(
                leading_candidates,
                key=lambda c: (
                    c["position"],
                    c["score"],
                ),
            )["column"]

        # -------------------------------------------------
        # Example:
        #
        # average salary for each department
        # average salary per department
        # -------------------------------------------------

        each_match = re.search(
            r"\b(?:each|every|per)\b",
            question,
            re.IGNORECASE,
        )

        if each_match:

            candidates = [
                c
                for c in column_matches
                if (
                    c["column"] in text_columns
                    and c["position"]
                    >= each_match.end()
                )
            ]

            if candidates:
                return min(
                    candidates,
                    key=lambda c: (
                        c["position"],
                        -c["score"],
                    ),
                )["column"]

        return None

    # -----------------------------------------------------
    # "by department"
    # -----------------------------------------------------

    pos = m.end()

    candidates = [
        c
        for c in column_matches
        if c["position"] >= pos
    ]

    if not candidates:
        return None

    text_candidates = [
        c
        for c in candidates
        if c["column"] in text_columns
    ]

    candidates = (
        text_candidates
        or candidates
    )

    return min(
        candidates,
        key=lambda c: (
            c["position"],
            -c["score"],
        ),
    )["column"]


# =========================================================
# DETECT ORDER BY + LIMIT
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
                    c["position"] - pos
                ),
                -c["score"],
            ),
        )["column"]

    # -----------------------------------------------------
    # TOP N
    # -----------------------------------------------------

    top_m = _TOP_PATTERN.search(
        question
    )

    if top_m:

        return (
            _column_near(
                top_m.end()
            ),
            "DESC",
            int(
                top_m.group(1)
            ),
        )

    # -----------------------------------------------------
    # BOTTOM N
    # -----------------------------------------------------

    bot_m = _BOTTOM_PATTERN.search(
        question
    )

    if bot_m:

        order_column = (
            aggregate_column
            if (
                group_by
                and aggregate_column
            )
            else _column_near(
                bot_m.end()
            )
        )

        return (
            order_column,
            "ASC",
            int(
                bot_m.group(1)
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

    return None, None, None


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

    filters = []

    filtered_columns = set()

    # =====================================================
    # COLUMN COUNT DETECTION
    # =====================================================

    is_column_count = bool(
        _COLUMN_COUNT_PATTERN.search(
            question
        )
    )

    # =====================================================
    # GET COLUMN TYPES
    # =====================================================

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

    # =====================================================
    # FIND COLUMN MATCHES
    # =====================================================

    column_matches = find_columns_with_positions(
        question,
        schema,
        synonyms_path,
    )

    matched_column_names = {
        m["column"]
        for m in column_matches
    }

    # =====================================================
    # CATEGORICAL VALUES
    # =====================================================

    # Do not create accidental filters for column-count
    # questions.

    if not is_column_count:

        for match in match_categorical_values(
            question,
            schema,
            allowed_columns=matched_column_names,
        ):

            col = match["column"]

            if col not in filtered_columns:

                filters.append(
                    {
                        "column": col,
                        "operator": "=",
                        "value": match["value"],
                    }
                )

                filtered_columns.add(
                    col
                )

    # =====================================================
    # DETECT OPERATORS
    # =====================================================

    if is_column_count:

        operators = []

    else:

        operators = detect_operators(
            question,
            operators_path,
        )

    # =====================================================
    # EXTRACT NUMBERS
    # =====================================================

    if is_column_count:

        all_numbers = []

    else:

        all_numbers = extract_numbers(
            question
        )

    used_num_ids = set()

    # =====================================================
    # PROCESS OPERATORS
    # =====================================================

    for op in operators:

        symbol = op["symbol"]

        op_pos = op["position"]

        # -------------------------------------------------
        # SKIP IN / NOT IN
        # -------------------------------------------------

        if symbol in _SKIP_OPS:
            continue

        # -------------------------------------------------
        # NULL OPERATORS
        # -------------------------------------------------

        if symbol in _NULL_OPS:

            col = (
                _nearest_column(
                    op_pos,
                    column_matches,
                    allowed=numeric_columns,
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

                filters.append(
                    {
                        "column": col,
                        "operator": symbol,
                    }
                )

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

                    filters.append(
                        {
                            "column": col,
                            "operator": symbol,
                            "value": nums_after[0]["value"],
                            "value2": nums_after[1]["value"],
                        }
                    )

                    filtered_columns.add(
                        col
                    )

                    used_num_ids.update(
                        {
                            id(nums_after[0]),
                            id(nums_after[1]),
                        }
                    )

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

                val = words_after[0].group()

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

                    filters.append(
                        {
                            "column": col,
                            "operator": "LIKE",
                            "value": f"%{val}%",
                        }
                    )

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

                filters.append(
                    {
                        "column": col,
                        "operator": symbol,
                        "value": nearest_num["value"],
                    }
                )

                filtered_columns.add(
                    col
                )

                used_num_ids.add(
                    id(nearest_num)
                )

    # =====================================================
    # AGGREGATE COLUMN
    # =====================================================

    agg_col = None

    if (
        not is_column_count
        and intent in _AGGREGATE_INTENTS
    ):

        agg_col = _find_agg_column(
            question,
            column_matches,
            numeric_columns,
        )

    # =====================================================
    # GROUP BY
    # =====================================================

    if is_column_count:

        group_by_col = None

    else:

        group_by_col = _detect_group_by(
            question,
            column_matches,
            text_columns,
        )

    # =====================================================
    # ORDER BY + LIMIT
    # =====================================================

    if is_column_count:

        order_col = None
        order_dir = None
        limit = None

    else:

        (
            order_col,
            order_dir,
            limit,
        ) = _detect_order_limit(
            question,
            column_matches,
            numeric_columns,
            group_by=group_by_col,
            aggregate_column=agg_col,
        )

    # =====================================================
    # RETURN QUERY OBJECT
    # =====================================================

    return {
        # Keep the original question.
        "question": question,

        "intent": intent,

        "filters": filters,

        "agg_column": agg_col,

        "group_by": group_by_col,

        "order_by": order_col,

        "order_dir": order_dir or "DESC",

        "limit": limit,

        "order_by_aggregate": bool(
            group_by_col
            and agg_col
            and order_col == agg_col
        ),

        # IMPORTANT:
        # Used by the executor to identify a column-count
        # request.
        "is_column_count": is_column_count,
    }


# =========================================================
# QUERY OBJECT -> SQL
# =========================================================

def query_to_sql(
    query,
    table_name="data",
):

    intent = query["intent"]

    filters = query.get(
        "filters",
        [],
    )

    agg_column = query.get(
        "agg_column"
    )

    group_by = query.get(
        "group_by"
    )

    order_by = query.get(
        "order_by"
    )

    order_dir = query.get(
        "order_dir",
        "DESC",
    )

    limit = query.get(
        "limit"
    )

    tbl = _quote_identifier(
        table_name
    )

    aggregate_alias = None

    # =====================================================
    # COLUMN COUNT
    # =====================================================
    #
    # IMPORTANT:
    #
    # Never return a custom marker such as:
    #
    # __COLUMN_COUNT__
    #
    # because the SQL validator only accepts SELECT
    # statements.
    #
    # Instead, generate a completely valid SELECT query.
    #
    # The executor can identify this request using:
    #
    # query["is_column_count"] == True
    #
    # and calculate the actual number of columns from
    # the loaded schema.
    #
    # =====================================================

    question = query.get(
        "question",
        "",
    )

    is_column_count = (
        query.get(
            "is_column_count",
            False,
        )
        or
        bool(
            _COLUMN_COUNT_PATTERN.search(
                question
            )
        )
    )

    if is_column_count:

        return (
            f"SELECT * FROM {tbl} LIMIT 1"
        )

    # =====================================================
    # AGGREGATE OVERRIDE
    # =====================================================

    agg_overridden = (
        limit is not None
        and group_by is None
        and intent in _AGGREGATE_INTENTS
    )

    # =====================================================
    # SELECT
    # =====================================================

    if (
        intent == "SELECT"
        or agg_overridden
    ):

        select_part = "SELECT *"

    # =====================================================
    # COUNT
    # =====================================================

    elif intent == "COUNT":

        if group_by:

            select_part = (
                "SELECT "
                f"{_quote_identifier(group_by)}, "
                "COUNT(*)"
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
                f"Could not determine which column "
                f"to apply '{intent}' to. "
                "Try rephrasing your question "
                "with the column name, "
                f"e.g. 'average of <column name>'."
            )

        col = _quote_identifier(
            agg_column
        )

        if group_by:

            clean_column_name = re.sub(
                r"[^a-zA-Z0-9]+",
                "_",
                agg_column,
            ).strip(
                "_"
            ).lower()

            aggregate_alias = (
                f"{intent.lower()}_"
                f"{clean_column_name}"
            )

            select_part = (
                "SELECT "
                f"{_quote_identifier(group_by)}, "
                f"{intent}({col}) AS "
                f"{_quote_identifier(aggregate_alias)}"
            )

        else:

            select_part = (
                f"SELECT {intent}({col})"
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
        f"{select_part} FROM {tbl}"
    )

    # =====================================================
    # WHERE
    # =====================================================

    if filters:

        conditions = []

        for f in filters:

            col_q = _quote_identifier(
                f["column"]
            )

            operator = f["operator"]

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

                v1 = f.get(
                    "value",
                    "",
                )

                v2 = f.get(
                    "value2",
                    "",
                )

                conditions.append(
                    f"{col_q} {operator} "
                    f"{v1} AND {v2}"
                )

            # -------------------------------------------------
            # OTHER OPERATORS
            # -------------------------------------------------

            else:

                value = str(
                    f.get(
                        "value",
                        "",
                    )
                )

                # Numeric value
                if value.replace(
                    ".",
                    "",
                    1,
                ).lstrip(
                    "-"
                ).isdigit():

                    conditions.append(
                        f"{col_q} "
                        f"{operator} "
                        f"{value}"
                    )

                # Text value
                else:

                    safe = value.replace(
                        "'",
                        "''",
                    )

                    conditions.append(
                        f"{col_q} "
                        f"{operator} "
                        f"'{safe}'"
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

    if group_by:

        sql += (
            " GROUP BY "
            f"{_quote_identifier(group_by)}"
        )

    # =====================================================
    # ORDER BY
    # =====================================================

    if order_by:

        order_expression = (
            _quote_identifier(
                aggregate_alias
            )
            if (
                query.get(
                    "order_by_aggregate"
                )
                and aggregate_alias
            )
            else _quote_identifier(
                order_by
            )
        )

        sql += (
            " ORDER BY "
            f"{order_expression} "
            f"{order_dir}"
        )

    # =====================================================
    # LIMIT
    # =====================================================

    if limit is not None:

        sql += (
            f" LIMIT {int(limit)}"
        )

    # =====================================================
    # RETURN SQL
    # =====================================================

    return sql