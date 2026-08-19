import re

from operator_detector import detect_operators
from attribute_matcher import find_columns_with_positions
from value_matcher import (
    extract_numbers,
    match_categorical_values
)
from schema_reader import (
    get_numeric_columns,
    get_text_columns
)


# =========================================================
# CONSTANTS
# =========================================================

_AGGREGATE_INTENTS = {
    "AVG",
    "MAX",
    "MIN",
    "SUM"
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
    "<>"
}


_BETWEEN_OPS = {
    "BETWEEN",
    "NOT BETWEEN"
}


_NULL_OPS = {
    "IS NULL",
    "IS NOT NULL"
}


_LIKE_OPS = {
    "LIKE"
}


_SKIP_OPS = {
    "IN",
    "NOT IN"
}


_TOP_PATTERN = re.compile(
    r"\btop\s+(\d+)\b",
    re.IGNORECASE
)


_BOTTOM_PATTERN = re.compile(
    r"\b(?:bottom|lowest|least|worst|minimum)\s+(\d+)\b",
    re.IGNORECASE
)


_RANK_WORD_PATTERN = re.compile(
    r"\b(?:highest|maximum|max|largest|biggest|"
    r"lowest|minimum|min|smallest|least)\b",
    re.IGNORECASE
)


_LOWEST_WORD_PATTERN = re.compile(
    r"\b(?:lowest|minimum|min|smallest|least)\b",
    re.IGNORECASE
)


# =========================================================
# IDENTIFIER
# =========================================================

def _quote_identifier(name):
    """
    Safely quote SQLite identifier.

    Also removes accidental surrounding spaces.
    """

    name = str(name).strip()

    escaped = name.replace(
        '"',
        '""'
    )

    return f'"{escaped}"'


# =========================================================
# COLUMN MATCH HELPERS
# =========================================================

def _nearest_column(
    ref_pos,
    column_matches,
    allowed=None,
    exclude=None
):
    candidates = list(
        column_matches
    )

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
                c["position"] - ref_pos
            ),
            -c["score"]
        )
    )["column"]


def _column_after(
    ref_pos,
    column_matches,
    allowed=None,
    exclude=None
):
    """
    Find the best column appearing after ref_pos.
    """

    candidates = [
        c
        for c in column_matches
        if c["position"] >= ref_pos
    ]

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
            c["position"],
            -c["score"]
        )
    )["column"]


# =========================================================
# AGGREGATE COLUMN
# =========================================================

