import re

from operator_detector import detect_operators
from attribute_matcher import (
    find_columns_with_positions,
    resolve_schema_column
)
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
    if name is None:
        return None

    return str(name).strip()


def _quote_identifier(name):
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
    if isinstance(value, str):
        return value.strip()

    return value


def _canonical_column(name, schema):
    """
    ALWAYS convert a column reference to the
    exact schema column name.
    """

    if not name:
        return None

    resolved = resolve_schema_column(
        name,
        schema
    )

    if resolved:
        return resolved

    return None


def _canonical_columns(columns, schema):
    """
    Convert a list/set of column names into
    exact schema names.
    """

    result = set()

    for column in columns:

        resolved = _canonical_column(
            column,
            schema
        )

        if resolved:
            result.add(resolved)

    return result


def _nearest_column(
    ref_pos,
    column_matches,
    allowed=None,
    exclude=None
):
    candidates = column_matches

    if allowed is not None:

        candidates = [
            column
            for column in candidates
            if column["column"] in allowed
        ]

    if exclude:

        candidates = [
            column
            for column in candidates
            if column["column"] not in exclude
        ]

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda column: (
            abs(
                column["position"]
                - ref_pos
            ),
            -column["score"]
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

    for match in re.finditer(
        r"\S+",
        question.lower()
    ):

        if match.group() in _AGGREGATE_KEYWORDS:

            agg_keyword_pos = match.start()
            break

    numeric_matches = [
        column
        for column in column_matches
        if column["column"] in numeric_columns
    ]

    if not numeric_matches:
        return None

    if agg_keyword_pos is None:

        return max(
            numeric_matches,
            key=lambda column: column["score"]
        )["column"]

    return min(
        numeric_matches,
        key=lambda column: (
            abs(
                column["position"]
                - agg_keyword_pos
            ),
            -column["score"]
        )
    )["column"]


def _detect_group_by(
    question,
    column_matches
):
    match = re.search(
        r"\bby\b",
        question,
        re.IGNORECASE
    )

    if not match:
        return None

    pos = match.end()

    candidates = [
        column
        for column in column_matches
        if column["position"] >= pos
    ]

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda column: (
            column["position"],
            -column["score"]
        )
    )["column"]


