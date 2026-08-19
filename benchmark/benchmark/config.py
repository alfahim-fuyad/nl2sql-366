"""
config.py — dataset & path configuration for the benchmark.
"""

import os


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATASETS_DIR = os.path.join(
    BASE_DIR,
    "datasets"
)

REPORT_DIR = os.path.join(
    BASE_DIR,
    "report"
)

DB_PATH = os.path.join(
    BASE_DIR,
    "benchmark.db"
)

QUESTIONS_PATH = os.path.join(
    BASE_DIR,
    "questions.json"
)

LATEST_REPORT_PATH = os.path.join(
    REPORT_DIR,
    "latest.json"
)

RANDOM_STATE = 42


# ============================================================
# DATASETS
# ============================================================

DATASETS = {

    "dengue": {
        "csv": "dengue.csv",
        "table": "dengue",
    },

    "diabetes": {
        "csv": "diabetes_prediction_dataset.csv",
        "table": "diabetes",
    },

    "ecommerce": {
        "csv": "E-commerce.csv",
        "table": "ecommerce",
    },

    "employee": {
        "csv": "Employee Dataset.csv",
        "table": "employee",
    },

    "housing": {
        "csv": "Housing.csv",
        "table": "housing",
    },

    "student_performance": {
        "csv": "Student_performance.csv",
        "table": "student_performance",
    },
}


# ============================================================
# ML TASK CONFIGURATION
# ============================================================

ML_TASKS = {

    "dengue": {
        "target": "Outcome",
        "task_type": "classification",
        "drop_cols": [],
    },

    "diabetes": {
        "target": "diabetes",
        "task_type": "classification",
        "drop_cols": [],
    },

    "ecommerce": {
        "target": "Purchase Amount (USD)",
        "task_type": "regression",
        "drop_cols": [],
    },

    "employee": {
        "target": "Performance Rating",
        "task_type": "classification",
        "drop_cols": [
            "Employee Name",
            "Last Working Day",
        ],
    },

    "housing": {
        "target": "price",
        "task_type": "regression",
        "drop_cols": [],
    },

    "student_performance": {
        "target": "GradeClass",
        "task_type": "classification",
        "drop_cols": [
            "StudentID",
            "GPA",
        ],
    },
}