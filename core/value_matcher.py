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
    r"\b(?:highest|maximum|max|largest|biggest|lowest|minimum|min|smallest|least)\b",
    re.IGNORECASE,
)


_LOWEST_WORD_PATTERN = re.compile(
    r"\b(?:lowest|minimum|min|smallest|least)\b",
    re.IGNORECASE,
)


def _quote_identifier(name):
    escaped = str(name).replace(
        '"',
        '""'
    )

    return f'"{escaped}"'


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
            -c["score"],
        ),
    )["column"]


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
        question.lower()
    ):

        word = m.group().strip(
            ".,?!"
        )

        if word in _AGGREGATE_KEYWORDS:
            agg_keyword_pos = m.start()
            break

    numeric_matches = [
        c
        for c in column_matches
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
            -c["score"],
        ),
    )["column"]


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

        aggregate_match = re.search(
            r"\b(?:avg|average|mean|max|maximum|highest|largest|biggest|min|minimum|lowest|smallest|sum|total)\b",
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
                if c["column"]
                in numeric_columns
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
                -c["score"],
            ),
        )["column"]

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
                and n["position"]
                > column_pos
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

        if re.search(
            r"\b(?:by|for|where|with|having)\b",
            between_text,
        ):
            continue

        if re.search(
            r"\b(?:top|bottom|lowest|highest|least|most)\b",
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


def build_query(
    question,
    schema,
    intent,
    operators_path="knowledge/operators.json",
    synonyms_path="knowledge/synonyms.json",
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

    # --------------------------------------------------
    # ATTRIBUTE MATCHING
    # --------------------------------------------------

    column_matches = find_columns_with_positions(
        question,
        schema,
        synonyms_path,
    )

    matched_column_names = {
        m["column"]
        for m in column_matches
    }

    # --------------------------------------------------
    # CATEGORICAL MATCHING
    #
    # This is the important part for:
    #
    # "how many female are there"
    #
    # female -> gender
    # Female -> actual schema value
    # --------------------------------------------------

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

        filters.append({
            "column": col,
            "operator": "=",
            "value": match["value"],
        })

        filtered_columns.add(
            col
        )

    # --------------------------------------------------
    # OPERATORS
    # --------------------------------------------------

    operators = detect_operators(
        question,
        operators_path,
    )

    all_numbers = extract_numbers(
        question
    )

    used_num_ids = set()

    for op in operators:

        symbol = op["symbol"]
        op_pos = op["position"]

        if symbol in _SKIP_OPS:
            continue

        # ----------------------------------------------
        # NULL
        # ----------------------------------------------

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

                filters.append({
                    "column": col,
                    "operator": symbol,
                })

                filtered_columns.add(
                    col
                )

            continue

        # ----------------------------------------------
        # BETWEEN
        # ----------------------------------------------

        if symbol in _BETWEEN_OPS:

            nums_after = sorted(
                [
                    n
                    for n in all_numbers
                    if (
                        n["position"]
                        > op_pos
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

        # ----------------------------------------------
        # LIKE
        # ----------------------------------------------

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

        # ----------------------------------------------
        # SIMPLE OPERATORS
        # ----------------------------------------------

        if symbol in _SIMPLE_OPS:

            nums_after = sorted(
                [
                    n
                    for n in all_numbers
                    if (
                        n["position"]
                        > op_pos
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

    # --------------------------------------------------
    # IMPLICIT NUMERIC FILTERS
    # --------------------------------------------------

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

    # --------------------------------------------------
    # AGGREGATE
    # --------------------------------------------------

    agg_col = None

    if intent in _AGGREGATE_INTENTS:

        agg_col = _find_agg_column(
            question,
            column_matches,
            numeric_columns,
        )

    # --------------------------------------------------
    # GROUP BY
    # --------------------------------------------------

    group_by_col = _detect_group_by(
        question,
        column_matches,
        text_columns,
    )

    # --------------------------------------------------
    # ORDER / LIMIT
    # --------------------------------------------------

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

    return {
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
    }


def _is_numeric_value(value):
    value = str(value).strip()

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
    Convert a Python value into a safe SQL literal.
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


def query_to_sql(
    query,
    table_name="data",
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

    aggregate_alias = None

    # --------------------------------------------------
    # TOP/BOTTOM aggregate override
    # --------------------------------------------------

    agg_overridden = (
        limit is not None
        and group_by is None
        and intent in _AGGREGATE_INTENTS
    )

    # --------------------------------------------------
    # SELECT
    # --------------------------------------------------

    if (
        intent == "SELECT"
        and group_by
    ):

        select_part = (
            "SELECT "
            + _quote_identifier(
                group_by
            )
            + ", COUNT(*)"
        )

    elif (
        intent == "SELECT"
        or agg_overridden
    ):

        select_part = "SELECT *"

    # --------------------------------------------------
    # COUNT
    # --------------------------------------------------

    elif intent == "COUNT":

        if group_by:

            select_part = (
                "SELECT "
                + _quote_identifier(
                    group_by
                )
                + ", COUNT(*)"
            )

        else:

            select_part = (
                "SELECT COUNT(*)"
            )

    # --------------------------------------------------
    # AVG / MAX / MIN / SUM
    # --------------------------------------------------

    elif intent in _AGGREGATE_INTENTS:

        if not agg_column:

            raise ValueError(
                "Could not determine which "
                f"column to apply '{intent}' to."
            )

        col = _quote_identifier(
            agg_column
        )

        if group_by:

            alias_base = re.sub(
                r"[^a-zA-Z0-9]+",
                "_",
                str(agg_column),
            ).strip(
                "_"
            ).lower()

            aggregate_alias = (
                f"{intent.lower()}_"
                f"{alias_base}"
            )

            select_part = (
                "SELECT "
                + _quote_identifier(
                    group_by
                )
                + ", "
                + f"{intent}({col})"
                + " AS "
                + _quote_identifier(
                    aggregate_alias
                )
            )

        else:

            select_part = (
                f"SELECT {intent}({col})"
            )

    else:

        select_part = "SELECT *"

    # --------------------------------------------------
    # FROM
    # --------------------------------------------------

    sql = (
        f"{select_part} "
        f"FROM {tbl}"
    )

    # --------------------------------------------------
    # WHERE
    # --------------------------------------------------

    if filters:

        conditions = []

        for f in filters:

            column = f.get(
                "column"
            )

            operator = str(
                f.get(
                    "operator",
                    "="
                )
            ).upper()

            if not column:
                continue

            col_q = _quote_identifier(
                column
            )

            # ------------------------------------------
            # NULL
            # ------------------------------------------

            if operator in _NULL_OPS:

                conditions.append(
                    f"{col_q} {operator}"
                )

            # ------------------------------------------
            # BETWEEN
            # ------------------------------------------

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
                    f"{col_q} {operator} "
                    f"{v1} AND {v2}"
                )

            # ------------------------------------------
            # NORMAL
            # ------------------------------------------

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

    # --------------------------------------------------
    # GROUP BY
    # --------------------------------------------------

    if group_by:

        sql += (
            " GROUP BY "
            + _quote_identifier(
                group_by
            )
        )

    # --------------------------------------------------
    # ORDER BY
    # --------------------------------------------------

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
            f" ORDER BY "
            f"{order_expression} "
            f"{order_dir}"
        )

    # --------------------------------------------------
    # LIMIT
    # --------------------------------------------------

    if limit:

        sql += (
            f" LIMIT {int(limit)}"
        )

    return sql