# core/value_matcher.py

import re
from collections import defaultdict

_BINARY_TRUE_MAP  = {"yes": "Yes", "true": "True", "1": "1"}
_BINARY_FALSE_MAP = {"no": "No",  "false": "False", "0": "0"}


def extract_numbers(text):
    numbers = []
    for match in re.finditer(r"\b\d+(?:\.\d+)?\b", text):
        numbers.append({"value": match.group(), "position": match.start()})
    return numbers


def _is_binary_column(sample_values):
    if len(sample_values) != 2:
        return False
    lower_vals = {str(v).lower() for v in sample_values}
    return lower_vals in [{"yes", "no"}, {"true", "false"}, {"0", "1"}]


def match_categorical_values(text, schema, allowed_columns=None):
    text_lower = text.lower()

    value_to_columns = defaultdict(list)
    for column, info in schema.items():
        if "int" in info["dtype"] or "float" in info["dtype"]:
            continue
        for sample in info.get("sample_values", []):
            sample_lower = str(sample).lower()
            if sample_lower:
                value_to_columns[sample_lower].append(column)

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

            if allowed_columns is not None:
                owners = value_to_columns[sample_lower]
                is_ambiguous = len(owners) > 1
                if is_ambiguous and column not in allowed_columns:
                    continue

            matches.append({"column": column, "value": sample_str})
            matched_columns.add(column)
            break

    return matches
