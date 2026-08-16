# nl2sql-366 — Natural Language to SQL Query Generation System

A Natural Language to SQL (nl2sql-366) system that converts plain English questions into SQL queries for CSV/Excel datasets. Users can upload a CSV/Excel file, ask questions in English, and get results without writing SQL.

---

## Overview

nl2sql-366 uses a hybrid approach that combines Machine Learning (TF-IDF + Naive Bayes) with rule-based techniques. The system breaks a user's question into smaller parts, such as finding the intent, column names, operators, and values, and then combines them to generate the final SQL query. This follows a compositional approach, making the system simple, accurate, and easy to understand.

The system works with CSV/Excel datasets by automatically detecting their schema, so users can start querying immediately without changing the code within the supported query capabilities.

**Live demo:** [nl2sql-366 on Render](https://nl2sql-366.onrender.com)

---

## Features

* Upload CSV/Excel datasets with automatic schema detection
* Supports six query types: `SELECT`, `COUNT`, `AVG`, `MAX`, `MIN`, `SUM`
* `GROUP BY` aggregation: `"average salary by department"`
* `ORDER BY + LIMIT` ranking: `"top 5 highest salary"`
* `BETWEEN` range filters: `"age between 25 and 40"`
* Multiple `AND`-connected conditions
* 300+ domain synonym dictionary (students, employees, health, sales, sports, …)
* Fuzzy column matching with underscore-to-space normalization
* Natural-language operator detection
* Numeric and categorical value matching
* SQL injection prevention and schema-level validation
* Flask web UI with drag-and-drop CSV/Excel upload
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

## Benchmark & Evaluation

The project includes a reproducible **100-query benchmark** using five previously unseen single-table datasets:

* Students — 20 queries
* Employees — 20 queries
* Healthcare — 20 queries
* Sales — 20 queries
* Sports — 20 queries

**Total: 100 natural-language queries.**

The benchmark covers the six supported query types along with grouped aggregation, sorting and limits, range filters, categorical filters, and multiple `AND` conditions.

Execution accuracy is measured by running both the generated SQL and the corresponding gold SQL and comparing their results.

### Latest Results

| Method                     | Intent Accuracy | Execution Accuracy | Execution F1 |   Valid SQL |
| -------------------------- | --------------: | -----------------: | -----------: | ----------: |
| Rule-based intent baseline |          86.00% |             96.00% |        0.960 |     100.00% |
| TF-IDF + Naive Bayes only  |          90.00% |            100.00% |        1.000 |     100.00% |
| **Proposed Hybrid**        |     **100.00%** |        **100.00%** |    **1.000** | **100.00%** |

The proposed hybrid achieved **100% execution accuracy across all five benchmark datasets**.

The intent classifier was also tested separately on a **20,000-example holdout set** from the 100,000-example intent dataset:

| Metric             |     Result |
| ------------------ | ---------: |
| Accuracy           | **99.48%** |
| Weighted Precision | **99.49%** |
| Weighted Recall    | **99.48%** |
| Weighted F1        | **99.47%** |

### Security & Latency

* SQL validator: **8/8 security and correctness cases passed**
* Mean end-to-end latency: **3.524 ms**
* Median latency: **3.326 ms**
* P95 latency: **5.023 ms**

The validator checks include rejection of `DROP`, `DELETE`, `UPDATE`, `INSERT`, unknown columns, unknown tables, and multiple SQL statements.

Latency was measured in the local SQLite/Replit development environment. These numbers are environment-specific and should not be treated as hardware-independent performance guarantees.

### Synonym Dictionary Check

The synonym dictionary contains alternative words and phrases that can help match user questions with dataset columns.

For the current 100 benchmark queries, removing the synonym dictionary still produced **100/100 correct results**. This happened because the benchmark questions already use column names or terms that are close to the dataset schema.

Therefore, this benchmark does not fully test the synonym feature. A separate set of questions using different words for the same columns would be needed to properly evaluate synonym handling.

Run the benchmark with:

```bash
python benchmark/run_benchmark.py
```

The results are saved to:

```text
benchmark/results/latest.json
benchmark/results/latest.md
```

---

## Project Structure

```text
nl2sql-366/
├── app.py                        # Flask web application
├── main.py                       # Command-line interface
│
├── core/
│   ├── attribute_matcher.py      # Matches user words with dataset columns
│   ├── dataset_loader.py         # Loads CSV/Excel data into the database
│   ├── intent_detector.py        # Detects SELECT, COUNT, AVG, MAX, MIN, SUM
│   ├── operator_detector.py      # Detects operators such as >, <, =, BETWEEN
│   ├── response.py               # Formats CLI responses
│   ├── schema_reader.py          # Reads dataset columns and data types
│   ├── sql_executor.py           # Executes generated SQL queries
│   ├── sql_generator.py          # Builds SQL queries from detected information
│   ├── sql_validator.py          # Checks SQL safety and valid columns/tables
│   ├── tokenizer.py              # Cleans and tokenizes user questions
│   └── value_matcher.py          # Finds numeric and categorical values
│
├── knowledge/
│   ├── operators.json             # Natural-language operator mappings
│   ├── stopwords.json             # Common words ignored during matching
│   └── synonyms.json              # Domain-specific synonym mappings
│
├── models/
│   ├── intent_model.pkl           # Trained Naive Bayes model
│   ├── vectorizer.pkl             # Trained TF-IDF vectorizer
│   └── train_intent.py            # Script for training the intent model
│
├── training_data/
│   ├── intent_dataset.csv         # 100,000 labelled training examples
│   ├── generate_dataset.py        # Generates training examples
│   └── convert_wikisql.py         # Converts WikiSQL data to the required format
│
├── tests/
│   ├── conftest.py                # Shared pytest configuration
│   ├── test_dataset_and_schema.py # Dataset and schema tests
│   ├── test_matchers.py           # Column and value matching tests
│   ├── test_sql_generation_and_execution.py
│   ├── test_tokenizer_and_operator.py
│   └── test_validator.py          # SQL validation tests
│
├── benchmark/
│   ├── fixtures.py                # Benchmark datasets and test queries
│   ├── run_benchmark.py           # Runs the 100-query benchmark
│   ├── generated_datasets/        # Generated benchmark datasets
│   └── results/                   # Saved benchmark results
│
├── templates/
│   ├── index.html                 # Main web UI template
│   └── partials/
│       ├── navbar.html             # Top navbar and mobile menu
│       ├── about_modal.html        # About modal content
│       ├── help_modal.html         # Help modal content
│       ├── upload_card.html        # Drag-and-drop upload card
│       ├── preview_card.html       # Dataset preview table
│       └── query_card.html         # Question input and results display
│
├── static/
│   ├── css/
│   │   ├── base.css               # General page styling
│   │   ├── navbar.css             # Navbar styling
│   │   ├── modal.css              # Modal styling
│   │   ├── upload.css             # Upload section styling
│   │   └── query-results.css      # Query and result styling
│   │
│   ├── images/
│   │   └── ewu-logo.png           # East West University logo
│   │
│   └── js/
│       ├── dom.js                 # Shared DOM references
│       ├── utils.js               # Common frontend utilities
│       ├── upload.js              # File upload functionality
│       ├── query.js               # Question submission and result display
│       ├── navbar.js              # Navbar interactions
│       └── modals.js              # About and Help modal controls
│
├── data/
│   └── sample.csv                # Sample dataset for testing
│
├── favicon.svg                    # Browser favicon
├── simulation.html                # Interactive pipeline visualiser
├── requirements.txt               # Python dependencies
├── Procfile                      # Render start command
└── render.yaml                   # Render deployment configuration
```

The project is divided into separate modules so that dataset handling, question processing, SQL generation, validation, execution, and the web interface can be developed and maintained independently.

The CSS and JavaScript files are kept separate by responsibility and are loaded directly by `templates/index.html`, so no bundler or build step is required. The Jinja files inside `templates/partials/` are included by `index.html` to keep the page structure organized.

---

## Technology Stack

| Technology          | Purpose                                    |
| ------------------- | ------------------------------------------ |
| Python 3.8+         | Core language                              |
| Flask               | Web framework                              |
| pandas              | CSV/Excel loading and DataFrame operations |
| SQLite / PostgreSQL | Query execution backend                    |
| scikit-learn        | TF-IDF vectorizer + Naive Bayes classifier |
| RapidFuzz           | Fuzzy string matching for column names     |
| SQLAlchemy          | PostgreSQL persistence                     |
| pytest              | Automated testing                          |

---

## Getting Started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Train the intent model

```bash
python3 models/train_intent.py
```

The pre-trained `.pkl` files are already included, so this step is only needed if you want to retrain the model using updated data.

### 3. Run the web app

```bash
python3 app.py
```

Open:

```text
http://localhost:5000
```

### 4. Or use the CLI

```bash
python3 main.py
```

---

## Running Tests

```bash
pytest tests/
```

The current test suite contains **35 unit and integration tests** covering:

* Dataset loading
* Schema processing
* Column matching
* Value matching
* Tokenization
* Operator detection
* SQL generation
* SQL execution
* SQL validation

---

## Deployment — Render + Neon DB

The project is configured for deployment on [Render](https://render.com/) with a [Neon](https://neon.tech/) PostgreSQL database.

1. Create a Render web service from this repository.
2. Set the `DATABASE_URL` environment variable to your Neon connection string.
3. Set `SESSION_SECRET` to a random secret string.
4. Render will run the application using the `Procfile`.

---

## Pipeline Architecture

```text
User Question
      │
      ▼
Intent Detector      ← TF-IDF + Naive Bayes
      │
      ▼
Attribute Matcher    ← Fuzzy matching + synonyms
      │
      ▼
Operator Detector    ← Natural language → SQL operators
      │
      ▼
Value Matcher        ← Numbers + categorical values
      │
      ▼
SQL Generator        ← Internal query → SQL
      │
      ▼
SQL Validator        ← Safety + schema validation
      │
      ▼
SQL Executor         ← SQLite / PostgreSQL
      │
      ▼
Query Results
```

---

## Known Limitations

| Limitation        | Details                                                        |
| ----------------- | -------------------------------------------------------------- |
| OR / IN filters   | Only `AND`-connected conditions are supported                  |
| Nested conditions | `(A OR B) AND C` is not supported                              |
| JOINs             | Only single-table queries are supported                        |
| Date expressions  | Natural-language dates such as `"last month"` are not resolved |
| Language          | English queries only                                           |

---

## Reproducibility

The repository contains the files needed to run the same training and benchmark setup, including:

* 100,000-example intent dataset
* Trained model files
* Model training script
* WikiSQL conversion script
* Benchmark fixtures
* 100-query benchmark
* Benchmark runner
* Per-query benchmark results
* Unit and integration tests

To run the benchmark:

```bash
python benchmark/run_benchmark.py
```

Benchmark results are saved to:

```text
benchmark/results/latest.json
benchmark/results/latest.md
```

---

## License

This project was developed as part of the **CSE366 (Artificial Intelligence)** course at **East West University**.
