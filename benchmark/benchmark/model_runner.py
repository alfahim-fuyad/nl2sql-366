"""
model_runner.py — trains a simple ML model per dataset (classification or
regression, depending on config.ML_TASKS) and answers prediction questions.
"""
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error

from . import config
from . import dataset_loader

_MODEL_CACHE = {}


def _prepare_features(df: pd.DataFrame, target: str, drop_cols):
    y = df[target]
    X = df.drop(columns=[target] + [c for c in drop_cols if c in df.columns])
    X = pd.get_dummies(X, drop_first=True)
    return X, y


def _train(dataset_key: str):
    """Train (once, cached) the model for a dataset and stash everything
    needed to answer prediction questions about specific rows."""
    if dataset_key in _MODEL_CACHE:
        return _MODEL_CACHE[dataset_key]

    task_cfg = config.ML_TASKS[dataset_key]
    target = task_cfg["target"]
    task_type = task_cfg["task_type"]
    drop_cols = task_cfg["drop_cols"]

    df = dataset_loader.get_dataframe(dataset_key)
    target = target.replace(" ", "_")
    drop_cols = [c.replace(" ", "_") for c in drop_cols]

    X, y = _prepare_features(df, target, drop_cols)

    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X, y, df.index, test_size=0.2, random_state=config.RANDOM_STATE
    )

    if task_type == "classification":
        model = RandomForestClassifier(n_estimators=200, random_state=config.RANDOM_STATE)
    else:
        model = RandomForestRegressor(n_estimators=200, random_state=config.RANDOM_STATE)

    model.fit(X_train, y_train)

    if task_type == "classification":
        score = accuracy_score(y_test, model.predict(X_test))
    else:
        score = mean_squared_error(y_test, model.predict(X_test)) ** 0.5  # RMSE

    result = {
        "model": model,
        "X": X,
        "y": y,
        "X_test": X_test,
        "y_test": y_test,
        "idx_test": list(idx_test),
        "task_type": task_type,
        "score": score,  # accuracy for classification, RMSE for regression
        "target": target,
    }
    _MODEL_CACHE[dataset_key] = result
    return result


def predict_row(dataset_key: str, row_index: int):
    """Predict the target value for a specific row (by DataFrame index)."""
    info = _train(dataset_key)
    row = info["X"].loc[[row_index]]
    pred = info["model"].predict(row)[0]
    return pred


def actual_value(dataset_key: str, row_index: int):
    """Ground-truth target value for a specific row."""
    info = _train(dataset_key)
    return info["y"].loc[row_index]


def model_score(dataset_key: str):
    """Held-out test score: accuracy for classification, RMSE for regression."""
    info = _train(dataset_key)
    return info["task_type"], round(float(info["score"]), 4)


def sample_test_indices(dataset_key: str, n: int = 5):
    """A handful of held-out row indices, for building prediction questions."""
    info = _train(dataset_key)
    return info["idx_test"][:n]
