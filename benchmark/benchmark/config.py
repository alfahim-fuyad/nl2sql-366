"""
config.py — dataset & path configuration for the benchmark.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
REPORT_DIR = os.path.join(BASE_DIR, "report")
DB_PATH = os.path.join(BASE_DIR, "benchmark.db")
QUESTIONS_PATH = os.path.join(BASE_DIR, "questions.json")
LATEST_REPORT_PATH = os.path.join(REPORT_DIR, "latest.json")

RANDOM_STATE = 42

# Maps a logical dataset name -> (csv filename, sqlite table name)
DATASETS = {
    "housing": {
        "csv": "Housing.csv",
        "table": "housing",
    },
    "dengue": {
        "csv": "dengue.csv",
        "table": "dengue",
    },
    "temp_and_rain": {
        "csv": "Temp_and_rain.csv",
        "table": "temp_and_rain",
    },
    "student_performance": {
        "csv": "Student_performance.csv",
        "table": "student_performance",
    },
    "employee": {
        "csv": "Employee Dataset.csv",
        "table": "employee",
    },
}

# ML task configuration: which column to predict, and what kind of task it is.
ML_TASKS = {
    "housing": {
        "target": "price",
        "task_type": "regression",
        "drop_cols": [],
    },
    "dengue": {
        "target": "Outcome",
        "task_type": "classification",
        "drop_cols": [],
    },
    "temp_and_rain": {
        "target": "rain",
        "task_type": "regression",
        "drop_cols": [],
    },
    "student_performance": {
        "target": "GradeClass",
        "task_type": "classification",
        "drop_cols": ["StudentID", "GPA"],  # GPA leaks the target directly
    },
    "employee": {
        "target": "Performance Rating",
        "task_type": "classification",
        "drop_cols": ["Employee Name", "Last Working Day"],
    },
}
