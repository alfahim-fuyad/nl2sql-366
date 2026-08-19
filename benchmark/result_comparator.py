# result_comparator.py — robust result-set comparison for NL2SQL benchmarking.
#
# Design principles:
#   1. Execute both reference and generated SQL, compare RESULT SETS, not strings.
#   2. Two SQL queries that produce identical results are considered equivalent.
#   3. Handle row ordering, column ordering, numeric precision, NULLs, empty results.
#   4. Preserve ordering for ORDER BY queries; use set comparison otherwise.

import math
import re
from typing import List, Tuple, Any, Optional


# ---------------------------------------------------------------------------
# Value normalization
# ---------------------------------------------------------------------------

def _normalize_value(v: Any) -> Any:
    """Normalize a single cell value for comparison."""
    if v is None:
        return None

    # Booleans → int (SQLite may return 0/1)
    if isinstance(v, bool):
        return int(v)

    # Integers
    if isinstance(v, int) and not isinstance(v, bool):
        return v

    # Floats — round to reasonable precision
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return str(v)
        # Round to 6 decimal places to handle floating-point drift
        rounded = round(v, 6)
        # If it's effectively an integer, convert
        if rounded == int(rounded) and abs(rounded) < 1e15:
            return int(rounded)
        return rounded

    # Strings — strip whitespace
    if isinstance(v, str):
        return v.strip()

    return v


