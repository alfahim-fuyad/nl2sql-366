import re


DANGEROUS_KEYWORDS = [
    "drop",
    "delete",
    "update",
    "insert",
    "alter",
    "attach",
    "detach",
    "pragma",
    "create",
    "truncate",
]


def _strip_string_literals(sql):
    """
    Remove SQL string literals before keyword/identifier checks.
    """

    return re.sub(
        r"'(?:[^']|'')*'",
        "''",
        sql
    )


def _normalize_column_name(name):
    """
    Normalize column name for comparison only.

    Examples:

        Monthly_Income -> monthly income
        Monthly Income -> monthly income
        MONTHLY_INCOME -> monthly income
        student-name   -> student name
    """

    if name is None:
        return ""

    text = str(name).strip().lower()

    text = text.replace(
        "_",
        " "
    )

    text = text.replace(
        "-",
        " "
    )

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def _build_column_lookup(schema):
    """
    Build normalized column -> exact schema column lookup.
    """

    lookup = {}

    for column in schema.keys():

        actual = str(
            column
        ).strip()

        if not actual:
            continue

        normalized = _normalize_column_name(
            actual
        )

        if normalized:
            lookup[normalized] = actual

    return lookup


def _resolve_schema_column(
    column,
    schema
):
    """
    Resolve a SQL column reference to the
    exact schema column.
    """

    if not column:
        return None

    column = str(
        column
    ).strip()

    if not column:
        return None

    # Exact
    if column in schema:
        return column

    # Case insensitive
    column_lower = column.lower()

    for raw_column in schema.keys():

        actual = str(
            raw_column
        ).strip()

        if actual.lower() == column_lower:
            return actual

    # Normalized
    normalized_target = _normalize_column_name(
        column
    )

    lookup = _build_column_lookup(
        schema
    )

    return lookup.get(
        normalized_target
    )


def _extract_where_columns(
    where_clause
):
    """
    Extract columns used in WHERE conditions.

    Supports:
        "Monthly_Income" > 50000
        `Monthly_Income` >= 50000
        Monthly_Income > 50000
        "Gender" = 'Male'
    """

    col_pattern = re.compile(
        r'''
        (?:
            "([^"]+)"
            |
            `([^`]+)`
            |
            ([A-Za-z_][A-Za-z0-9_]*)
        )
        \s*
        (?:
            !=
            |<>
            |>=
            |<=
            |=
            |>
            |<
            |\bLIKE\b
            |\bBETWEEN\b
            |\bIS\b
        )
        ''',
        re.IGNORECASE |
        re.VERBOSE
    )

    columns = []

    for match in col_pattern.finditer(
        where_clause
    ):

        column = (
            match.group(1)
            or match.group(2)
            or match.group(3)
            or ""
        ).strip()

        if not column:
            continue

        if column.lower() in {
            "and",
            "or",
            "not",
        }:
            continue

        columns.append(
            column
        )

    return columns


def _extract_select_columns(
    sql
):
    """
    Extract explicit columns from SELECT.

    Aggregate expressions such as:
        AVG("Monthly_Income")
        MAX("Age")
        MIN("Salary")
        SUM("Income")

    are supported.

    SELECT * is ignored.
    """

    match = re.search(
        r"\bselect\b(.+?)\bfrom\b",
        sql,
        re.IGNORECASE |
        re.DOTALL
    )

    if not match:
        return []

    select_part = match.group(1)

    columns = []

    # Quoted identifiers
    for quoted in re.findall(
        r'"([^"]+)"',
        select_part
    ):

        if quoted.strip() != "*":
            columns.append(
                quoted.strip()
            )

    # Backtick identifiers
    for quoted in re.findall(
        r'`([^`]+)`',
        select_part
    ):

        if quoted.strip() != "*":
            columns.append(
                quoted.strip()
            )

    return columns


def _extract_group_order_columns(
    sql
):
    """
    Extract GROUP BY / ORDER BY identifiers.
    """

    columns = []

    patterns = [
        r"\bgroup\s+by\s+(.+?)(?:\border\s+by\b|\blimit\b|$)",
        r"\border\s+by\s+(.+?)(?:\blimit\b|$)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            sql,
            re.IGNORECASE |
            re.DOTALL
        )

        if not match:
            continue

        clause = match.group(1)

        # Quoted identifiers
        for value in re.findall(
            r'"([^"]+)"',
            clause
        ):

            columns.append(
                value.strip()
            )

        for value in re.findall(
            r'`([^`]+)`',
            clause
        ):

            columns.append(
                value.strip()
            )

    return columns