def _find_agg_column(
    question,
    column_matches,
    numeric_columns
):
    """
    Determine which numeric column should be aggregated.

    Examples:

        total salary
        sum salary
        average age
        max price

    Important:
    aggregate column may appear AFTER the aggregate keyword,
    therefore positional matching is used.
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

    question_lower = question.lower()

    # -----------------------------------------------------
    # Find aggregate keyword
    # -----------------------------------------------------

    aggregate_match = None

    for match in re.finditer(
        r"\b[a-zA-Z_]+\b",
        question_lower
    ):

        word = match.group().lower()

        if word in _AGGREGATE_KEYWORDS:

            aggregate_match = match
            break

    # -----------------------------------------------------
    # No aggregate keyword
    # -----------------------------------------------------

    if aggregate_match is None:

        return max(
            numeric_matches,
            key=lambda c: (
                c["score"],
                -c["position"]
            )
        )["column"]

    agg_pos = aggregate_match.end()

    # -----------------------------------------------------
    # Prefer numeric column AFTER aggregate keyword
    # -----------------------------------------------------

    after = [
        c
        for c in numeric_matches
        if c["position"] >= agg_pos
    ]

    if after:

        return min(
            after,
            key=lambda c: (
                c["position"],
                -c["score"]
            )
        )["column"]

    # -----------------------------------------------------
    # Fallback: nearest numeric column
    # -----------------------------------------------------

    return min(
        numeric_matches,
        key=lambda c: (
            abs(
                c["position"]
                - aggregate_match.start()
            ),
            -c["score"]
        )
    )["column"]


# =========================================================
# GROUP BY
# =========================================================

def _detect_group_by(
    question,
    column_matches,
    text_columns
):
    """
    Detect:

        by department
        group by department
        per department
        each department
    """

    question_lower = question.lower()

    # -----------------------------------------------------
    # Explicit "group by"
    # -----------------------------------------------------

    group_match = re.search(
        r"\bgroup\s+by\b",
        question_lower
    )

    if group_match:

        pos = group_match.end()

        candidates = [
            c
            for c in column_matches
            if c["position"] >= pos
        ]

        text_candidates = [
            c
            for c in candidates
            if c["column"] in text_columns
        ]

        candidates = (
            text_candidates
            or candidates
        )

        if candidates:

            return min(
                candidates,
                key=lambda c: (
                    c["position"],
                    -c["score"]
                )
            )["column"]

    # -----------------------------------------------------
    # "by department"
    # -----------------------------------------------------

    by_match = re.search(
        r"\bby\b",
        question_lower
    )

    if by_match:

        pos = by_match.end()

        candidates = [
            c
            for c in column_matches
            if c["position"] >= pos
        ]

        text_candidates = [
            c
            for c in candidates
            if c["column"] in text_columns
        ]

        candidates = (
            text_candidates
            or candidates
        )

        if candidates:

            return min(
                candidates,
                key=lambda c: (
                    c["position"],
                    -c["score"]
                )
            )["column"]

    # -----------------------------------------------------
    # "per department"
    # -----------------------------------------------------

    per_match = re.search(
        r"\b(?:per|each|every)\b",
        question_lower
    )

    if per_match:

        pos = per_match.end()

        candidates = [
            c
            for c in column_matches
            if c["position"] >= pos
            and c["column"] in text_columns
        ]

        if candidates:

            return min(
                candidates,
                key=lambda c: (
                    c["position"],
                    -c["score"]
                )
            )["column"]

    # -----------------------------------------------------
    # "which department has highest salary"
    # -----------------------------------------------------

    aggregate_match = re.search(
        r"\b(?:avg|average|mean|max|maximum|highest|"
        r"largest|biggest|min|minimum|lowest|smallest|"
        r"sum|total)\b",
        question_lower
    )

    if aggregate_match:

        leading = [
            c
            for c in column_matches
            if c["column"] in text_columns
            and c["position"]
            < aggregate_match.start()
        ]

        if leading:

            return max(
                leading,
                key=lambda c: (
                    c["position"],
                    c["score"]
                )
            )["column"]

    return None


# =========================================================
# ORDER / LIMIT
# =========================================================

def _detect_order_limit(
    question,
    column_matches,
    numeric_columns,
    group_by=None,
    aggregate_column=None
):

    def _numeric_column_near(
        pos
    ):

        candidates = [
            c
            for c in column_matches
            if c["column"] in numeric_columns
            and c["position"] >= pos
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
                -c["score"]
            )
        )["column"]

    # -----------------------------------------------------
    # TOP N
    # -----------------------------------------------------

    top_match = _TOP_PATTERN.search(
        question
    )

    if top_match:

        order_column = (
            aggregate_column
            if aggregate_column
            else _numeric_column_near(
                top_match.end()
            )
        )

        return (
            order_column,
            "DESC",
            int(
                top_match.group(1)
            )
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
            if aggregate_column
            else _numeric_column_near(
                bottom_match.end()
            )
        )

        return (
            order_column,
            "ASC",
            int(
                bottom_match.group(1)
            )
        )

    # -----------------------------------------------------
    # Highest / lowest with GROUP BY
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
            1
        )

    return (
        None,
        None,
        None
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
    used_num_ids
):

    filters = []

    if (
        not column_matches
        or not all_numbers
    ):
        return filters

    lower_question = question.lower()

    for column_match in column_matches:

        column = column_match[
            "column"
        ]

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
            if id(n) not in used_num_ids
            and n["position"] > column_pos
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

        # Don't turn "salary by department 5"
        # into salary = 5
        if re.search(
            r"\b(?:by|for|where|with|having)\b",
            between_text
        ):
            continue

        # Don't confuse ranking with filters
        if re.search(
            r"\b(?:top|bottom|lowest|highest|"
            r"least|most)\b",
            between_text
        ):
            continue

        words_between = re.findall(
            r"[a-zA-Z_]+",
            between_text
        )

        if len(words_between) > 4:
            continue

        filters.append({
            "column": column,
            "operator": "=",
            "value": number["value"]
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
    synonyms_path="knowledge/synonyms.json"
):

    filters = []
    filtered_columns = set()

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
    # COLUMN MATCHING
    # -----------------------------------------------------

    column_matches = find_columns_with_positions(
        question,
        schema,
        synonyms_path
    )

    # -----------------------------------------------------
    # CATEGORICAL VALUES
    # -----------------------------------------------------

    matched_column_names = {
        m["column"]
        for m in column_matches
    }

    categorical_matches = match_categorical_values(
        question,
        schema,
        allowed_columns=matched_column_names
    )

    for match in categorical_matches:

        col = match[
            "column"
        ]

        if col in filtered_columns:
            continue

        filters.append({
            "column": col,
            "operator": "=",
            "value": match["value"]
        })

        filtered_columns.add(
            col
        )

    # -----------------------------------------------------
    # OPERATORS
    # -----------------------------------------------------

    operators = detect_operators(
        question,
        operators_path
    )

    all_numbers = extract_numbers(
        question
    )

    used_num_ids = set()

    for op in operators:

        symbol = op["symbol"]
        op_pos = op["position"]

        # -------------------------------------------------
        # SKIP IN
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
                    exclude=filtered_columns
                )
            )

            if (
                col
                and col not in filtered_columns
            ):

                filters.append({
                    "column": col,
                    "operator": symbol
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
                    if n["position"] > op_pos
                    and id(n)
                    not in used_num_ids
                ],
                key=lambda n: n["position"]
            )

            if len(nums_after) >= 2:

                col = _nearest_column(
                    op_pos,
                    column_matches,
                    allowed=numeric_columns,
                    exclude=filtered_columns
                )

                if (
                    col
                    and col not in filtered_columns
                ):

                    filters.append({
                        "column": col,
                        "operator": symbol,
                        "value":
                            nums_after[0]["value"],
                        "value2":
                            nums_after[1]["value"]
                    })

                    filtered_columns.add(
                        col
                    )

                    used_num_ids.update({
                        id(nums_after[0]),
                        id(nums_after[1])
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
                    question.lower()
                )
                if m.start() > op_pos
            ]

            if words_after:

                val = words_after[
                    0
                ].group().strip(
                    ".,?!"
                )

                col = (
                    _nearest_column(
                        op_pos,
                        column_matches,
                        allowed=text_columns,
                        exclude=filtered_columns
                    )
                    or
                    _nearest_column(
                        op_pos,
                        column_matches,
                        exclude=filtered_columns
                    )
                )

                if (
                    col
                    and col not in filtered_columns
                ):

                    filters.append({
                        "column": col,
                        "operator": "LIKE",
                        "value":
                            f"%{val}%"
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
                    if n["position"] > op_pos
                    and id(n)
                    not in used_num_ids
                ],
                key=lambda n: n["position"]
            )

            if not nums_after:
                continue

            nearest_num = nums_after[0]

            col = _nearest_column(
                nearest_num["position"],
                column_matches,
                allowed=numeric_columns,
                exclude=filtered_columns
            )

            if (
                col
                and col not in filtered_columns
            ):

                filters.append({
                    "column": col,
                    "operator": symbol,
                    "value":
                        nearest_num["value"]
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
            used_num_ids
        )
    )

    filters.extend(
        implicit_filters
    )

    # -----------------------------------------------------
    # AGGREGATE COLUMN
    # -----------------------------------------------------

    agg_col = None

    if intent in _AGGREGATE_INTENTS:

        agg_col = _find_agg_column(
            question,
            column_matches,
            numeric_columns
        )

    # -----------------------------------------------------
    # GROUP BY
    # -----------------------------------------------------

    group_by_col = _detect_group_by(
        question,
        column_matches,
        text_columns
    )

    # -----------------------------------------------------
    # ORDER / LIMIT
    # -----------------------------------------------------

    (
        order_col,
        order_dir,
        limit
    ) = _detect_order_limit(
        question,
        column_matches,
        numeric_columns,
        group_by=group_by_col,
        aggregate_column=agg_col
    )

    # -----------------------------------------------------
    # RETURN
    # -----------------------------------------------------

    return {
        "intent": intent,
        "filters": filters,
        "agg_column": agg_col,
        "group_by": group_by_col,
        "order_by": order_col,
        "order_dir":
            order_dir or "DESC",
        "limit": limit,
        "order_by_aggregate": bool(
            group_by_col
            and agg_col
            and order_col == agg_col
        ),
    }


# =========================================================
# QUERY -> SQL
# =========================================================

def query_to_sql(
    query,
    table_name="data"
):

    intent = query[
        "intent"
    ]

    filters = query.get(
        "filters",
        []
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
        "DESC"
    )

    limit = query.get(
        "limit"
    )

    tbl = _quote_identifier(
        table_name
    )

    aggregate_alias = None

    # -----------------------------------------------------
    # AGGREGATE + TOP/BOTTOM WITHOUT GROUP
    # -----------------------------------------------------

    agg_overridden = (
        limit is not None
        and group_by is None
        and intent in _AGGREGATE_INTENTS
    )

    # -----------------------------------------------------
    # SELECT
    # -----------------------------------------------------

    if (
        intent == "SELECT"
        and group_by
    ):

        select_part = (
            "SELECT "
            f"{_quote_identifier(group_by)}, "
            "COUNT(*)"
        )

    elif (
        intent == "SELECT"
        or agg_overridden
    ):

        select_part = "SELECT *"

    # -----------------------------------------------------
    # COUNT
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # AGGREGATES
    # -----------------------------------------------------

    elif intent in _AGGREGATE_INTENTS:

        if not agg_column:

            raise ValueError(
                f"Could not determine which column "
                f"to apply '{intent}' to."
            )

        col = _quote_identifier(
            agg_column
        )

        # -------------------------------------------------
        # AGGREGATE + GROUP BY
        # -------------------------------------------------

        if group_by:

            alias_base = re.sub(
                r"[^a-zA-Z0-9]+",
                "_",
                str(agg_column).strip()
            ).strip("_").lower()

            aggregate_alias = (
                f"{intent.lower()}_"
                f"{alias_base}"
            )

            select_part = (
                "SELECT "
                f"{_quote_identifier(group_by)}, "
                f"{intent}({col}) AS "
                f"{_quote_identifier(aggregate_alias)}"
            )

        # -------------------------------------------------
        # SIMPLE AGGREGATE
        # -------------------------------------------------

        else:

            select_part = (
                "SELECT "
                f"{intent}({col})"
            )

    else:

        select_part = "SELECT *"

    # -----------------------------------------------------
    # FROM
    # -----------------------------------------------------

    sql = (
        f"{select_part} "
        f"FROM {tbl}"
    )

    # -----------------------------------------------------
    # WHERE
    # -----------------------------------------------------

    if filters:

        conditions = []

        for f in filters:

            col_q = _quote_identifier(
                f["column"]
            )

            operator = f[
                "operator"
            ]

            # ---------------------------------------------
            # NULL
            # ---------------------------------------------

            if operator in _NULL_OPS:

                conditions.append(
                    f"{col_q} {operator}"
                )

            # ---------------------------------------------
            # BETWEEN
            # ---------------------------------------------

            elif operator in _BETWEEN_OPS:

                v1 = f.get(
                    "value",
                    ""
                )

                v2 = f.get(
                    "value2",
                    ""
                )

                conditions.append(
                    f"{col_q} "
                    f"{operator} "
                    f"{v1} AND {v2}"
                )

            # ---------------------------------------------
            # NORMAL OPERATOR
            # ---------------------------------------------

            else:

                value = str(
                    f.get(
                        "value",
                        ""
                    )
                )

                numeric_value = (
                    value.replace(
                        ".",
                        "",
                        1
                    ).lstrip(
                        "-"
                    ).isdigit()
                )

                if numeric_value:

                    conditions.append(
                        f"{col_q} "
                        f"{operator} "
                        f"{value}"
                    )

                else:

                    safe = value.replace(
                        "'",
                        "''"
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

    # -----------------------------------------------------
    # GROUP BY
    # -----------------------------------------------------

    if group_by:

        sql += (
            " GROUP BY "
            + _quote_identifier(
                group_by
            )
        )

    # -----------------------------------------------------
    # ORDER BY
    # -----------------------------------------------------

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
            f"{order_expression} "
            f"{order_dir}"
        )

    # -----------------------------------------------------
    # LIMIT
    # -----------------------------------------------------

    if limit is not None:

        sql += (
            f" LIMIT {int(limit)}"
        )

    return sql