def _detect_order_limit(
    question,
    column_matches,
    numeric_columns
):

    def _column_near(pos):

        candidates = [
            column
            for column in column_matches
            if (
                column["column"] in numeric_columns
                and column["position"] >= pos
            )
        ]

        if not candidates:

            candidates = [
                column
                for column in column_matches
                if column["column"] in numeric_columns
            ]

        if not candidates:
            return None

        return min(
            candidates,
            key=lambda column: (
                abs(
                    column["position"] - pos
                ),
                -column["score"]
            )
        )["column"]

    top_match = _TOP_PATTERN.search(
        question
    )

    if top_match:

        return (
            _column_near(
                top_match.end()
            ),
            "DESC",
            int(top_match.group(1))
        )

    bottom_match = _BOTTOM_PATTERN.search(
        question
    )

    if bottom_match:

        return (
            _column_near(
                bottom_match.end()
            ),
            "ASC",
            int(bottom_match.group(1))
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

    # =========================================================
    # SCHEMA COLUMN SETS
    # =========================================================

    numeric_columns = _canonical_columns(
        get_numeric_columns(schema),
        schema
    )

    text_columns = _canonical_columns(
        get_text_columns(schema),
        schema
    )

    # =========================================================
    # FIND COLUMNS
    # =========================================================

    column_matches = find_columns_with_positions(
        question,
        schema,
        synonyms_path
    )

    # ---------------------------------------------------------
    # Force exact schema names
    # ---------------------------------------------------------

    clean_matches = []

    for match in column_matches:

        resolved = _canonical_column(
            match.get("column"),
            schema
        )

        if not resolved:
            continue

        clean_matches.append({
            "column": resolved,
            "position": match.get(
                "position",
                0
            ),
            "score": match.get(
                "score",
                0
            ),
        })

    column_matches = clean_matches

    matched_column_names = {
        match["column"]
        for match in column_matches
    }

    # =========================================================
    # CATEGORICAL FILTERS
    # =========================================================

    categorical_matches = match_categorical_values(
        question,
        schema,
        allowed_columns=matched_column_names
    )

    for match in categorical_matches:

        # IMPORTANT:
        # value_matcher may return:
        # Monthly Income
        # instead of:
        # Monthly_Income
        #
        # Resolve it here.

        col = _canonical_column(
            match.get("column"),
            schema
        )

        if not col:
            continue

        value = _clean_value(
            match.get("value")
        )

        if col not in filtered_columns:

            filters.append({
                "column": col,
                "operator": "=",
                "value": value,
            })

            filtered_columns.add(col)

    # =========================================================
    # OPERATORS
    # =========================================================

    operators = detect_operators(
        question,
        operators_path
    )

    all_numbers = extract_numbers(
        question
    )

    used_num_ids = set()

    # =========================================================
    # PROCESS OPERATORS
    # =========================================================

    for op in operators:

        symbol = op["symbol"]
        op_pos = op["position"]

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

            col = _canonical_column(
                col,
                schema
            )

            if col and col not in filtered_columns:

                filters.append({
                    "column": col,
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
                    number
                    for number in all_numbers
                    if (
                        number["position"] > op_pos
                        and id(number)
                        not in used_num_ids
                    )
                ],
                key=lambda number: number["position"]
            )

            if len(nums_after) >= 2:

                col = _nearest_column(
                    op_pos,
                    column_matches,
                    allowed=numeric_columns,
                    exclude=filtered_columns
                )

                col = _canonical_column(
                    col,
                    schema
                )

                if col and col not in filtered_columns:

                    filters.append({
                        "column": col,
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
                match
                for match in re.finditer(
                    r"\S+",
                    question.lower()
                )
                if match.start() > op_pos
            ]

            if words_after:

                value = words_after[0].group()

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

                col = _canonical_column(
                    col,
                    schema
                )

                if col and col not in filtered_columns:

                    filters.append({
                        "column": col,
                        "operator": "LIKE",
                        "value": f"%{value}%",
                    })

                    filtered_columns.add(col)

            continue

        # -----------------------------------------------------
        # SIMPLE OPERATORS
        # -----------------------------------------------------

        if symbol in _SIMPLE_OPS:

            nums_after = sorted(
                [
                    number
                    for number in all_numbers
                    if (
                        number["position"] > op_pos
                        and id(number)
                        not in used_num_ids
                    )
                ],
                key=lambda number: number["position"]
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

            col = _canonical_column(
                col,
                schema
            )

            if col and col not in filtered_columns:

                filters.append({
                    "column": col,
                    "operator": symbol,
                    "value": nearest_num["value"],
                })

                filtered_columns.add(col)

                used_num_ids.add(
                    id(nearest_num)
                )

    # =========================================================
    # GROUP BY
    # =========================================================

    group_by_col = _detect_group_by(
        question,
        column_matches
    )

    group_by_col = _canonical_column(
        group_by_col,
        schema
    )

    # =========================================================
    # ORDER BY + LIMIT
    # =========================================================

    (
        order_col,
        order_dir,
        limit
    ) = _detect_order_limit(
        question,
        column_matches,
        numeric_columns
    )

    order_col = _canonical_column(
        order_col,
        schema
    )

    # =========================================================
    # AGGREGATE COLUMN
    # =========================================================

    agg_col = None

    if intent in _AGGREGATE_INTENTS:

        agg_col = _find_agg_column(
            question,
            column_matches,
            numeric_columns
        )

        agg_col = _canonical_column(
            agg_col,
            schema
        )

    # =========================================================
    # FINAL SAFETY CHECK
    # =========================================================

    clean_filters = []

    for filter_item in filters:

        col = _canonical_column(
            filter_item.get("column"),
            schema
        )

        if not col:
            continue

        new_filter = dict(filter_item)
        new_filter["column"] = col

        clean_filters.append(
            new_filter
        )

    filters = clean_filters

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
    table_name="data",
    schema=None
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

    # =========================================================
    # CANONICALIZE ALL COLUMNS
    # =========================================================

    if schema is not None:

        if agg_column:
            agg_column = _canonical_column(
                agg_column,
                schema
            )

        if group_by:
            group_by = _canonical_column(
                group_by,
                schema
            )

        if order_by:
            order_by = _canonical_column(
                order_by,
                schema
            )

    else:

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

    # =========================================================
    # FILTERS
    # =========================================================

    clean_filters = []

    for filter_item in filters:

        column = filter_item.get(
            "column"
        )

        if schema is not None:

            column = _canonical_column(
                column,
                schema
            )

        else:

            column = _clean_column_name(
                column
            )

        if not column:
            continue

        new_filter = dict(
            filter_item
        )

        new_filter["column"] = column

        if "value" in new_filter:
            new_filter["value"] = _clean_value(
                new_filter["value"]
            )

        if "value2" in new_filter:
            new_filter["value2"] = _clean_value(
                new_filter["value2"]
            )

        clean_filters.append(
            new_filter
        )

    filters = clean_filters

    # =========================================================
    # AGGREGATE + LIMIT
    # =========================================================

    agg_overridden = (
        limit is not None
        and group_by is None
        and intent in _AGGREGATE_INTENTS
    )

    # =========================================================
    # SELECT
    # =========================================================

    if intent == "SELECT" or agg_overridden:

        select_part = "SELECT *"

    elif intent == "COUNT":

        if group_by:

            select_part = (
                "SELECT "
                f"{_quote_identifier(group_by)}, "
                "COUNT(*)"
            )

        else:

            select_part = "SELECT COUNT(*)"

    elif intent in _AGGREGATE_INTENTS:

        if not agg_column:

            raise ValueError(
                f"Could not determine which column "
                f"to apply '{intent}' to. "
                "Try rephrasing your question "
                "with the column name."
            )

        col = _quote_identifier(
            agg_column
        )

        if group_by:

            select_part = (
                "SELECT "
                f"{_quote_identifier(group_by)}, "
                f"{intent}({col})"
            )

        else:

            select_part = (
                "SELECT "
                f"{intent}({col})"
            )

    else:

        select_part = "SELECT *"

    # =========================================================
    # FROM
    # =========================================================

    sql = (
        f"{select_part} "
        f"FROM {tbl}"
    )

    # =========================================================
    # WHERE
    # =========================================================

    if filters:

        conditions = []

        for filter_item in filters:

            column = filter_item["column"]

            col_q = _quote_identifier(
                column
            )

            operator = filter_item[
                "operator"
            ]

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

                value1 = _clean_value(
                    filter_item.get(
                        "value",
                        ""
                    )
                )

                value2 = _clean_value(
                    filter_item.get(
                        "value2",
                        ""
                    )
                )

                conditions.append(
                    f"{col_q} "
                    f"{operator} "
                    f"{value1} AND {value2}"
                )

            # -------------------------------------------------
            # Normal operators
            # -------------------------------------------------

            else:

                value = _clean_value(
                    filter_item.get(
                        "value",
                        ""
                    )
                )

                value_str = str(
                    value
                ).strip()

                # Numeric
                try:
                    float(value_str)
                    is_numeric = True
                except (ValueError, TypeError):
                    is_numeric = False

                if is_numeric:

                    conditions.append(
                        f"{col_q} "
                        f"{operator} "
                        f"{value_str}"
                    )

                # Text
                else:

                    safe = value_str.replace(
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

    # =========================================================
    # GROUP BY
    # =========================================================

    if group_by:

        sql += (
            " GROUP BY "
            f"{_quote_identifier(group_by)}"
        )

    # =========================================================
    # ORDER BY
    # =========================================================

    if order_by:

        direction = (
            "ASC"
            if str(order_dir).upper()
            == "ASC"
            else "DESC"
        )

        sql += (
            " ORDER BY "
            f"{_quote_identifier(order_by)} "
            f"{direction}"
        )

    # =========================================================
    # LIMIT
    # =========================================================

    if limit is not None:

        try:
            limit_int = int(limit)

            if limit_int > 0:

                sql += (
                    f" LIMIT {limit_int}"
                )

        except (ValueError, TypeError):
            pass

    return sql