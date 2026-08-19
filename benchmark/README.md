# NL2SQL-366 Benchmark Framework

A rigorous, research-grade benchmarking system for evaluating the NL2SQL-366 natural language to SQL conversion pipeline. The benchmark compares **execution results** (not SQL strings) to determine correctness.

## Design Philosophy

The primary evaluation metric is **result-set equivalence**: two SQL queries are considered equivalent if they produce the same normalized database result, regardless of syntactic differences. For example:

```sql
-- Reference SQL
SELECT AVG(salary) FROM employees;

-- Generated SQL (different string, same result → CORRECT)
SELECT AVG("salary") FROM employees;
```

## Quick Start

```bash
cd /path/to/nl2sql-366
python benchmark/run_benchmark.py
```

This single command:

1. Loads all 6 datasets into an SQLite database
2. Loads the NL2SQL intent classification model
3. Executes all 180 reference SQL queries (ground truth)
4. Runs each natural language query through the full NL2SQL-366 pipeline
5. Validates, executes, and compares generated SQL results
6. Computes all metrics (accuracy, F1, precision, recall, etc.)
7. Saves CSV, JSON, and Markdown reports
8. Generates publication-quality charts

## Output Directory

After running, all outputs are in `benchmark/output/`:

```
benchmark/output/
├── benchmark_queries.csv        # Input: all benchmark queries
├── benchmark_results.csv        # Per-query results (16 columns)
├── benchmark_summary.json       # Machine-readable metrics
├── benchmark_report.md          # Full Markdown report with charts
├── chart_intent_accuracy.png    # Intent classification accuracy
├── chart_result_match.png       # Result match accuracy by intent
├── chart_overall_metrics.png    # Overall metric comparison
├── chart_error_distribution.png # Error category breakdown
├── chart_dataset_accuracy.png   # Per-dataset accuracy
├── chart_pipeline_funnel.png    # Pipeline stage pass rates
└── benchmark.db                 # SQLite database used for execution
```

## Evaluation Pipeline

For every benchmark query:

```
Natural Language Query
    ↓
Reference SQL (ground truth)
    ↓
Execute on Database → Reference Result

---

Natural Language Query
    ↓
NL2SQL-366 Pipeline:
    1. Intent Detection (ML + rule overrides)
    2. Schema/Attribute Matching (fuzzy matching)
    3. Operator/Value Detection
    4. SQL Generation
    5. SQL Validation
    6. SQL Execution → Generated Result

---

Reference Result vs Generated Result
    ↓
Result Normalization (ordering, precision, NULLs)
    ↓
Set-based Comparison → Pass/Fail
```

## Metrics Computed

| Metric | Description |
|--------|-------------|
| Intent Classification Accuracy | Correct intent prediction rate |
| SQL Validity Rate | Percentage of generated SQL that passes validation |
| SQL Execution Success Rate | Percentage that executes without error |
| Result Match Accuracy | Primary metric: generated result equals reference result |
| Exact SQL Match Rate | String-identical SQL (strict) |
| Macro F1 | Weighted F1 score across all intent types |
| Precision / Recall / F1 per intent | Binary classification metrics per intent |
| Average SQL Generation Time | Latency of the SQL generation step |
| Average Execution Time | Latency of SQL execution |

## Result Normalization

The comparator handles:

- **Row ordering**: Preserved for ORDER BY queries; sorted for order-insensitive queries
- **Numeric precision**: Floats rounded to 6 decimal places; integers compared exactly
- **Floating-point tolerance**: Relative tolerance of 1e-6 for near-equal floats
- **NULL values**: NULL == NULL (both sides must be NULL to match)
- **Empty results**: Two empty result sets are considered matching
- **Type coercion**: Strings that parse as numbers are compared numerically

## Datasets

| Dataset | Rows | Domain | Table Name |
|---------|------|--------|------------|
| Housing | 545 | Real estate | `housing` |
| Student Performance | 2,392 | Education | `student_performance` |
| Diabetes Prediction | 100,000 | Healthcare | `diabetes_prediction_dataset` |
| Dengue | 1,000 | Healthcare | `dengue` |
| Employee | 25 | HR | `employee_dataset` |
| E-commerce | 10,000 | Retail | `ecommerce_dataset` |

## Benchmark Query Distribution

- **Total SQL queries**: 180
- **Queries per dataset**: 30
- **Intent distribution**: SELECT (83), AVG (34), COUNT (25), MAX (14), MIN (11), SUM (13)
- **Query complexity**: Simple filters, aggregate queries, GROUP BY with ORDER BY, multi-condition WHERE clauses, BETWEEN ranges, ranking with LIMIT

## Latest Benchmark Results (v3)

| Metric | Score |
|--------|-------|
| Total Queries | 180 |
| Intent Accuracy | 80.00% |
| Valid SQL | 93.89% |
| Execution Success | 93.89% |
| Result Match Accuracy | 50.00% |
| Macro F1 | 65.84% |
| Passed | 90 / 180 |
| Avg SQL Generation Time | 0.01 ms |
| Avg Execution Time | 4.73 ms |
| Total Runtime | 10.48 s |

### Per-Intent Breakdown

