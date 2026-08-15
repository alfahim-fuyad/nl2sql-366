# core/operator_detector.py

import re
import json


def load_operators(path="knowledge/operators.json"):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data.pop("_comment", None)
    return data


def detect_operators(text, operators_path="knowledge/operators.json"):
    operators = load_operators(operators_path)
    text_lower = text.lower()

    found = []
    used_positions = set()

    symbol_pattern = r"(>=|<=|!=|<>|>|<|=)"

    for match in re.finditer(symbol_pattern, text):
        start = match.start()
        end = match.end()

        found.append({
            "symbol": match.group(),
            "position": start
        })

        used_positions.update(range(start, end))

    sorted_phrases = sorted(
        operators.keys(),
        key=len,
        reverse=True
    )

    generic_phrases = {
        "is",
        "was",
        "are",
        "equal",
        "equals",
        "exactly"
    }

    stronger_operator_pattern = re.compile(
        r"^\s+"
        r"(greater than or equal to|"
        r"more than or equal to|"
        r"higher than or equal to|"
        r"no less than|"
        r"not less than|"
        r"at least|"
        r"less than or equal to|"
        r"lower than or equal to|"
        r"no more than|"
        r"not more than|"
        r"at most|"
        r"greater than|"
        r"more than|"
        r"older than|"
        r"higher than|"
        r"larger than|"
        r"bigger than|"
        r"above|"
        r"over|"
        r"exceeding|"
        r"exceeds|"
        r"after|"
        r"later than|"
        r"beyond|"
        r"less than|"
        r"younger than|"
        r"lower than|"
        r"smaller than|"
        r"below|"
        r"under|"
        r"before|"
        r"earlier than|"
        r"within|"
        r"beneath)",
        re.IGNORECASE
    )

    for phrase in sorted_phrases:

        pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"

        for match in re.finditer(pattern, text_lower):
            start = match.start()
            end = match.end()

            if any(pos in used_positions for pos in range(start, end)):
                continue

            if phrase in generic_phrases:
                remaining = text_lower[end:]

                if stronger_operator_pattern.search(remaining):
                    continue

            found.append({
                "symbol": operators[phrase],
                "position": start
            })

            used_positions.update(range(start, end))

    found.sort(key=lambda item: item["position"])

    strong_symbols = {
        ">",
        "<",
        ">=",
        "<=",
        "!=",
        "<>",
        "BETWEEN",
        "NOT BETWEEN",
        "IS NULL",
        "IS NOT NULL",
        "LIKE",
        "IN",
        "NOT IN"
    }

    strong_positions = [
        item["position"]
        for item in found
        if item["symbol"] in strong_symbols
    ]

    if strong_positions:
        cleaned = []

        for item in found:
            if item["symbol"] == "=":
                conflict = any(
                    0 <= strong_pos - item["position"] <= 30
                    for strong_pos in strong_positions
                )

                if conflict:
                    continue

            cleaned.append(item)

        found = cleaned

    return found