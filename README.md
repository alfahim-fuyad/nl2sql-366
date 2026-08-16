# nl2sql-366 — Natural Language to SQL Query Generation System

A lightweight **Natural Language to SQL (NL2SQL)** system that converts plain-English questions into SQL queries for **single-table CSV/Excel datasets**. Users can upload a dataset, ask questions in English, and view the generated SQL and results without writing SQL manually.

---

## Overview

nl2sql-366 uses a **hybrid approach** combining **TF-IDF + Multinomial Naive Bayes** with rule-based techniques.

The system processes a question through several stages: intent detection, column matching, operator detection, value extraction, SQL generation, validation, and execution. This compositional design keeps the system modular, transparent, and easy to evaluate.

The schema of an uploaded dataset is detected automatically, allowing the same system to work across different single-table CSV/Excel datasets within its supported query capabilities.

**Live demo:** [nl2sql-366 on Render](https://nl2sql-366.onrender.com/)

---

## Features

* Upload CSV/Excel datasets with automatic schema detection
* Six query types: `SELECT`, `COUNT`, `AVG`, `MAX`, `MIN`, `SUM`
* `GROUP BY` aggregation
* `ORDER BY + LIMIT` ranking
* `BETWEEN` range filters
* Multiple `AND`-connected conditions
* 300+ domain synonym mappings
* Fuzzy column matching with underscore-to-space normalization
* Natural-language operator detection
* Numeric and categorical value matching
* SQL safety and schema-level validation
* Flask web UI with drag-and-drop upload
* SQLite for local execution
* PostgreSQL for production

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

The repository includes a reproducible **100-query benchmark** using **five previously unseen single-table domains**:

* Students — 20 queries
* Employees — 20 queries
* Healthcare — 20 queries
* Sales — 20 queries
* Sports — 20 queries

**Total: 100 natural-language queries.**

The benchmark covers all six supported intents, grouped aggregation, ordering and limits, range filters, categorical filters, and `AND`-connected conditions.

Execution accuracy is measured by comparing the results of generated SQL with the results of gold SQL queries rather than by comparing SQL strings alone.

### Latest Results

| Method                     | Intent Accuracy | Execution Accuracy | Execution F1 | Valid SQL   |
| -------------------------- | --------------- | ------------------ | ------------ | ----------- |
| Rule-based intent baseline | 86.00%          | 96.00%             | 0.960        | 100.00%     |
| TF-IDF + Naive Bayes only  | 90.00%          | 100.00%            | 1.000        | 100.00%     |
| **Proposed Hybrid**        | **100.00%**     | **100.00%**        | **1.000**    | **100.00%** |

The proposed hybrid achieved **100% execution accuracy across all five benchmark domains**.

The intent classifier was independently evaluated on a **20,000-example holdout set** from the 100,000-example intent dataset:

| Metric             | Result     |
| ------------------ | ---------- |
| Accuracy           | **99.48%** |
| Weighted Precision | **99.49%** |
| Weighted Recall    | **99.48%** |
| Weighted F1        | **99.47%** |

### Security & Latency

* SQL validator: **8/8 security/correctness cases passed**
* Mean end-to-end latency: **3.524 ms**
* Median latency: **3.326 ms**
* P95 latency: **5.023 ms**

The validator tests included rejection of `DROP`, `DELETE`, `UPDATE`, `INSERT`, unknown columns, unknown tables, and multiple statements.

Latency values were measured on the local SQLite/Replit development environment and are **environment-specific measurements, not hardware-independent guarantees**.

### Synonym Ablation

Removing the synonym dictionary still resulted in **100/100** on this benchmark because the benchmark questions explicitly use the schema attributes.

Therefore, this result does **not** show that the synonym dictionary is unnecessary. A dedicated synonym-focused challenge set would provide a stronger evaluation.

Run the benchmark with:

```bash
python benchmark/run_benchmark.py
```

Results are written to:

```text
benchmark/results/latest.json
benchmark/results/latest.md
```

---

## Project Structure

```text
nl2sql-366/
├── app.py                        # Flask web server
├── main.py                       # Interactive CLI
│
├── core/
│   ├── attribute_matcher.py      # Fuzzy column name matching
│   ├── dataset_loader.py         # CSV → SQLite / PostgreSQL
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
│   ├── operators.json
│   ├── stopwords.json
│   └── synonyms.json
│
├── models/
│   ├── intent_model.pkl
│   ├── vectorizer.pkl
│   └── train_intent.py
│
├── training_data/
│   ├── intent_dataset.csv        # 100,000 labelled examples
│   ├── generate_dataset.py
│   └── convert_wikisql.py
│
├── tests/
│   ├── conftest.py
│   ├── test_dataset_and_schema.py
│   ├── test_matchers.py
│   ├── test_sql_generation_and_execution.py
│   ├── test_tokenizer_and_operator.py
│   └── test_validator.py
│
├── benchmark/
│   ├── fixtures.py
│   ├── run_benchmark.py
│   ├── generated_datasets/
│   └── results/
│
├── templates/
│   ├── index.html
│   └── partials/
│       ├── navbar.html
│       ├── about_modal.html
│       ├── help_modal.html
│       ├── upload_card.html
│       ├── preview_card.html
│       └── query_card.html
│
├── static/
│   ├── css/
│   ├── images/
│   └── js/
│
├── data/
│   └── sample.csv
│
├── simulation.html
├── requirements.txt
├── Procfile
└── render.yaml
```

---

## Technology Stack

| Technology          | Purpose                        |
| ------------------- | ------------------------------ |
| Python 3.8+         | Core language                  |
| Flask               | Web framework                  |
| pandas              | Dataset loading and processing |
| SQLite / PostgreSQL | Query execution                |
| scikit-learn        | TF-IDF + Naive Bayes           |
| RapidFuzz           | Fuzzy column matching          |
| SQLAlchemy          | PostgreSQL persistence         |
| pytest              | Automated testing              |

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

Pre-trained `.pkl` files are already included. Retraining is only necessary when the training data or training configuration changes.

### 3. Run the web app

```bash
python3 app.py
```

Open:

```text
http://localhost:5000
```

### 4. Or run the CLI

```bash
python3 main.py
```

---

## Running Tests

```bash
pytest tests/
```

The current test suite contains **35 unit and integration tests** covering dataset loading, schema processing, matching, tokenization, SQL generation, execution, and validation.

---

## Deployment — Render + Neon

The project is configured for deployment on [Render](https://render.com/) with [Neon](https://neon.tech/) PostgreSQL.

1. Create a Render web service from this repository.
2. Set `DATABASE_URL` to your Neon PostgreSQL connection string.
3. Set `SESSION_SECRET` to a random secret.
4. Render starts the application using the `Procfile`.

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

The repository includes the main artifacts required to reproduce the reported evaluation:

* 100,000-example intent dataset
* Trained model artifacts
* Model training scripts
* WikiSQL conversion script
* Deterministic benchmark fixtures
* 100-query benchmark
* Benchmark execution script
* Per-query JSON results
* Unit and integration tests

Run the benchmark with:

```bash
python benchmark/run_benchmark.py
```

Results are written to:

```text
benchmark/results/latest.json
benchmark/results/latest.md
```

---

## License

This project was developed as part of the **CSE366 (Artificial Intelligence)** course at **East West University**.
