"""
Detects SQL comparison operators from natural language phrases.

Scans the question for phrases defined in operators.json (e.g. "older than" → ">"),
using greedy longest-first matching to avoid shorter phrases shadowing longer ones.
Also supports symbolic operators such as >, <, >=, <=, =, !=.
"""

import re
import json


def load_operators(path="knowledge/operators.json"):
    """Load the phrase-to-operator mapping from the JSON knowledge file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.pop("_comment", None)
    return data


def detect_operators(text, operators_path="knowledge/operators.json"):
    """
    Find all SQL operators referenced in the question, with their positions.

    Supports both natural language operators and symbolic operators.

    Returns:
        List of dicts: [{"symbol": ">", "position": 10}, ...]
        Sorted by ascending position in the original text.
    """
    operators = load_operators(operators_path)
    text_lower = text.lower()

    found = []
    used_positions = set()

    # -----------------------------
    # Step 1: Detect symbolic operators
    # -----------------------------
    symbol_pattern = r"(>=|<=|!=|<>|>|<|=)"

    for match in re.finditer(symbol_pattern, text):
        start = match.start()
        end = match.end()

        found.append({
            "symbol": match.group(),
            "position": start
        })

        used_positions.update(range(start, end))

    # -----------------------------
    # Step 2: Detect phrase operators
    # -----------------------------
    sorted_phrases = sorted(operators.keys(), key=len, reverse=True)

    for phrase in sorted_phrases:

        for match in re.finditer(re.escape(phrase), text_lower):
            start = match.start()
            end = match.end()

            if set(range(start, end)) & used_positions:
                continue

            char_before = text_lower[start - 1] if start > 0 else " "
            char_after = text_lower[end] if end < len(text_lower) else " "

            if not (char_before in (" ", "\t") or start == 0):
                continue

            if not (char_after in (" ", "\t") or end == len(text_lower)):
                continue

            found.append({
                "symbol": operators[phrase],
                "position": start
            })

            used_positions.update(range(start, end))

    found.sort(key=lambda item: item["position"])
    return found