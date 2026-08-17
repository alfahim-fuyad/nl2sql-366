# core/sql_generator.py
import re
import calendar

from operator_detector import detect_operators
from attribute_matcher import find_columns_with_positions
from value_matcher import extract_numbers, match_categorical_values, _MONTH_MAP
from schema_reader import get_numeric_columns, get_text_columns


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

# Map intent to the keywords that should be used to find the aggregate column
_INTENT_KEYWORDS = {
    "AVG": ["avg", "average", "mean"],
    "MAX": ["max", "maximum", "highest", "largest", "biggest", "top"],
    "MIN": ["min", "minimum", "lowest", "smallest", "least"],
    "SUM": ["sum", "total", "aggregate"],
}

_SIMPLE_OPS = {">", "<", ">=", "<=", "=", "!=", "<>"}
_BETWEEN_OPS = {"BETWEEN", "NOT BETWEEN"}
_NULL_OPS = {"IS NULL", "IS NOT NULL"}
_LIKE_OPS = {"LIKE"}
_SKIP_OPS = {"IN", "NOT IN"}

_TOP_PATTERN = re.compile(
    r"\btop\s+(\d+)\b",
    re.IGNORECASE
)

_BOTTOM_PATTERN = re.compile(
    r"\b(?:bottom|lowest|least|worst|minimum)\s+(\d+)\b",
    re.IGNORECASE
)

_RANK_WORD_PATTERN = re.compile(
    r"\b(?:highest|maximum|max|largest|biggest|lowest|minimum|min|smallest|least)\b",
    re.IGNORECASE
)

_LOWEST_WORD_PATTERN = re.compile(
    r"\b(?:lowest|minimum|min|smallest|least)\b",
    re.IGNORECASE
)

# Month-related columns (case-insensitive check)
_MONTH_COLUMNS = {"month", "months"}
_YEAR_COLUMNS = {"year", "years"}


def _quote_identifier(name):
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def _nearest_column(ref_pos, column_matches, allowed=None, exclude=None):
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
            abs(c["position"] - ref_pos),
            -c["score"]
        )
    )["column"]


def _find_agg_column(question, column_matches, numeric_columns, intent=None):
    """
    Find the column to apply an aggregate function to.
    When intent is known, use intent-specific keywords to find the right column.
    E.g., for AVG intent with "highest average rainfall",
    we should find "average" (not "highest") and match to the nearest numeric column.
    """
    if not numeric_columns:
        return None

    agg_keyword_pos = None

    # Determine which keywords to look for based on intent
    if intent and intent in _INTENT_KEYWORDS:
        target_keywords = _INTENT_KEYWORDS[intent]
    else:
        target_keywords = list(_AGGREGATE_KEYWORDS.keys())

    for m in re.finditer(r"\S+", question.lower()):
        word = m.group().strip(".,?!")
        if word in target_keywords:
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
            abs(c["position"] - agg_keyword_pos),
            -c["score"]
        )
    )["column"]