| Intent | Queries | Intent Acc. | Result Match | Valid SQL |
|--------|---------|-------------|--------------|-----------|
| AVG | 34 | 100.00% | 67.65% | 91.18% |
| COUNT | 25 | 80.00% | 36.00% | 88.00% |
| MAX | 14 | 100.00% | 64.29% | 92.86% |
| MIN | 11 | 100.00% | 63.64% | 90.91% |
| SELECT | 83 | 62.65% | 42.17% | 100.00% |
| SUM | 13 | 100.00% | 53.85% | 76.92% |

### Per-Dataset Breakdown

| Dataset | Queries | Result Match | Intent Acc. |
|---------|---------|--------------|-------------|
| housing_dataset | 30 | 70.00% | 100.00% |
| ecommerce_dataset | 30 | 56.67% | 70.00% |
| diabetes_prediction_dataset | 30 | 53.33% | 73.33% |
| dengue_dataset | 30 | 46.67% | 63.33% |
| student_performance_dataset | 30 | 43.33% | 80.00% |
| employee_dataset | 30 | 30.00% | 93.33% |

### Error Distribution

| Error Category | Count |
|----------------|-------|
| intent_error | 36 |
| result_mismatch | 46 |
| sql_validation_error | 8 |

## File Descriptions

### `run_benchmark.py`
Main entry point. Orchestrates the entire benchmark pipeline: dataset loading, NL2SQL pipeline execution, result comparison, metric computation, and output generation.

### `result_comparator.py`
Implements robust result-set comparison. Handles value normalization, order-sensitive vs order-insensitive comparison, and failure classification.

### `metrics.py`
Computes all evaluation metrics: overall, per-intent, per-dataset, F1 scores, and error analysis. Also provides terminal-friendly summary formatting.

### `generate_charts.py`
Generates 6 publication-quality matplotlib charts for the benchmark report.

### `benchmark/` (existing package)
Preserved from the original project. Contains `config.py`, `dataset_loader.py`, `sql_executor.py`, and the `datasets/` directory with CSV files.

## Reproducibility

The benchmark is fully deterministic:

- No random processes in SQL execution
- No data leakage (benchmark queries are not used for training)
- Reference SQL is never modified during evaluation
- Same input always produces the same output

## Research Integrity Notes

- **Primary metric**: Result match accuracy (execution-based), not SQL string similarity
- **Exact SQL match** is reported separately but is not the primary metric
- **Intent accuracy**, **SQL validity**, and **execution success** are reported as intermediate metrics
- The system honestly reports its limitations — the `student_performance` dataset exposes the system's difficulty with encoded integer values (Gender=1, Ethnicity=0) that don't have natural language descriptors in the query text

## Change Log

### v3 — Benchmark Restructuring (50.00% Result Match)

Restructured the benchmark to use six real-world datasets and 180 reference SQL queries with normalized, executable SQL throughout. Key changes:

| Change | Description | Impact |
|--------|-------------|--------|
| Dataset swap | Replaced `temp_and_rain` (CSV missing) with `diabetes_prediction_dataset` (100k rows, healthcare) | 30 new queries |
| Column cleaning | Aggressive column-name normalization strips `$`, `(`, `)`, `.`, collapses underscores | Resolves 12 reference errors in E-commerce |
| Reference SQL fixes | All 180 reference SQLs now use canonical table names and properly double-quoted identifiers | All 180 queries execute cleanly |
| Dataset aliases | Case-insensitive alias resolution supports `Employee Dataset`, `E-commerce`, `Housing`, etc. | Robust question-label handling |
| Table aliasing | Original CSV-stem table names registered as SQLite aliases alongside canonical names | Backward-compatible reference SQL |

**Result: 0/180 → 180/180 reference SQL queries execute successfully; 90/180 generated queries match the reference result.**

### v2 — Pipeline Optimization (55.35% Result Match on legacy 271-query benchmark)

Identified and fixed 8 root causes across 6 core modules using systematic failure analysis of 178 failed queries:

| Fix | Module | Description | Impact |
|-----|--------|-------------|--------|
| Comma number parsing | `value_matcher.py` | `"5,000,000"` → `5000000` | ~40 queries |
| Month name extraction | `value_matcher.py` | `"June"` → `6`, `"January"` → `1` | ~15 queries |
| Binary column patterns | `value_matcher.py` | `"have air conditioning"` → yes, `"without basement"` → no | ~15 queries |
| Domain-specific synonyms | `synonyms.json` | 80+ entries for 5 datasets (temperature→tem, rainfall→rain, etc.) | ~37 queries |
| Intent-aware agg column | `sql_generator.py` | `"highest average rainfall"` → AVG on rain, not Year | ~10 queries |
| GROUP BY on dimensions | `sql_generator.py` | Year/Month recognized as grouping dimensions | ~10 queries |
| Two-pass implicit filter | `sql_generator.py` | Numbers before AND after column ("have 2 parking") | ~12 queries |
| Operator fixes | `operators.json`, `intent_detector.py` | Removed false LIKE, improved SUM/SELECT intent | ~5 queries |

### v1 — Initial Benchmark (34.32% Result Match on legacy 271-query benchmark)

Baseline evaluation on 271 queries across 5 datasets.

## Dependencies

- Python 3.8+
- pandas
- scikit-learn (for loading the pre-trained intent model)
- rapidfuzz (used by the core attribute matcher)
- matplotlib (for chart generation)
- No additional dependencies beyond what the original project requires
