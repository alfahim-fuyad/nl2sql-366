"""
Trains and saves the intent classification model.

Uses TF-IDF feature extraction with a Multinomial Naive Bayes classifier.
The trained model and vectorizer are saved as pickle files and loaded by
the application at startup.

Usage:
    python3 models/train_intent.py
"""

import pickle
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


def train_and_save(
    csv_path="training_data/intent_dataset.csv",
    model_path="models/intent_model.pkl",
    vectorizer_path="models/vectorizer.pkl",
):
    """Train the intent classifier and save the model and vectorizer to disk."""
    data      = pd.read_csv(csv_path)
    questions = data["question"]
    intents   = data["intent"]

    x_train, x_test, y_train, y_test = train_test_split(
        questions, intents, test_size=0.2, random_state=42
    )

    vectorizer   = TfidfVectorizer(ngram_range=(1, 2))
    x_train_vec  = vectorizer.fit_transform(x_train)
    x_test_vec   = vectorizer.transform(x_test)

    model = MultinomialNB()
    model.fit(x_train_vec, y_train)

    predictions = model.predict(x_test_vec)
    accuracy    = accuracy_score(y_test, predictions)
    print(f"Test accuracy: {round(accuracy * 100, 2)}%")

    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    with open(vectorizer_path, "wb") as f:
        pickle.dump(vectorizer, f)

    print(f"Model saved:      {model_path}")
    print(f"Vectorizer saved: {vectorizer_path}")


if __name__ == "__main__":
    train_and_save()