def _detect_group_by(question, column_matches, text_columns, numeric_columns=None):
    """
    Detect GROUP BY column from the question.
    Enhanced to also detect grouping on numeric dimension columns (Year, Month).
    """
    if numeric_columns is None:
        numeric_columns = set()

    m = re.search(
        r"\bby\b",
        question,
        re.IGNORECASE
    )

    if not m:
        aggregate_match = re.search(
            r"\b(?:avg|average|mean|max|maximum|highest|largest|biggest|"
            r"min|minimum|lowest|smallest|sum|total)\b",
            question,
            re.IGNORECASE,
        )

        if not aggregate_match:
            return None

        # Check for "which/what" pattern - indicates GROUP BY
        has_which = re.search(
            r"\b(?:which|what)\b",
            question,
            re.IGNORECASE
        )

        # Leading candidates before aggregate keyword
        # Include both text columns AND numeric dimension columns (Year, Month)
        dimension_cols = text_columns | {
            c for c in numeric_columns
            if c.lower() in _MONTH_COLUMNS | _YEAR_COLUMNS
        }

        leading_candidates = [
            c for c in column_matches
            if c["column"] in dimension_cols
            and c["position"] < aggregate_match.start()
        ]

        if has_which and leading_candidates:
            return max(
                leading_candidates,
                key=lambda c: (
                    c["position"],
                    c["score"]
                ),
            )["column"]

        # "each/every/per" pattern
        each_match = re.search(
            r"\b(?:each|every|per)\b",
            question,
            re.IGNORECASE,
        )

        if each_match:
            candidates = [
                c for c in column_matches
                if c["column"] in (dimension_cols if dimension_cols else text_columns)
                and c["position"] >= each_match.end()
            ]

            if candidates:
                return min(
                    candidates,
                    key=lambda c: (
                        c["position"],
                        -c["score"]
                    ),
                )["column"]

        return None

    pos = m.end()

    candidates = [
        c for c in column_matches
        if c["position"] >= pos
    ]

    if not candidates:
        return None

    text_candidates = [
        c for c in candidates
        if c["column"] in text_columns
    ]

    candidates = text_candidates or candidates

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
    numeric_columns,
    group_by=None,
    aggregate_column=None
):
    def _column_near(pos):
        candidates = [
            c for c in column_matches
            if c["column"] in numeric_columns
            and c["position"] >= pos
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
                abs(c["position"] - pos),
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
        order_column = (
            aggregate_column
            if group_by and aggregate_column
            else _column_near(bot_m.end())
        )

        return (
            order_column,
            "ASC",
            int(bot_m.group(1))
        )

    if (
        group_by
        and aggregate_column
        and _RANK_WORD_PATTERN.search(question)
    ):
        direction = (
            "ASC"
            if _LOWEST_WORD_PATTERN.search(question)
            else "DESC"
        )

        return (
            aggregate_column,
            direction,
            1
        )

    return None, None, None


def _extract_month_filter(question, schema, column_matches, filtered_columns, all_numbers, used_num_ids):
    """
    Special handling for month names in queries.
    If a month name appears (converted to number by extract_numbers),
    and there's a Month/year column in the schema, create a filter.
    """
    filters = []
    lower_question = question.lower()

    # Check if any month name appears in the question
    month_found = False
    month_num = None
    month_position = None
    for month_name, num_str in _MONTH_MAP.items():
        if len(month_name) > 2:  # Skip abbreviated months for position tracking
            pattern = r"\b" + re.escape(month_name) + r"\b"
            m = re.search(pattern, lower_question)
            if m:
                month_found = True
                month_num = num_str
                month_position = m.start()
                break

    if not month_found:
        return filters

    # Find a Month column in the schema
    month_col = None
    for col in schema.keys():
        if col.lower() in _MONTH_COLUMNS and col not in filtered_columns:
            month_col = col
            break

    if not month_col:
        return filters

    # Check if this month number was already extracted and used
    month_num_used = False
    for n in all_numbers:
        if n["value"] == month_num and id(n) in used_num_ids:
            month_num_used = True
            break

    if not month_num_used:
        filters.append({
            "column": month_col,
            "operator": "=",
            "value": month_num
        })
        filtered_columns.add(month_col)

        # Mark the corresponding number as used
        for n in all_numbers:
            if n["value"] == month_num and id(n) not in used_num_ids:
                used_num_ids.add(id(n))
                break

    return filters


def _extract_year_filter(question, schema, column_matches, filtered_columns, all_numbers, used_num_ids):
    """
    Special handling for year values in queries.
    If a 4-digit number that looks like a year appears, and there's a Year column,
    associate it with that column.
    """
    filters = []

    # Find a Year column in the schema
    year_col = None
    for col in schema.keys():
        if col.lower() in _YEAR_COLUMNS and col not in filtered_columns:
            year_col = col
            break

    if not year_col:
        return filters

    # Look for 4-digit numbers that could be years (1800-2100 range)
    for n in all_numbers:
        if id(n) in used_num_ids:
            continue
        try:
            val = int(n["value"])
            if 1800 <= val <= 2100:
                filters.append({
                    "column": year_col,
                    "operator": "=",
                    "value": n["value"]
                })
                filtered_columns.add(year_col)
                used_num_ids.add(id(n))
                break  # Only one year filter
        except (ValueError, TypeError):
            continue

    return filters


def _extract_implicit_numeric_filters(
    question,
    column_matches,
    numeric_columns,
    filtered_columns,
    all_numbers,
    used_num_ids
):
    filters = []

    if not column_matches or not all_numbers:
        return filters

    lower_question = question.lower()
    dimension_cols = {c for c in numeric_columns if c.lower() in _MONTH_COLUMNS | _YEAR_COLUMNS}

    # --- Pass 1: Numbers AFTER column (original logic) ---
    for column_match in column_matches:
        column = column_match["column"]
        if column not in numeric_columns or column in filtered_columns or column in dimension_cols:
            continue

        column_pos = column_match["position"]
        candidates = [n for n in all_numbers if id(n) not in used_num_ids and n["position"] > column_pos]
        if not candidates:
            continue

        number = min(candidates, key=lambda n: n["position"])
        number_pos = number["position"]
        between_text = lower_question[column_pos:number_pos]

        if re.search(r"\b(?:by|for|where|with|having)\b", between_text):
            continue
        if re.search(r"\b(?:top|bottom|lowest|highest|least|most)\b", between_text):
            continue
        if len(re.findall(r"[a-zA-Z_]+", between_text)) > 4:
            continue

        operator = _detect_implicit_operator(question, number_pos, column_pos, column, lower_question)
        filters.append({"column": column, "operator": operator, "value": number["value"]})
        filtered_columns.add(column)
        used_num_ids.add(id(number))

    # --- Pass 2: Numbers BEFORE column ("have 2 parking", "exactly 3 bedrooms") ---
    for column_match in column_matches:
        column = column_match["column"]
        if column not in numeric_columns or column in filtered_columns or column in dimension_cols:
            continue

        column_pos = column_match["position"]
        candidates = [n for n in all_numbers if id(n) not in used_num_ids and n["position"] < column_pos]
        if not candidates:
            continue

        number = max(candidates, key=lambda n: n["position"])
        number_pos = number["position"]
        between_text = lower_question[number_pos:column_pos]

        if len(re.findall(r"[a-zA-Z_]+", between_text)) > 5:
            continue
        if re.search(r"\b(?:where|having|group|order)\b", between_text):
            continue

        operator = _detect_implicit_operator_before(question, number_pos, column_pos, column, lower_question)
        filters.append({"column": column, "operator": operator, "value": number["value"]})
        filtered_columns.add(column)
        used_num_ids.add(id(number))

    return filters


def _detect_implicit_operator(question, number_pos, column_pos, column_name, lower_question):
    """Detect operator when column appears BEFORE number. E.g. "price over 5000" -> ">" """
    between = lower_question[column_pos:number_pos]
    if re.search(r"\b(?:more than|greater than|higher than|larger than|over|above|exceeding|older than)\b", between):
        return ">"
    if re.search(r"\b(?:less than|lower than|smaller than|under|below|fewer than|younger than)\b", between):
        return "<"
    if re.search(r"\b(?:at least|or more|>=|greater than or equal)\b", between):
        return ">="
    if re.search(r"\b(?:at most|or less|or fewer|<=|less than or equal)\b", between):
        return "<="
    if re.search(r"\b(?:exactly|equal to|equals)\b", between):
        return "="
    return "="


def _detect_implicit_operator_before(question, number_pos, column_pos, column_name, lower_question):
    """Detect operator when number appears BEFORE column. E.g. "exactly 3 bedrooms" -> "=", "4 or more bedrooms" -> ">=" """
    between = lower_question[number_pos:column_pos]
    if re.search(r"\b(?:or more|at least|or greater)\b", between):
        return ">="
    if re.search(r"\b(?:or less|at most|or fewer)\b", between):
        return "<="
    if re.search(r"\b(?:more than|greater than|higher than|over|above|exceeding)\b", between):
        return ">"
    if re.search(r"\b(?:less than|lower than|smaller than|under|below|fewer than)\b", between):
        return "<"
    if re.search(r"\b(?:exactly|equal to|equals|precisely)\b", between):
        return "="
    if re.search(r"\b(?:no|zero|without)\b", between):
        return "="
    # Check after column too for "4 or more bedrooms"
    after_col = lower_question[column_pos:column_pos+30]
    if re.search(r"\b(?:or more|at least)\b", after_col):
        return ">="
    if re.search(r"\b(?:or less|at most)\b", after_col):
        return "<="
    return "="


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
        get_numeric_columns(schema)
    )

    text_columns = set(
        get_text_columns(schema)
    )

    column_matches = find_columns_with_positions(
        question,
        schema,
        synonyms_path
    )

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
        col = match["column"]

        if col not in filtered_columns:
            filters.append({
                "column": col,
                "operator": "=",
                "value": match["value"]
            })

            filtered_columns.add(col)

    operators = detect_operators(
        question,
        operators_path
    )

    all_numbers = extract_numbers(question)
    used_num_ids = set()

    for op in operators:
        symbol = op["symbol"]
        op_pos = op["position"]

        if symbol in _SKIP_OPS:
            continue

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

            if col and col not in filtered_columns:
                filters.append({
                    "column": col,
                    "operator": symbol
                })

                filtered_columns.add(col)

            continue

        if symbol in _BETWEEN_OPS:
            nums_after = sorted(
                [
                    n for n in all_numbers
                    if n["position"] > op_pos
                    and id(n) not in used_num_ids
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

                if col and col not in filtered_columns:
                    filters.append({
                        "column": col,
                        "operator": symbol,
                        "value": nums_after[0]["value"],
                        "value2": nums_after[1]["value"]
                    })

                    filtered_columns.add(col)

                    used_num_ids.update({
                        id(nums_after[0]),
                        id(nums_after[1])
                    })

            continue

        if symbol in _LIKE_OPS:
            words_after = [
                m for m in re.finditer(
                    r"\S+",
                    question.lower()
                )
                if m.start() > op_pos
            ]

            if words_after:
                val = words_after[0].group().strip(
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

                if col and col not in filtered_columns:
                    filters.append({
                        "column": col,
                        "operator": "LIKE",
                        "value": f"%{val}%"
                    })

                    filtered_columns.add(col)

            continue

        if symbol in _SIMPLE_OPS:
            nums_after = sorted(
                [
                    n for n in all_numbers
                    if n["position"] > op_pos
                    and id(n) not in used_num_ids
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

            if col and col not in filtered_columns:
                filters.append({
                    "column": col,
                    "operator": symbol,
                    "value": nearest_num["value"]
                })

                filtered_columns.add(col)
                used_num_ids.add(
                    id(nearest_num)
                )

    # --- Month filter (before implicit numeric filters) ---
    month_filters = _extract_month_filter(
        question, schema, column_matches, filtered_columns,
        all_numbers, used_num_ids
    )
    filters.extend(month_filters)

    # --- Year filter ---
    year_filters = _extract_year_filter(
        question, schema, column_matches, filtered_columns,
        all_numbers, used_num_ids
    )
    filters.extend(year_filters)

    implicit_filters = _extract_implicit_numeric_filters(
        question,
        column_matches,
        numeric_columns,
        filtered_columns,
        all_numbers,
        used_num_ids
    )

    filters.extend(
        implicit_filters
    )

    agg_col = None

    if intent in _AGGREGATE_INTENTS:
        agg_col = _find_agg_column(
            question,
            column_matches,
            numeric_columns,
            intent=intent
        )

    group_by_col = _detect_group_by(
        question,
        column_matches,
        text_columns,
        numeric_columns=numeric_columns
    )

    order_col, order_dir, limit = _detect_order_limit(
        question,
        column_matches,
        numeric_columns,
        group_by=group_by_col,
        aggregate_column=agg_col
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


def query_to_sql(query, table_name="data"):
    intent = query["intent"]
    filters = query.get("filters", [])
    agg_column = query.get("agg_column")
    group_by = query.get("group_by")
    order_by = query.get("order_by")
    order_dir = query.get(
        "order_dir",
        "DESC"
    )
    limit = query.get("limit")

    tbl = _quote_identifier(
        table_name
    )

    aggregate_alias = None

    agg_overridden = (
        limit is not None
        and group_by is None
        and intent in _AGGREGATE_INTENTS
    )

    if intent == "SELECT" and group_by:
        select_part = (
            f"SELECT "
            f"{_quote_identifier(group_by)}, "
            f"COUNT(*)"
        )

    elif intent == "SELECT" or agg_overridden:
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
                f"Could not determine which column to apply "
                f"'{intent}' to. "
                f"Try rephrasing your question with the "
                f"column name, e.g. "
                f"'average of <column name>'."
            )

        col = _quote_identifier(
            agg_column
        )

        if group_by:
            alias_base = re.sub(
                r"[^a-zA-Z0-9]+",
                "_",
                agg_column
            ).strip("_").lower()

            aggregate_alias = (
                f"{intent.lower()}_{alias_base}"
            )

            select_part = (
                f"SELECT "
                f"{_quote_identifier(group_by)}, "
                f"{intent}({col}) AS "
                f"{_quote_identifier(aggregate_alias)}"
            )

        else:
            select_part = (
                f"SELECT "
                f"{intent}({col})"
            )

    else:
        select_part = "SELECT *"

    sql = (
        f"{select_part} "
        f"FROM {tbl}"
    )

    if filters:
        conditions = []

        for f in filters:
            col_q = _quote_identifier(
                f["column"]
            )

            operator = f["operator"]

            if operator in _NULL_OPS:
                conditions.append(
                    f"{col_q} {operator}"
                )

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
                    f"{col_q} {operator} "
                    f"{v1} AND {v2}"
                )

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
                    ).lstrip("-").isdigit()
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

        sql += (
            " WHERE "
            + " AND ".join(conditions)
        )

    if group_by:
        sql += (
            " GROUP BY "
            + _quote_identifier(group_by)
        )

    if order_by:
        if (
            query.get("order_by_aggregate")
            and aggregate_alias
        ):
            order_expression = _quote_identifier(
                aggregate_alias
            )
        else:
            order_expression = _quote_identifier(
                order_by
            )

        sql += (
            f" ORDER BY "
            f"{order_expression} "
            f"{order_dir}"
        )

    if limit:
        sql += (
            f" LIMIT {limit}"
        )

    return sql
