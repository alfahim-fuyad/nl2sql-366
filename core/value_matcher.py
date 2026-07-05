"""
Extracts filter values from a natural language question.

Two types of values are detected:
    - Numeric: integers and floats found via regular expression.
    - Categorical: text values matched against the schema's sample_values
      using case-insensitive word-boundary search.
"""

import re
from collections import defaultdict

_BINARY_TRUE_MAP  = {"yes": "Yes", "true": "True", "1": "1"}
_BINARY_FALSE_MAP = {"no": "No",  "false": "False", "0": "0"}


def extract_numbers(text):
    """
    Find all integers and floats in the text, with their character positions.

    Returns:
        List of dicts: [{"value": "30", "position": 25}, ...]
    """
    numbers = []
    for match in re.finditer(r"\b\d+(?:\.\d+)?\b", text):
        numbers.append({"value": match.group(), "position": match.start()})
    return numbers


def _is_binary_column(sample_values):
    """
    Return True if a column has exactly two values that form a binary pair.

    Recognized pairs: yes/no, true/false, 0/1.
    """
    if len(sample_values) != 2:
        return False
    lower_vals = {str(v).lower() for v in sample_values}
    return lower_vals in [{"yes", "no"}, {"true", "false"}, {"0", "1"}]


def match_categorical_values(text, schema, allowed_columns=None):
    """
    Find categorical filter values in the question by comparing against the schema.

    Rules:
        - Numeric columns are skipped (handled by the operator detector).
        - At most one value per column is matched (the first occurrence).
        - Word-boundary checks prevent partial-word false positives
          (e.g. "female" will not also match "Male").
        - Matching is case-insensitive; the original-case value is returned.
        - Ambiguity guard: if a value word appears in more than one column's
          sample_values, it is only matched for columns that are present in
          allowed_columns.  Unambiguous values (only one column owns them) are
          always matched, regardless of allowed_columns.  This prevents shared
          binary values like "Yes"/"No" from being silently assigned to a column
          that was never mentioned in the question.

    Args:
        text:            The natural-language question.
        schema:          Dict mapping column names to {"dtype", "sample_values"}.
        allowed_columns: Set of column names explicitly found in the question.
                         Pass None to skip the ambiguity guard entirely (legacy).

    Returns:
        List of dicts: [{"column": "Gender", "value": "Female"}, ...]
    """
    text_lower = text.lower()

    # --- Step 1: build value → [columns] index for ambiguity detection --------
    # Only index non-numeric columns.
    value_to_columns = defaultdict(list)
    for column, info in schema.items():
        if "int" in info["dtype"] or "float" in info["dtype"]:
            continue
        for sample in info.get("sample_values", []):
            sample_lower = str(sample).lower()
            if sample_lower:
                value_to_columns[sample_lower].append(column)

    # --- Step 2: scan schema columns for matching values ----------------------
    matches         = []
    matched_columns = set()

    for column, info in schema.items():
        if column in matched_columns:
            continue

        dtype = info["dtype"]
        if "int" in dtype or "float" in dtype:
            continue

        sample_values = info.get("sample_values", [])
        if not sample_values:
            continue

        for sample in sample_values:
            sample_str   = str(sample)
            sample_lower = sample_str.lower()
            if not sample_lower:
                continue

            pattern = r"(?<![a-z0-9])" + re.escape(sample_lower) + r"(?![a-z0-9])"
            if not re.search(pattern, text_lower):
                continue

            # Value found in text — apply ambiguity guard when requested.
            if allowed_columns is not None:
                owners = value_to_columns[sample_lower]
                is_ambiguous = len(owners) > 1
                if is_ambiguous and column not in allowed_columns:
                    # Ambiguous value, and this column wasn't mentioned → skip.
                    continue

            matches.append({"column": column, "value": sample_str})
            matched_columns.add(column)
            break  # at most one value per column

    return matches
