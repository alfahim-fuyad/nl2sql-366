"""
Text cleaning and tokenization utilities.

The main pipeline uses raw question text directly, but this module is used
by the test suite and is available as a utility for preprocessing tasks.
"""

import os
import re
import json


def load_stopwords(path="knowledge/stopwords.json"):
    """Load the stopword list. Returns an empty list if the file is missing."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_text(text):
    """
    Lowercase the text and remove punctuation.

    Retains letters, digits, and spaces. Non-alphanumeric characters
    (including hyphens and apostrophes) are replaced with spaces so that
    word boundaries are preserved.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text, stopwords_path="knowledge/stopwords.json"):
    """
    Clean the text, split into tokens, and remove stopwords.

    Returns a list of meaningful word tokens from the question.
    """
    stopwords = load_stopwords(stopwords_path)
    cleaned   = clean_text(text)
    tokens    = cleaned.split()
    return [t for t in tokens if t not in stopwords]
