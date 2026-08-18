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
    "top": "MAX",

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


def _clean_column_name(name):
    """
    Clean column name while preserving database naming convention.

    IMPORTANT:
        Monthly_Income remains Monthly_Income
        ' Monthly_Income ' -> Monthly_Income
    """

    if name is None:
        return None

    return str(name).strip()


def _quote_identifier(name):
    """Safely quote SQLite identifier."""

    name = _clean_column_name(name)

    if not name:
        raise ValueError(
            "Cannot quote an empty column name."
        )

    return (
        '"'
        + name.replace('"', '""')
        + '"'
    )


def _clean_value(value):
    """Clean string values without changing numeric values."""

    if isinstance(value, str):
        return value.strip()

    return value


def _nearest_column(
    ref_pos,
    column_matches,
    allowed=None,
    exclude=None
):
    candidates = column_matches

    if allowed is not None:
        candidates = [
            c for c in candidates
            if c["column"] in allowed
        ]

    if exclude:
        candidates = [
            c for c in candidates
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


def _find_agg_column(
    question,
    column_matches,
    numeric_columns
):
    if not numeric_columns:
        return None

    agg_keyword_pos = None

    for m in re.finditer(
        r"\S+",
        question.lower()
    ):

        if m.group() in _AGGREGATE_KEYWORDS:

            agg_keyword_pos = m.start()
            break

    numeric_matches = [
        c for c in column_matches
        if c["column"] in numeric_columns
    ]

    if not numeric_matches:
        return None

    if agg_keyword_pos is None:

        return max(
            numeric_matches,
            key=lambda c: c["score"]
        )["column"]

    return min(
        numeric_matches,
        key=lambda c: (
            abs(
                c["position"]
                - agg_keyword_pos
            ),
            -c["score"]
        )
    )["column"]


def _detect_group_by(
    question,
    column_matches
):
    m = re.search(
        r"\bby\b",
        question,
        re.IGNORECASE
    )

    if not m:
        return None

    pos = m.end()

    candidates = [
        c for c in column_matches
        if c["position"] >= pos
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


def _detect_order_limit(
    question,
    column_matches,
    numeric_columns
):

    def _column_near(pos):

        candidates = [
            c for c in column_matches
            if (
                c["column"] in numeric_columns
                and c["position"] >= pos
            )
        ]

        if not candidates:

            candidates = [
                c for c in column_matches
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

    top_m = _TOP_PATTERN.search(question)

    if top_m:

        return (
            _column_near(top_m.end()),
            "DESC",
            int(top_m.group(1))
        )

    bot_m = _BOTTOM_PATTERN.search(question)

    if bot_m:

        return (
            _column_near(bot_m.end()),
            "ASC",
            int(bot_m.group(1))
        )

    return None, None, None


def build_query(
    question,
    schema,
    intent,
    operators_path="knowledge/operators.json",
    synonyms_path="knowledge/synonyms.json"
):

    filters = []
    filtered_columns = set()

    # ---------------------------------------------------------
    # Schema column sets
    # ---------------------------------------------------------

    numeric_columns = {
        _clean_column_name(c)
        for c in get_numeric_columns(schema)
    }

    text_columns = {
        _clean_column_name(c)
        for c in get_text_columns(schema)
    }

    # ---------------------------------------------------------
    # Find columns
    # ---------------------------------------------------------

    column_matches = find_columns_with_positions(
        question,
        schema,
        synonyms_path
    )

    # Normalize returned column names
    for match in column_matches:

        match["column"] = _clean_column_name(
            match["column"]
        )

    matched_column_names = {
        m["column"]
        for m in column_matches
    }

    # ---------------------------------------------------------
    # Categorical filters
    # ---------------------------------------------------------

    categorical_matches = match_categorical_values(
        question,
        schema,
        allowed_columns=matched_column_names
    )

    for match in categorical_matches:

        col = _clean_column_name(
            match["column"]
        )

        value = _clean_value(
            match["value"]
        )

        if (
            col
            and col not in filtered_columns
        ):

            filters.append({
                "column": col,
                "operator": "=",
                "value": value,
            })

            filtered_columns.add(col)

    # ---------------------------------------------------------
    # Operators
    # ---------------------------------------------------------

    operators = detect_operators(
        question,
        operators_path
    )

    all_numbers = extract_numbers(
        question
    )

    used_num_ids = set()

    # ---------------------------------------------------------
    # Process operators
    # ---------------------------------------------------------

    for op in operators:

        symbol = op["symbol"]
        op_pos = op["position"]

        # Ignore IN / NOT IN for now
        if symbol in _SKIP_OPS:
            continue

        # -----------------------------------------------------
        # NULL
        # -----------------------------------------------------

        if symbol in _NULL_OPS:

            col = (
                _nearest_column(
                    op_pos,
                    column_matches,
                    allowed=numeric_columns,
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
                    "column": _clean_column_name(col),
                    "operator": symbol,
                })

                filtered_columns.add(col)

            continue

        # -----------------------------------------------------
        # BETWEEN
        # -----------------------------------------------------

        if symbol in _BETWEEN_OPS:

            nums_after = sorted(
                [
                    n for n in all_numbers
                    if (
                        n["position"] > op_pos
                        and id(n)
                        not in used_num_ids
                    )
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
                        "column": _clean_column_name(col),
                        "operator": symbol,
                        "value": nums_after[0]["value"],
                        "value2": nums_after[1]["value"],
                    })

                    filtered_columns.add(col)

                    used_num_ids.update({
                        id(nums_after[0]),
                        id(nums_after[1])
                    })

            continue

        # -----------------------------------------------------
        # LIKE
        # -----------------------------------------------------

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

                val = words_after[0].group()

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
                        "column": _clean_column_name(col),
                        "operator": "LIKE",
                        "value": f"%{val}%",
                    })

                    filtered_columns.add(col)

            continue

        # -----------------------------------------------------
        # SIMPLE OPERATORS
        # -----------------------------------------------------

        if symbol in _SIMPLE_OPS:

            nums_after = sorted(
                [
                    n for n in all_numbers
                    if (
                        n["position"] > op_pos
                        and id(n)
                        not in used_num_ids
                    )
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
                    "column": _clean_column_name(col),
                    "operator": symbol,
                    "value": nearest_num["value"],
                })

                filtered_columns.add(col)

                used_num_ids.add(
                    id(nearest_num)
                )

    # ---------------------------------------------------------
    # GROUP BY
    # ---------------------------------------------------------

    group_by_col = _detect_group_by(
        question,
        column_matches
    )

    if group_by_col:
        group_by_col = _clean_column_name(
            group_by_col
        )

    # ---------------------------------------------------------
    # ORDER BY + LIMIT
    # ---------------------------------------------------------

    (
        order_col,
        order_dir,
        limit
    ) = _detect_order_limit(
        question,
        column_matches,
        numeric_columns
    )

    if order_col:
        order_col = _clean_column_name(
            order_col
        )

    # ---------------------------------------------------------
    # Aggregate column
    # ---------------------------------------------------------

    agg_col = None

    if intent in _AGGREGATE_INTENTS:

        agg_col = _find_agg_column(
            question,
            column_matches,
            numeric_columns
        )

        if agg_col:
            agg_col = _clean_column_name(
                agg_col
            )

    # ---------------------------------------------------------
    # Final result
    # ---------------------------------------------------------

    return {
        "intent": intent,
        "filters": filters,
        "agg_column": agg_col,
        "group_by": group_by_col,
        "order_by": order_col,
        "order_dir": order_dir or "DESC",
        "limit": limit,
    }


def query_to_sql(
    query,
    table_name="data"
):

    intent = query["intent"]

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

    # ---------------------------------------------------------
    # Normalize everything before SQL generation
    # ---------------------------------------------------------

    for f in filters:

        if "column" in f:
            f["column"] = _clean_column_name(
                f["column"]
            )

        if "value" in f:
            f["value"] = _clean_value(
                f["value"]
            )

        if "value2" in f:
            f["value2"] = _clean_value(
                f["value2"]
            )

    if agg_column:
        agg_column = _clean_column_name(
            agg_column
        )

    if group_by:
        group_by = _clean_column_name(
            group_by
        )

    if order_by:
        order_by = _clean_column_name(
            order_by
        )

    # ---------------------------------------------------------
    # Aggregate + LIMIT special case
    # ---------------------------------------------------------

    agg_overridden = (
        limit is not None
        and group_by is None
        and intent in _AGGREGATE_INTENTS
    )

    # ---------------------------------------------------------
    # SELECT part
    # ---------------------------------------------------------

    if intent == "SELECT" or agg_overridden:

        select_part = "SELECT *"

    elif intent == "COUNT":

        if group_by:

            select_part = (
                f"SELECT "
                f"{_quote_identifier(group_by)}, "
                f"COUNT(*)"
            )

        else:

            select_part = "SELECT COUNT(*)"

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

            select_part = (
                f"SELECT "
                f"{_quote_identifier(group_by)}, "
                f"{intent}({col})"
            )

        else:

            select_part = (
                f"SELECT "
                f"{intent}({col})"
            )

    else:

        select_part = "SELECT *"

    # ---------------------------------------------------------
    # FROM
    # ---------------------------------------------------------

    sql = (
        f"{select_part} "
        f"FROM {tbl}"
    )

    # ---------------------------------------------------------
    # WHERE
    # ---------------------------------------------------------

    if filters:

        conditions = []

        for f in filters:

            column = _clean_column_name(
                f["column"]
            )

            col_q = _quote_identifier(
                column
            )

            operator = f["operator"]

            # ---------------------------------------------
            # NULL operators
            # ---------------------------------------------

            if operator in _NULL_OPS:

                conditions.append(
                    f"{col_q} {operator}"
                )

            # ---------------------------------------------
            # BETWEEN
            # ---------------------------------------------

            elif operator in _BETWEEN_OPS:

                v1 = _clean_value(
                    f.get("value", "")
                )

                v2 = _clean_value(
                    f.get("value2", "")
                )

                conditions.append(
                    f"{col_q} "
                    f"{operator} "
                    f"{v1} AND {v2}"
                )

            # ---------------------------------------------
            # Normal operators
            # ---------------------------------------------

            else:

                value = _clean_value(
                    f.get("value", "")
                )

                value_str = str(
                    value
                ).strip()

                # Numeric
                if (
                    value_str
                    .replace(".", "", 1)
                    .lstrip("-")
                    .isdigit()
                ):

                    conditions.append(
                        f"{col_q} "
                        f"{operator} "
                        f"{value_str}"
                    )

                # Text
                else:

                    safe = (
                        value_str
                        .replace(
                            "'",
                            "''"
                        )
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

    # ---------------------------------------------------------
    # GROUP BY
    # ---------------------------------------------------------

    if group_by:

        sql += (
            " GROUP BY "
            f"{_quote_identifier(group_by)}"
        )

    # ---------------------------------------------------------
    # ORDER BY
    # ---------------------------------------------------------

    if order_by:

        sql += (
            " ORDER BY "
            f"{_quote_identifier(order_by)} "
            f"{order_dir}"
        )

    # ---------------------------------------------------------
    # LIMIT
    # ---------------------------------------------------------

    if limit:

        sql += (
            f" LIMIT {limit}"
        )

    return sql