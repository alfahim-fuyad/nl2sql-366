# core/tokenizer.py

import os
import re
import json


def load_stopwords(path="knowledge/stopwords.json"):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_text(text):
    text = text.lower()

    text = re.sub(r"(>=|<=|!=|>|<|=)", r" \1 ", text)

    text = re.sub(r"[^a-z0-9\s><=!.]", " ", text)

    text = re.sub(r"\s+", " ", text).strip()

    return text


def tokenize(text, stopwords_path="knowledge/stopwords.json"):
    stopwords = load_stopwords(stopwords_path)
    cleaned = clean_text(text)
    tokens = cleaned.split()
    return [t for t in tokens if t not in stopwords]