def _validate_columns(
    columns,
    schema
):
    """
    Validate a list of columns against schema.
    """

    for column in columns:

        resolved = _resolve_schema_column(
            column,
            schema
        )

        if resolved is None:

            return (
                False,
                f"Column '{column}' "
                "does not exist in the schema."
            )

    return True, None


def validate_sql(
    sql,
    schema,
    table_name="data"
):
    """
    Validate generated SQL.

    Features:
        - SELECT only
        - blocks dangerous keywords
        - blocks multiple statements
        - validates table
        - validates WHERE columns
        - validates SELECT columns
        - validates GROUP BY columns
        - validates ORDER BY columns
        - supports spaces/underscores/case differences
    """

    if not isinstance(
        sql,
        str
    ):
        return False, "SQL must be a string."

    if not isinstance(
        schema,
        dict
    ):
        return False, "Invalid schema."

    sql_stripped = sql.strip()

    if not sql_stripped:
        return False, "SQL query is empty."

    sql_lower = sql_stripped.lower()

    # =========================================================
    # SELECT ONLY
    # =========================================================

    if not sql_lower.startswith(
        "select"
    ):

        return (
            False,
            "Only SELECT queries are allowed."
        )

    # =========================================================
    # STRING LITERALS
    # =========================================================

    sql_no_literals = _strip_string_literals(
        sql_stripped
    )

    sql_no_literals_low = (
        sql_no_literals.lower()
    )

    # =========================================================
    # DANGEROUS KEYWORDS
    # =========================================================

    for keyword in DANGEROUS_KEYWORDS:

        if re.search(
            r"\b"
            + re.escape(keyword)
            + r"\b",
            sql_no_literals_low
        ):

            return (
                False,
                f"Dangerous keyword detected: "
                f"'{keyword}'."
            )

    # =========================================================
    # MULTIPLE STATEMENTS
    # =========================================================

    if ";" in sql_stripped.rstrip(";"):

        return (
            False,
            "Multiple SQL statements are not allowed."
        )

    # =========================================================
    # TABLE VALIDATION
    # =========================================================

    table_lower = str(
        table_name
    ).lower()

    table_pattern = re.compile(
        r'\b(?:from|join)\s+'
        r'(?:'
        r'"'
        + re.escape(table_lower)
        + r'"'
        r'|'
        + re.escape(table_lower)
        + r'\b'
        r')',
        re.IGNORECASE
    )

    if not table_pattern.search(
        sql_no_literals
    ):

        return (
            False,
            f"Table '{table_name}' "
            "not found in query."
        )

    # =========================================================
    # VALIDATE SELECT COLUMNS
    # =========================================================

    select_columns = (
        _extract_select_columns(
            sql_stripped
        )
    )

    valid, error = _validate_columns(
        select_columns,
        schema
    )

    if not valid:
        return False, error

    # =========================================================
    # WHERE
    # =========================================================

    where_match = re.search(
        r"\bwhere\b"
        r"(.+?)"
        r"(?:"
        r"\bgroup\s+by\b"
        r"|"
        r"\border\s+by\b"
        r"|"
        r"\blimit\b"
        r"|$"
        r")",
        sql_stripped,
        re.IGNORECASE |
        re.DOTALL
    )

    if where_match:

        where_clause = (
            where_match.group(1)
        )

        where_no_literals = (
            _strip_string_literals(
                where_clause
            )
        )

        where_columns = (
            _extract_where_columns(
                where_no_literals
            )
        )

        valid, error = _validate_columns(
            where_columns,
            schema
        )

        if not valid:
            return False, error

    # =========================================================
    # GROUP BY / ORDER BY
    # =========================================================

    clause_columns = (
        _extract_group_order_columns(
            sql_stripped
        )
    )

    valid, error = _validate_columns(
        clause_columns,
        schema
    )

    if not valid:
        return False, error

    # =========================================================
    # SUCCESS
    # =========================================================

    return True, "SQL is valid."