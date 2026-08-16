# nl2sql-366 benchmark results

Generated on **2026-08-16T20:01:19Z** by `python benchmark/run_benchmark.py`.
The benchmark contains 100 queries over five deterministic, previously unseen single-table schemas (20 per domain).

## Method comparison

| Method | Intent accuracy | Execution accuracy | Execution F1 | Valid SQL |
|---|---:|---:|---:|---:|
| Rule-based intent baseline | 86.00% | 96.00% | 0.960 | 100.00% |
| TF-IDF + Naive Bayes only | 90.00% | 100.00% | 1.000 | 100.00% |
| Proposed hybrid | 100.00% | 100.00% | 1.000 | 100.00% |

Execution accuracy requires matching the gold result columns and rows; ordering is checked for ranking queries and ignored for unordered SQL results. Execution F1 is the mean row-level F1 across queries.

## Cross-domain hybrid results

| Domain | Queries | Execution accuracy | Execution F1 |
|---|---:|---:|---:|
| Students | 20 | 100.00% | 1.000 |
| Employees | 20 | 100.00% | 1.000 |
| Healthcare | 20 | 100.00% | 1.000 |
| Sales | 20 | 100.00% | 1.000 |
| Sports | 20 | 100.00% | 1.000 |

## Query-category results

| Category | Queries | Hybrid execution accuracy |
|---|---:|---:|
| And Filter | 5 | 100.00% |
| Avg | 5 | 100.00% |
| Between | 5 | 100.00% |
| Categorical | 10 | 100.00% |
| Comparison | 5 | 100.00% |
| Count | 5 | 100.00% |
| Filtered Aggregate | 10 | 100.00% |
| Filtered Count | 5 | 100.00% |
| Group By | 20 | 100.00% |
| Max | 5 | 100.00% |
| Min | 5 | 100.00% |
| Order Limit | 10 | 100.00% |
| Select | 5 | 100.00% |
| Sum | 5 | 100.00% |

## Final intent-classifier holdout

- Dataset: `training_data/intent_dataset.csv`
- Examples: 100,000 (80,000 train / 20,000 test)
- Accuracy: **99.48%**
- Weighted precision: **99.49%**
- Weighted recall: **99.48%**
- Weighted F1: **99.47%**

Confusion-matrix label order: AVG, COUNT, MAX, MIN, SELECT, SUM

## Ablation

| Variant | Queries | Correct | Execution accuracy |
|---|---:|---:|---:|
| Hybrid | 100 | 100 | 100.00% |
| Hybrid Without Synonyms | 100 | 100 | 100.00% |

## Security validation

8/8 validator cases passed (100.00%). Unsafe statements, unknown columns/tables, and multiple statements are expected to be rejected; a safe SELECT is the positive control.

## Latency

| Stage | Mean (ms) | Median (ms) | P95 (ms) |
|---|---:|---:|---:|
| Tokenization | 0.348 | 0.280 | 0.582 |
| Intent Detection | 1.668 | 1.502 | 2.531 |
| Attribute Value Matching | 1.214 | 1.035 | 2.368 |
| Sql Generation | 0.010 | 0.009 | 0.015 |
| Validation | 0.068 | 0.059 | 0.132 |
| Execution | 0.361 | 0.320 | 0.526 |
| Total | 3.670 | 3.304 | 5.401 |

> These measurements are local SQLite timings on the Replit development environment; they are not a deployment or hardware-independent performance guarantee.
