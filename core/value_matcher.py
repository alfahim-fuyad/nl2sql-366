# core/value_matcher.py

import re
import calendar
from collections import defaultdict

_BINARY_TRUE_MAP  = {"yes": "Yes", "true": "True", "1": "1"}
_BINARY_FALSE_MAP = {"no": "No",  "false": "False", "0": "0"}

# Month name -> number mapping
_MONTH_MAP = {name.lower(): str(num) for num, name in enumerate(calendar.month_name) if num}
_MONTH_MAP.update({
    "jan": "1", "feb": "2", "mar": "3", "apr": "4",
    "may": "5", "jun": "6", "jul": "7", "aug": "8",
    "sep": "9", "oct": "10", "nov": "11", "dec": "12",
})

# Binary column descriptor patterns:
#   "houses have air conditioning" -> column=airconditioning, value='yes'
#   "houses without a basement"    -> column=basement, value='no'
_POSSESSIVE_YES = re.compile(
    r"\b(?:have|has|with|got)\s+(?:a\s+|an\s+)?"  # "have a / have / with a"
    r"([a-z][a-z\s]*?)"
    r"(?:\?|\.|,|;|$)",
    re.IGNORECASE,
)
_NEGATION_NO = re.compile(
    r"\b(?:without|no|don'?t have|does not have|do not have|doesn'?t have)\s+(?:a\s+|an\s+)?"
    r"([a-z][a-z\s]*?)"
    r"(?:\?|\.|,|;|$)",
    re.IGNORECASE,
)


def extract_numbers(text):
    """
    Extract numeric values from text.
    Handles comma-separated numbers like "5,000,000" -> "5000000".
    Also extracts month names as their numeric equivalents.
    Returns list of {"value": str, "position": int}.
    """
    numbers = []

    # First pass: comma-separated numbers (e.g., "5,000,000" or "1,234.56")
    for match in re.finditer(r"\b(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d+)\b", text):
        raw = match.group()
        # Remove commas for numeric value
        clean = raw.replace(",", "")
        # Skip if this is part of a comma-separated number that was already matched
        # (the regex above already handles multi-part comma numbers)
        numbers.append({"value": clean, "position": match.start()})

    # Second pass: month names -> numbers
    seen_positions = {n["position"] for n in numbers}
    text_lower = text.lower()
    for month_name, month_num in _MONTH_MAP.items():
        # Word-boundary match for month names
        pattern = r"\b" + re.escape(month_name) + r"\b"
        for m in re.finditer(pattern, text_lower):
            if m.start() not in seen_positions:
                numbers.append({"value": month_num, "position": m.start()})
                seen_positions.add(m.start())

    # Sort by position in text
    numbers.sort(key=lambda n: n["position"])
    return numbers


def _is_binary_column(sample_values):
    if len(sample_values) != 2:
        return False
    lower_vals = {str(v).lower() for v in sample_values}
    return lower_vals in [{"yes", "no"}, {"true", "false"}, {"0", "1"}]


def _is_binary_int_column(sample_values):
    """Check if a column has only 0/1 integer values (numeric binary)."""
    if len(sample_values) != 2:
        return False
    lower_vals = {str(v).lower() for v in sample_values}
    return lower_vals == {"0", "1"}


