# nl2sql-366 — Natural Language to SQL Query Generation System

A Natural Language to SQL (nl2sql-366) system that converts plain English questions into SQL queries for CSV/Excel datasets. Users can upload a CSV/Excel file, ask questions in English, and get results without writing SQL.

---

## Overview

nl2sql-366 uses a hybrid approach that combines Machine Learning (TF-IDF + Naive Bayes) with rule-based techniques. The system breaks a user's question into smaller parts, such as finding the intent, column names, operators, and values, and then combines them to generate the final SQL query. This follows a compositional approach, making the system simple, accurate, and easy to understand.

The system works with CSV/Excel datasets by automatically detecting their schema, so users can start querying immediately without changing the code.

**Live demo:** [nl2sql-366 on Render](https://nl2sql-366.onrender.com)

---

## Features

* Upload CSV or Excel (`.xlsx`) files with automatic schema detection
* Supports six query types: `SELECT`, `COUNT`, `AVG`, `MAX`, `MIN`, `SUM`
* `GROUP BY` aggregation: `"average salary by department"`
* `ORDER BY + LIMIT` ranking: `"top 5 highest salary"`
* `BETWEEN` range filters: `"age between 25 and 40"`
* 300+ domain synonym dictionary (students, employees, health, sales, sports, …)
* Fuzzy column matching with underscore-to-space normalization
* SQL injection prevention and schema-level validation
* Flask web UI with drag-and-drop CSV upload
* SQLite locally, PostgreSQL in production

---

## Example Queries

| Question                             | Generated SQL                                                          |
| ------------------------------------ | ---------------------------------------------------------------------- |
| `show female patients older than 30` | `SELECT * FROM "data" WHERE "Gender" = 'Female' AND "Age" > 30`        |
| `average salary by department`       | `SELECT "Department", AVG("Salary") FROM "data" GROUP BY "Department"` |
| `top 5 highest salary`               | `SELECT * FROM "data" ORDER BY "Salary" DESC LIMIT 5`                  |
| `how many students from Dhaka`       | `SELECT COUNT(*) FROM "data" WHERE "District" = 'Dhaka'`               |
| `total sales by region`              | `SELECT "Region", SUM("Sales") FROM "data" GROUP BY "Region"`          |

---

## Project Structure

```text
nl2sql-366/
├── app.py                        # Flask web server
├── main.py                       # Interactive CLI
│
├── core/
│   ├── attribute_matcher.py      # Fuzzy column name matching
│   ├── dataset_loader.py         # CSV/Excel → SQLite / PostgreSQL
│   ├── intent_detector.py        # ML intent classifier
│   ├── operator_detector.py      # NL phrase → SQL operator
│   ├── response.py               # CLI result formatter
│   ├── schema_reader.py          # DataFrame schema extraction
│   ├── sql_executor.py           # Query execution
│   ├── sql_generator.py          # Internal query → SQL string
│   ├── sql_validator.py          # Safety + correctness checks
│   ├── tokenizer.py              # Text cleaning utilities
│   └── value_matcher.py          # Number + categorical extraction
│
├── knowledge/
│   ├── operators.json            # NL phrase → SQL operator mapping
│   ├── stopwords.json            # Words to ignore during matching
│   └── synonyms.json             # Domain synonym dictionary (300+ entries)
│
├── models/
│   ├── intent_model.pkl          # Trained Naive Bayes classifier
│   ├── vectorizer.pkl            # Fitted TF-IDF vectorizer
│   └── train_intent.py           # Training script
│
├── training_data/
│   ├── intent_dataset.csv        # 100,000 labelled training examples
│   ├── generate_dataset.py       # Synthetic dataset generator
│   └── convert_wikisql.py        # WikiSQL → intent format converter
│
├── tests/
│   ├── conftest.py
│   ├── test_dataset_and_schema.py
│   ├── test_matchers.py
│   ├── test_sql_generation_and_execution.py
│   ├── test_tokenizer_and_operator.py
│   └── test_validator.py
│
├── templates/
│   ├── index.html                # Main web UI template
│   └── partials/
│       ├── navbar.html           # Top navbar + mobile hamburger menu
│       ├── about_modal.html      # "About" modal content
│       ├── help_modal.html       # "Help" modal content
│       ├── upload_card.html      # Drag & drop upload card
│       ├── preview_card.html     # Dataset preview table
│       └── query_card.html       # Question input + SQL/results display
│
├── favicon.svg
│
├── static/
│   ├── css/
│   │   ├── base.css              # Reset, body, container, header, card
│   │   ├── navbar.css            # Navbar + mobile hamburger menu
│   │   ├── modal.css             # Modal shell + About modal styling
│   │   ├── upload.css            # Drop zone, upload strip, data requirements
│   │   └── query-results.css     # Ask row, SQL output, results table, spinner
│   │
│   ├── images/
│   │   └── ewu-logo.png
│   │
│   └── js/
│       ├── dom.js                # Shared DOM element references
│       ├── utils.js              # Shared UI helpers (errors, escaping)
│       ├── upload.js             # Drag & drop / file upload logic
│       ├── query.js              # Ask question + render results
│       ├── navbar.js             # Logo reload + mobile hamburger menu
│       └── modals.js             # About/Help modal behavior
│
├── data/
│   └── sample.csv                # Sample dataset for testing
│
├── simulation.html               # Interactive pipeline visualizer (learning tool)
├── requirements.txt              # List of required Python packages
├── Procfile                      # Starts the Flask app on Render
└── render.yaml                   # Render deployment settings
```

Each CSS and JavaScript file has a single responsibility and is loaded directly by `templates/index.html`. No bundler or build step is required.

The Jinja partials in `templates/partials/` are `{% include %}`-ed by `index.html` and keep the page markup organized by section; they are not standalone routes.

---

## Technology Stack

| Technology          | Purpose                                          |
| ------------------- | ------------------------------------------------ |
| Python 3.8+         | Core language                                    |
| Flask               | Web framework                                    |
| pandas              | CSV loading and DataFrame operations             |
| SQLite / PostgreSQL | Query execution backend                          |
| scikit-learn        | TF-IDF vectorizer + Naive Bayes classifier       |
| RapidFuzz           | Fuzzy string matching for column name resolution |
| SQLAlchemy          | PostgreSQL persistence                           |
| pytest              | Test suite                                       |

---

## Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Train the Intent Model

```bash
python3 models/train_intent.py
```

The pre-trained `.pkl` files are already included, so this step is only needed if you want to retrain the model on updated data.

### 3. Run the Web App

```bash
python3 app.py
```

Open http://localhost:5000 in your browser.

### 4. Or Use the CLI

```bash
python3 main.py
```

---

## Running Tests

```bash
pytest tests/
```

All 33 tests should pass.

The test suite covers:

* Dataset loading and schema detection
* Attribute matching
* Fuzzy and synonym-based matching
* SQL generation and execution
* Tokenizer and operator detection
* SQL validation and safety checks

---

## Deployment (Render + Neon DB)

The project is configured for deployment on [Render](https://render.com) with a [Neon](https://neon.tech) PostgreSQL database.

1. Create a Render web service from this repository.
2. Set the `DATABASE_URL` environment variable to your Neon connection string.
3. Set `SESSION_SECRET` to a random secret string.
4. Render will run `gunicorn app:app` automatically via the `Procfile`.

---

## Pipeline Architecture

```text
User Question
      │
      ▼
Intent Detector      ← TF-IDF + Naive Bayes → SELECT / COUNT / AVG / MAX / MIN / SUM
      │
      ▼
Attribute Matcher    ← Fuzzy match + synonyms → column name(s)
      │
      ▼
Operator Detector    ← Phrase dictionary → SQL operator symbol (>, <, =, …)
      │
      ▼
Value Matcher        ← Regex (numbers) + schema sample lookup (categoricals)
      │
      ▼
SQL Generator        ← Internal query dict → SQL string (double-quoted identifiers)
      │
      ▼
SQL Validator        ← Safety check + schema column verification
      │
      ▼
SQL Executor         ← SQLite / PostgreSQL → (columns, rows)
      │
      ▼
Results
```

---

## Benchmark

The project includes a benchmark suite under `benchmark/` that evaluates the full NL2SQL pipeline on **180 reference SQL queries** across **6 real-world datasets** using **execution-based result-set equivalence** as the primary correctness metric rather than SQL string similarity.

### Datasets

| Dataset             | Rows    | Domain      | Table Name                    |
| ------------------- | ------- | ----------- | ----------------------------- |
| Housing             | 545     | Real estate | `housing`                     |
| Student Performance | 2,392   | Education   | `student_performance`         |
| Diabetes Prediction | 100,000 | Healthcare  | `diabetes_prediction_dataset` |
| Dengue              | 1,000   | Healthcare  | `dengue`                      |
| Employee            | 25      | HR          | `employee_dataset`            |
| E-commerce          | 10,000  | Retail      | `ecommerce_dataset`           |

### Running the Benchmark

```bash
python benchmark/run_benchmark.py
```

Outputs (CSV, JSON, Markdown report, 6 PNG charts, and the SQLite benchmark database) are written to `benchmark/output/`.

### Latest Results (v3)

| Metric                    | Score      |
| ------------------------- | ---------- |
| Total Queries             | 180        |
| Intent Accuracy           | 80.00%     |
| Valid SQL                 | 93.89%     |
| Execution Success         | 93.89%     |
| **Result Match Accuracy** | **50.00%** |
| Macro F1                  | 65.84%     |
| Passed                    | 90 / 180   |

See `benchmark/README.md` and `benchmark/output/benchmark_report.md` for the full per-intent and per-dataset breakdown, error analysis, and change log.

---

## Known Limitations

| Limitation        | Details                                                        |
| ----------------- | -------------------------------------------------------------- |
| OR / IN filters   | Only AND-connected conditions are supported                    |
| Nested conditions | Parenthesized logic like `(A OR B) AND C` is not supported     |
| JOINs             | Only single-table queries are supported                        |
| Date expressions  | Natural language dates such as `"last month"` are not resolved |
| Language          | English only                                                   |

---

## License

This project was developed as part of the **CSE366 (Artificial Intelligence)** course at **East West University**.
