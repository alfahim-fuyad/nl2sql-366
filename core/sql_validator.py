# core/sql_validator.py

import re

DANGEROUS_KEYWORDS = [
    "drop", "delete", "update", "insert", "alter",
    "attach", "detach", "pragma", "create", "truncate",
]


def _strip_string_literals(sql):
    return re.sub(r"'(?:[^']|'')*'", "''", sql)


def validate_sql(sql, schema, table_name="data"):
    sql_stripped = sql.strip()
    sql_lower    = sql_stripped.lower()

    if not sql_lower.startswith("select"):
        return False, "Only SELECT queries are allowed."

    sql_no_literals     = _strip_string_literals(sql_stripped)
    sql_no_literals_low = sql_no_literals.lower()

    for keyword in DANGEROUS_KEYWORDS:
        if re.search(r"\b" + re.escape(keyword) + r"\b", sql_no_literals_low):
            return False, f"Dangerous keyword detected: '{keyword}'."

    if ";" in sql_stripped.rstrip(";"):
        return False, "Multiple SQL statements are not allowed."

    table_lower = table_name.lower()
    table_pattern = re.compile(
        r'\b(?:from|join)\s+(?:"' + re.escape(table_lower) + r'"|'
        + re.escape(table_lower) + r'\b)',
        re.IGNORECASE,
    )
    if not table_pattern.search(sql_no_literals):
        return False, f"Table '{table_name}' not found in query."

    valid_columns_lower = {c.lower() for c in schema.keys()}

    where_match = re.search(
        r"\bwhere\b(.+?)(?:\bgroup\s+by\b|\border\s+by\b|\blimit\b|$)",
        sql_stripped,
        re.IGNORECASE | re.DOTALL,
    )

    if where_match:
        where_clause      = where_match.group(1)
        where_no_literals = _strip_string_literals(where_clause)

        col_pattern = re.compile(
            r'(?:"([^"]+)"|`([^`]+)`|([A-Za-z_][A-Za-z0-9_ ]*))'
            r'\s*(?:=|!=|<>|>=|<=|>|<|\bLIKE\b|\bBETWEEN\b|\bIS\b)',
            re.IGNORECASE,
        )

        for m in col_pattern.finditer(where_no_literals):
            col_name = (m.group(1) or m.group(2) or m.group(3) or "").strip()
            if not col_name:
                continue
            if col_name.lower() in ("and", "or", "not"):
                continue
            if col_name.lower() not in valid_columns_lower:
                return False, f"Column '{col_name}' does not exist in the schema."

    return True, "SQL is valid."
