# tests/test_tokenizer_and_operator.py

from tokenizer import tokenize, clean_text
from operator_detector import detect_operators


def test_clean_text_removes_symbols():
    assert clean_text("Show ME, Female Patients!!") == "show me female patients"


def test_tokenize_removes_stopwords():
    tokens = tokenize("show all female patients", "knowledge/stopwords.json")
    assert "show" not in tokens
    assert "all" not in tokens
    assert "female" in tokens
    assert "patients" in tokens


def test_detect_operator_greater_than():
    result = detect_operators("age greater than 30", "knowledge/operators.json")
    assert len(result) == 1
    assert result[0]["symbol"] == ">"


def test_detect_operator_older_than():
    result = detect_operators("patients older than 40", "knowledge/operators.json")
    assert result[0]["symbol"] == ">"


def test_detect_operator_less_than():
    result = detect_operators("marks less than 50", "knowledge/operators.json")
    assert result[0]["symbol"] == "<"
