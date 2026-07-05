"""Tests for attribute matching and value extraction."""

from attribute_matcher import match_column
from value_matcher import extract_numbers, match_categorical_values


SCHEMA = {
    "Age":      {"dtype": "int64",  "sample_values": [30, 40]},
    "Gender":   {"dtype": "object", "sample_values": ["Male", "Female"]},
    "District": {"dtype": "object", "sample_values": ["Dhaka", "Sylhet"]},
}


def test_direct_column_match():
    assert match_column("age", SCHEMA, "knowledge/synonyms.json") == "Age"


def test_synonym_column_match():
    assert match_column("years", SCHEMA, "knowledge/synonyms.json") == "Age"


def test_no_match_returns_none():
    assert match_column("xyz123", SCHEMA, "knowledge/synonyms.json") is None


def test_extract_numbers():
    numbers = extract_numbers("show patients older than 30")
    assert len(numbers) == 1
    assert numbers[0]["value"] == "30"


def test_categorical_match_no_false_positive():
    # "female" must not also match "Male"
    matches = match_categorical_values("show female patients", SCHEMA)
    values  = [m["value"] for m in matches]
    assert "Female" in values
    assert "Male" not in values


def test_categorical_match_district():
    matches = match_categorical_values("patients from dhaka", SCHEMA)
    values  = [m["value"] for m in matches]
    assert "Dhaka" in values
