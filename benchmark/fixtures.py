"""Deterministic cross-domain datasets and a 100-query evaluation manifest.

The benchmark deliberately uses schemas and values that are not present in the
intent-training corpus.  Gold SQL is used only to compute execution accuracy;
the system under test never sees it.
"""

from __future__ import annotations


DATASETS = {
    "students": [
        {"Student": "Amina", "Age": 20, "Gender": "Female", "Department": "CSE", "District": "Dhaka", "GPA": 3.4, "Attendance": 90},
        {"Student": "Bashir", "Age": 22, "Gender": "Male", "Department": "EEE", "District": "Sylhet", "GPA": 3.8, "Attendance": 85},
        {"Student": "Chaya", "Age": 24, "Gender": "Female", "Department": "CSE", "District": "Dhaka", "GPA": 3.1, "Attendance": 75},
        {"Student": "Dipto", "Age": 21, "Gender": "Male", "Department": "BBA", "District": "Chittagong", "GPA": 3.6, "Attendance": 95},
        {"Student": "Esha", "Age": 23, "Gender": "Female", "Department": "EEE", "District": "Rajshahi", "GPA": 3.9, "Attendance": 88},
        {"Student": "Fahim", "Age": 26, "Gender": "Male", "Department": "CSE", "District": "Khulna", "GPA": 2.9, "Attendance": 70},
        {"Student": "Gita", "Age": 19, "Gender": "Female", "Department": "BBA", "District": "Dhaka", "GPA": 3.2, "Attendance": 92},
        {"Student": "Hasan", "Age": 25, "Gender": "Male", "Department": "EEE", "District": "Sylhet", "GPA": 3.5, "Attendance": 80},
    ],
    "employees": [
        {"Employee": "Arif", "Age": 28, "Gender": "Male", "Department": "Engineering", "City": "Dhaka", "Salary": 72000, "Years_Experience": 4},
        {"Employee": "Bela", "Age": 35, "Gender": "Female", "Department": "HR", "City": "Sylhet", "Salary": 68000, "Years_Experience": 9},
        {"Employee": "Chandan", "Age": 42, "Gender": "Male", "Department": "Sales", "City": "Dhaka", "Salary": 85000, "Years_Experience": 15},
        {"Employee": "Dalia", "Age": 31, "Gender": "Female", "Department": "Engineering", "City": "Rajshahi", "Salary": 91000, "Years_Experience": 7},
        {"Employee": "Emon", "Age": 26, "Gender": "Male", "Department": "HR", "City": "Chittagong", "Salary": 55000, "Years_Experience": 2},
        {"Employee": "Faria", "Age": 39, "Gender": "Female", "Department": "Sales", "City": "Dhaka", "Salary": 79000, "Years_Experience": 12},
        {"Employee": "Gopal", "Age": 24, "Gender": "Male", "Department": "Engineering", "City": "Khulna", "Salary": 61000, "Years_Experience": 1},
        {"Employee": "Hena", "Age": 45, "Gender": "Female", "Department": "HR", "City": "Sylhet", "Salary": 74000, "Years_Experience": 18},
    ],
    "healthcare": [
        {"Patient": "P01", "Age": 34, "Gender": "Female", "District": "Dhaka", "Diagnosis": "Diabetes", "BMI": 27.4, "Cholesterol": 210},
        {"Patient": "P02", "Age": 58, "Gender": "Male", "District": "Sylhet", "Diagnosis": "Hypertension", "BMI": 31.2, "Cholesterol": 245},
        {"Patient": "P03", "Age": 46, "Gender": "Female", "District": "Dhaka", "Diagnosis": "Asthma", "BMI": 23.8, "Cholesterol": 180},
        {"Patient": "P04", "Age": 67, "Gender": "Male", "District": "Chittagong", "Diagnosis": "Diabetes", "BMI": 29.6, "Cholesterol": 230},
        {"Patient": "P05", "Age": 29, "Gender": "Female", "District": "Rajshahi", "Diagnosis": "Asthma", "BMI": 21.5, "Cholesterol": 165},
        {"Patient": "P06", "Age": 52, "Gender": "Male", "District": "Dhaka", "Diagnosis": "Hypertension", "BMI": 33.1, "Cholesterol": 260},
        {"Patient": "P07", "Age": 41, "Gender": "Female", "District": "Khulna", "Diagnosis": "Diabetes", "BMI": 26.7, "Cholesterol": 205},
        {"Patient": "P08", "Age": 73, "Gender": "Male", "District": "Sylhet", "Diagnosis": "Asthma", "BMI": 28.3, "Cholesterol": 195},
    ],
    "sales": [
        {"Product": "Laptop", "Category": "Electronics", "Region": "North", "Salesperson": "Nadia", "Units": 12, "Revenue": 14400, "Discount": 5},
        {"Product": "Phone", "Category": "Electronics", "Region": "South", "Salesperson": "Rafi", "Units": 35, "Revenue": 21000, "Discount": 10},
        {"Product": "Desk", "Category": "Furniture", "Region": "East", "Salesperson": "Nadia", "Units": 8, "Revenue": 6400, "Discount": 0},
        {"Product": "Chair", "Category": "Furniture", "Region": "West", "Salesperson": "Sumi", "Units": 42, "Revenue": 8400, "Discount": 15},
        {"Product": "Tablet", "Category": "Electronics", "Region": "North", "Salesperson": "Rafi", "Units": 18, "Revenue": 12600, "Discount": 5},
        {"Product": "Monitor", "Category": "Electronics", "Region": "East", "Salesperson": "Sumi", "Units": 25, "Revenue": 10000, "Discount": 8},
        {"Product": "Sofa", "Category": "Furniture", "Region": "South", "Salesperson": "Nadia", "Units": 6, "Revenue": 18000, "Discount": 12},
        {"Product": "Printer", "Category": "Electronics", "Region": "West", "Salesperson": "Rafi", "Units": 15, "Revenue": 7500, "Discount": 3},
    ],
    "sports": [
        {"Player": "Ayan", "Team": "Tigers", "Country": "Bangladesh", "Sport": "Football", "Age": 22, "Score": 88, "Wins": 12},
        {"Player": "Borna", "Team": "Eagles", "Country": "India", "Sport": "Cricket", "Age": 27, "Score": 91, "Wins": 15},
        {"Player": "Cyrus", "Team": "Tigers", "Country": "Bangladesh", "Sport": "Cricket", "Age": 29, "Score": 84, "Wins": 10},
        {"Player": "Dipa", "Team": "Lions", "Country": "Nepal", "Sport": "Football", "Age": 24, "Score": 79, "Wins": 8},
        {"Player": "Emon", "Team": "Eagles", "Country": "Pakistan", "Sport": "Hockey", "Age": 31, "Score": 86, "Wins": 11},
        {"Player": "Faria", "Team": "Lions", "Country": "Bangladesh", "Sport": "Football", "Age": 26, "Score": 93, "Wins": 14},
        {"Player": "Gopal", "Team": "Tigers", "Country": "India", "Sport": "Hockey", "Age": 20, "Score": 76, "Wins": 7},
        {"Player": "Hira", "Team": "Lions", "Country": "Nepal", "Sport": "Cricket", "Age": 28, "Score": 89, "Wins": 13},
    ],
}