def _values_equal(a: Any, b: Any, rel_tol: float = 1e-6, abs_tol: float = 1e-9) -> bool:
    """Compare two normalized values with numeric tolerance."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False

    # Both numeric
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == b:
            return True
        # Relative tolerance for floats
        if isinstance(a, float) or isinstance(b, float):
            fa, fb = float(a), float(b)
            if fa == 0.0 and fb == 0.0:
                return True
            if fa == 0.0 or fb == 0.0:
                return abs(fa - fb) < abs_tol
            return abs(fa - fb) / max(abs(fa), abs(fb)) <= rel_tol
        return a == b

    # Both strings
    if isinstance(a, str) and isinstance(b, str):
        return a == b

    # Mixed types — try numeric comparison
    try:
        return _values_equal(float(a), float(b), rel_tol, abs_tol)
    except (TypeError, ValueError):
        return str(a) == str(b)


# ---------------------------------------------------------------------------
# Result-set normalization
# ---------------------------------------------------------------------------

def _is_order_sensitive(sql: str) -> bool:
    """Check whether a SQL query contains ORDER BY (order matters)."""
    # Remove subqueries to avoid false positives
    # Simple heuristic: if ORDER BY appears at the top level
    sql_upper = sql.upper().strip()
    if 'ORDER BY' not in sql_upper:
        return False
    # Check it's not inside a subquery (simple check)
    # Find the last ORDER BY which is the one that matters
    depth = 0
    for m in re.finditer(r'\(', sql):
        pass  # just count
    # Simpler: just check if ORDER BY exists
    return True


def normalize_rows(rows: List[Tuple], columns: List[str],
                   order_sensitive: bool = False) -> List[Tuple]:
    """
    Normalize a result set for comparison.
    Returns a list of tuples with normalized values.
    """
    if not rows:
        return []

    normalized = [tuple(_normalize_value(v) for v in row) for row in rows]

    if not order_sensitive:
        # Sort for order-insensitive comparison
        # Sort by converting each row to a tuple of comparable values
        def sort_key(row):
            key = []
            for v in row:
                if v is None:
                    # None sorts first
                    key.append((0, ""))
                elif isinstance(v, (int, float)):
                    key.append((1, v))
                else:
                    key.append((2, str(v)))
            return key

        normalized.sort(key=sort_key)

    return normalized


def compare_results(ref_cols: List[str], ref_rows: List[Tuple],
                    gen_cols: List[str], gen_rows: List[Tuple],
                    ref_sql: str = "", gen_sql: str = "") -> dict:
    """
    Compare reference and generated SQL execution results.

    Returns a dict with:
        - match: bool — whether results are equivalent
        - match_type: str — category of comparison
        - detail: str — human-readable explanation
        - ref_row_count: int
        - gen_row_count: int
        - ref_col_count: int
        - gen_col_count: int
    """
    ref_ncols = len(ref_cols)
    gen_ncols = len(gen_cols)
    ref_nrows = len(ref_rows)
    gen_nrows = len(gen_rows)

    # Both empty
    if ref_nrows == 0 and gen_nrows == 0:
        return {
            "match": True,
            "match_type": "both_empty",
            "detail": "Both result sets are empty.",
            "ref_row_count": 0, "gen_row_count": 0,
            "ref_col_count": ref_ncols, "gen_col_count": gen_ncols,
        }

    # One empty, one not
    if ref_nrows == 0 or gen_nrows == 0:
        return {
            "match": False,
            "match_type": "row_count_mismatch",
            "detail": f"Row count mismatch: reference has {ref_nrows}, generated has {gen_nrows}.",
            "ref_row_count": ref_nrows, "gen_row_count": gen_nrows,
            "ref_col_count": ref_ncols, "gen_col_count": gen_ncols,
        }

    # Column count mismatch (for non-aggregate single-column results, this may be OK)
    # For now, if both are single-column, compare directly
    if ref_ncols != gen_ncols and not (ref_ncols == 1 and gen_ncols == 1):
        return {
            "match": False,
            "match_type": "column_count_mismatch",
            "detail": f"Column count mismatch: reference has {ref_ncols}, generated has {gen_ncols}.",
            "ref_row_count": ref_nrows, "gen_row_count": gen_nrows,
            "ref_col_count": ref_ncols, "gen_col_count": gen_ncols,
        }

    # Determine if ordering matters
    order_sensitive = _is_order_sensitive(ref_sql)

    ref_normalized = normalize_rows(ref_rows, ref_cols, order_sensitive)
    gen_normalized = normalize_rows(gen_rows, gen_cols, order_sensitive)

    # Row count check
    if ref_nrows != gen_nrows:
        return {
            "match": False,
            "match_type": "row_count_mismatch",
            "detail": f"Row count mismatch: reference has {ref_nrows}, generated has {gen_nrows}.",
            "ref_row_count": ref_nrows, "gen_row_count": gen_nrows,
            "ref_col_count": ref_ncols, "gen_col_count": gen_ncols,
        }

    # Compare row by row
    mismatches = 0
    first_mismatch_detail = ""
    for i, (ref_row, gen_row) in enumerate(zip(ref_normalized, gen_normalized)):
        for j, (rv, gv) in enumerate(zip(ref_row, gen_row)):
            if not _values_equal(rv, gv):
                mismatches += 1
                if not first_mismatch_detail:
                    col_name = ref_cols[j] if j < len(ref_cols) else f"col{j}"
                    first_mismatch_detail = (
                        f"Row {i+1}, column '{col_name}': "
                        f"reference={rv!r}, generated={gv!r}"
                    )
                break  # One mismatch per row is enough to note

    if mismatches == 0:
        match_type = "exact_match" if ref_sql.strip().upper() == gen_sql.strip().upper() else "result_equivalent"
        return {
            "match": True,
            "match_type": match_type,
            "detail": f"All {ref_nrows} rows match. ({match_type})",
            "ref_row_count": ref_nrows, "gen_row_count": gen_nrows,
            "ref_col_count": ref_ncols, "gen_col_count": gen_ncols,
        }

    return {
        "match": False,
        "match_type": "value_mismatch",
        "detail": f"{mismatches}/{ref_nrows} rows differ. {first_mismatch_detail}",
        "ref_row_count": ref_nrows, "gen_row_count": gen_nrows,
        "ref_col_count": ref_ncols, "gen_col_count": gen_ncols,
    }


def classify_failure(query_record: dict) -> str:
    """
    Classify WHY a query failed, for error analysis.

    Returns one of:
        intent_error, schema_error, attribute_error, operator_error,
        value_error, sql_generation_error, sql_validation_error,
        sql_execution_error, result_mismatch
    """
    if not query_record.get("intent_match", True):
        return "intent_error"

    if not query_record.get("valid_sql", True):
        return "sql_validation_error"

    if not query_record.get("execution_success", True):
        return "sql_execution_error"

    if not query_record.get("result_match", True):
        # Distinguish between different failure modes
        comp = query_record.get("result_comparison", {})
        match_type = comp.get("match_type", "")

        if match_type == "row_count_mismatch":
            return "result_mismatch"
        if match_type == "column_count_mismatch":
            return "result_mismatch"
        if match_type == "value_mismatch":
            # Could be due to attribute, operator, or value errors
            return "result_mismatch"

    return "unknown"
