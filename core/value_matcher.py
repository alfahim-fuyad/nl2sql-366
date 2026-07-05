"""
Extracts filter values from a natural language question.

Two types of values are detected:
    - Numeric: integers and floats found via regular expression.
    - Categorical: text values matched against the schema's sample_values
      using case-insensitive word-boundary search.
"""

import re

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


def match_categorical_values(text, schema):
    """
    Find categorical filter values in the question by comparing against the schema.

    Rules:
        - Numeric columns are skipped (handled by the operator detector).
        - At most one value per column is matched (the first occurrence).
        - Word-boundary checks prevent partial-word false positives
          (e.g. "female" will not also match "Male").
        - Matching is case-insensitive; the original-case value is returned.

    Returns:
        List of dicts: [{"column": "Gender", "value": "Female"}, ...]
    """
    text_lower      = text.lower()
    matches         = []
    matched_columns = set()

    for column, info in schema.items():
        dtype = info["dtype"]
        if "int" in dtype or "float" in dtype:
            continue

        sample_values = info["sample_values"]
        if not sample_values:
            continue

        column_matched = False

        for sample in sample_values:
            if column_matched:
                break

            sample_str   = str(sample)
            sample_lower = sample_str.lower()
            if not sample_lower:
                continue

            pattern = r"(?<![a-z0-9])" + re.escape(sample_lower) + r"(?![a-z0-9])"

            if re.search(pattern, text_lower):
                if column in matched_columns:
                    continue
                matches.append({"column": column, "value": sample_str})
                matched_columns.add(column)
                column_matched = True

    return matches