def match_binary_int_descriptions(text, schema, allowed_columns=None):
    """
    Match natural language descriptions to binary integer columns (0/1).
    E.g., dengue dataset: NS1=1, IgG=1, IgM=1, Headache=1, etc.
    """
    text_lower = text.lower()
    matches = []

    for column, info in schema.items():
        if "int" not in info["dtype"] and "float" not in info["dtype"]:
            continue

        sample_values = info.get("sample_values", [])
        if not _is_binary_int_column(sample_values):
            continue

        col_lower = column.lower()
        # Check if the column name (or close variant) appears in text
        # For columns like NS1, IgG, IgM - check exact-ish match
        col_words = re.sub(r"[^a-z0-9]", " ", col_lower).split()

        # For short column names, require exact match
        if len(col_lower) <= 4:
            if re.search(r"\b" + re.escape(col_lower) + r"\b", text_lower):
                matches.append({"column": column, "value": "1"})
        else:
            # For longer names, check if key words appear
            matched = False
            for word in col_words:
                if len(word) >= 3 and re.search(r"\b" + re.escape(word) + r"\b", text_lower):
                    matches.append({"column": column, "value": "1"})
                    matched = True
                    break

    return matches


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

    # --- Strategy 1: Direct substring match (original logic) ---
    for column, info in schema.items():
        if column in matched_columns:
            continue

        dtype = info["dtype"]
        if "int" in dtype or "float" in dtype:
            continue

        sample_values = info.get("sample_values", [])
        if not sample_values:
            continue

        # Sort by length descending to prefer longer matches
        # ("semi-furnished" before "furnished")
        for sample in sorted(sample_values, key=lambda s: len(str(s)), reverse=True):
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

    # --- Strategy 2: Binary column possessive/negation patterns ---
    # Handles: "have air conditioning" -> airconditioning='yes'
    #          "without a basement"   -> basement='no'
    for column, info in schema.items():
        if column in matched_columns:
            continue
        dtype = info["dtype"]
        if "int" in dtype or "float" in dtype:
            continue

        sample_values = info.get("sample_values", [])
        if not _is_binary_column(sample_values):
            continue

        yes_val = None
        no_val = None
        for v in sample_values:
            vl = str(v).lower()
            if vl in ("yes", "true", "1"):
                yes_val = str(v)
            elif vl in ("no", "false", "0"):
                no_val = str(v)

        col_lower = column.lower()
        # Normalize column name: remove non-alphanumeric for comparison
        col_compact = re.sub(r"[^a-z0-9]", "", col_lower)

        # Build variants of the column descriptor:
        # e.g. "airconditioning" -> ["airconditioning", "air conditioning"]
        # e.g. "mainroad" -> ["mainroad", "main road"]
        # e.g. "basement" -> ["basement"]
        col_variants = [col_lower]
        if len(col_compact) != len(col_lower):
            # Column has underscores or other separators
            col_variants.append(col_compact)
        # Also try inserting spaces at plausible word boundaries
        # in compound words (heuristic: before consonant clusters following a vowel)
        spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", column)
        spaced = re.sub(r"([a-z])(?=[bcdfghjklmnpqrstvwxyz]{2,})", r"\1 ", spaced.lower())
        if spaced != col_lower and spaced not in col_variants:
            col_variants.append(spaced)

        # Also load synonyms for this column to get more variants
        try:
            import json, os
            syn_path = os.path.join(os.path.dirname(__file__), "..", "knowledge", "synonyms.json")
            if os.path.exists(syn_path):
                with open(syn_path, "r") as sf:
                    syns = json.load(sf)
                    syns.pop("_comment", None)
                # Add any synonym that maps TO this column
                for key, val in syns.items():
                    if val.lower() == col_lower and key not in col_variants:
                        col_variants.append(key.lower())
        except Exception:
            pass

        # Check possessive/preposition pattern:
        # "have/with/are/on <column_desc>" -> yes
        if yes_val:
            found = False
            for variant in col_variants:
                pat = re.escape(variant)
                possessive_re = re.compile(
                    r"\b(?:have|has|with|got|are|on the|on)\s+(?:a\s+|an\s+)?"
                    + pat +
                    r"\b",
                    re.IGNORECASE,
                )
                if possessive_re.search(text_lower):
                    if allowed_columns is None or column in allowed_columns:
                        matches.append({"column": column, "value": yes_val})
                        matched_columns.add(column)
                        found = True
                    break
            if found:
                continue

        # Check negation pattern: "without/no <column_desc>"
        if no_val and column not in matched_columns:
            for variant in col_variants:
                pat = re.escape(variant)
                negation_re = re.compile(
                    r"\b(?:without|no|don'?t have|does not have|do not have|doesn'?t have)\s+(?:a\s+|an\s+)?"
                    + pat +
                    r"\b",
                    re.IGNORECASE,
                )
                if negation_re.search(text_lower):
                    if allowed_columns is None or column in allowed_columns:
                        matches.append({"column": column, "value": no_val})
                        matched_columns.add(column)
                    break

    # --- Strategy 3: Fuzzy value matching for long values ---
    # Handles: "semi-furnished" might appear as "semi furnished" in text
    # Prefer LONGER matches to avoid "furnished" matching inside "semi-furnished"
    from rapidfuzz import fuzz
    for column, info in schema.items():
        if column in matched_columns:
            continue
        dtype = info["dtype"]
        if "int" in dtype or "float" in dtype:
            continue

        sample_values = info.get("sample_values", [])
        if not sample_values:
            continue

        # Sort by length descending: try longest values first
        sorted_samples = sorted(sample_values, key=lambda s: len(str(s)), reverse=True)

        for sample in sorted_samples:
            sample_str = str(sample)
            sample_lower = sample_str.lower()
            if len(sample_lower) < 4:
                continue

            sample_norm = re.sub(r"[^a-z0-9]", " ", sample_lower)
            text_norm = re.sub(r"[^a-z0-9]", " ", text_lower)

            # Use word-boundary check: the normalized sample must appear
            # as a complete phrase, not just as a substring
            if re.search(r"\b" + re.escape(sample_norm.strip()) + r"\b", text_norm):
                if allowed_columns is None or column in allowed_columns:
                    matches.append({"column": column, "value": sample_str})
                    matched_columns.add(column)
                    break

    return matches