def _case(question, intent, gold_sql, category):
    return {
        "question": question,
        "expected_intent": intent,
        "gold_sql": gold_sql,
        "category": category,
    }


def _common_cases(
    noun,
    group_col,
    numeric,
    secondary_numeric,
    categorical_col,
    categorical_value,
    group_value,
    binary_col,
    binary_value,
):
    table = '"data"'
    return [
        _case(f"show all {noun}", "SELECT", f"SELECT * FROM {table}", "select"),
        _case(f"how many {noun}", "COUNT", f"SELECT COUNT(*) FROM {table}", "count"),
        _case(f"average {numeric}", "AVG", f'SELECT AVG("{numeric}") FROM {table}', "avg"),
        _case(f"maximum {numeric}", "MAX", f'SELECT MAX("{numeric}") FROM {table}', "max"),
        _case(f"minimum {secondary_numeric}", "MIN", f'SELECT MIN("{secondary_numeric}") FROM {table}', "min"),
        _case(f"total {numeric}", "SUM", f'SELECT SUM("{numeric}") FROM {table}', "sum"),
        _case(f"average {numeric} by {group_col}", "AVG", f'SELECT "{group_col}", AVG("{numeric}") AS "avg_{numeric.lower()}" FROM {table} GROUP BY "{group_col}"', "group_by"),
        _case(f"count {noun} by {group_col}", "COUNT", f'SELECT "{group_col}", COUNT(*) FROM {table} GROUP BY "{group_col}"', "group_by"),
        _case(f"top 2 highest {numeric}", "SELECT", f'SELECT * FROM {table} ORDER BY "{numeric}" DESC LIMIT 2', "order_limit"),
        _case(f"bottom 2 lowest {secondary_numeric}", "SELECT", f'SELECT * FROM {table} ORDER BY "{secondary_numeric}" ASC LIMIT 2', "order_limit"),
        _case(f"show {noun} where {secondary_numeric} between 20 and 40", "SELECT", f'SELECT * FROM {table} WHERE "{secondary_numeric}" BETWEEN 20 AND 40', "between"),
        _case(f"show {noun} where {secondary_numeric} over 25", "SELECT", f'SELECT * FROM {table} WHERE "{secondary_numeric}" > 25', "comparison"),
        _case(f"show {noun} where {categorical_col} is {categorical_value}", "SELECT", f'''SELECT * FROM {table} WHERE "{categorical_col}" = '{categorical_value}' '''.strip(), "categorical"),
        _case(f"show {noun} where {binary_col} is {binary_value}", "SELECT", f'''SELECT * FROM {table} WHERE "{binary_col}" = '{binary_value}' '''.strip(), "categorical"),
        _case(f"total {numeric} by {group_col}", "SUM", f'SELECT "{group_col}", SUM("{numeric}") AS "sum_{numeric.lower()}" FROM {table} GROUP BY "{group_col}"', "group_by"),
        _case(f"maximum {numeric} where {categorical_col} is {categorical_value}", "MAX", f'''SELECT MAX("{numeric}") FROM {table} WHERE "{categorical_col}" = '{categorical_value}' '''.strip(), "filtered_aggregate"),
        _case(f"how many {noun} where {group_col} is {group_value}", "COUNT", f'''SELECT COUNT(*) FROM {table} WHERE "{group_col}" = '{group_value}' '''.strip(), "filtered_count"),
        _case(f"average {numeric} where {binary_col} is {binary_value}", "AVG", f'''SELECT AVG("{numeric}") FROM {table} WHERE "{binary_col}" = '{binary_value}' '''.strip(), "filtered_aggregate"),
        _case(f"show {noun} where {secondary_numeric} over 25 and {categorical_col} is {categorical_value}", "SELECT", f'''SELECT * FROM {table} WHERE "{categorical_col}" = '{categorical_value}' AND "{secondary_numeric}" > 25''', "and_filter"),
        _case(f"average {numeric} by {binary_col}", "AVG", f'SELECT "{binary_col}", AVG("{numeric}") AS "avg_{numeric.lower()}" FROM {table} GROUP BY "{binary_col}"', "group_by"),
    ]


QUERY_CASES = {
    "students": _common_cases(
        "students", "Department", "GPA", "Age", "District", "Dhaka",
        "CSE", "Gender", "Female"
    ),
    "employees": _common_cases(
        "employees", "Department", "Salary", "Age", "City", "Dhaka",
        "Engineering", "Gender", "Female"
    ),
    "healthcare": _common_cases(
        "patients", "Diagnosis", "BMI", "Age", "District", "Dhaka",
        "Diabetes", "Gender", "Female"
    ),
    "sales": _common_cases(
        "products", "Category", "Revenue", "Units", "Region", "North",
        "Electronics", "Category", "Electronics"
    ),
    "sports": _common_cases(
        "players", "Team", "Score", "Age", "Country", "Bangladesh",
        "Tigers", "Country", "Bangladesh"
    ),
}


def all_cases():
    """Return the manifest as ``(domain, case_id, case)`` tuples."""
    for domain, cases in QUERY_CASES.items():
        for index, case in enumerate(cases, start=1):
            yield domain, f"{domain}-{index:02d}", case