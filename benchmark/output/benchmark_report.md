# NL2SQL-366 Benchmark Report

**Generated:** 2026-08-18 18:02 UTC
**Total Runtime:** 5.06 seconds

## 1. Benchmark Overview

- **Total SQL Queries Evaluated:** 180
- **Number of Datasets/Schemas:** 6
- **Datasets:** dengue_dataset, ecommerce_dataset, employee_dataset, housing_dataset, student_performance_dataset, temp_and_rain_dataset
- **Queries per Dataset:** 30
- **Intent Distribution:**
  - AVG: 44 queries
  - COUNT: 69 queries
  - MAX: 17 queries
  - MIN: 16 queries
  - SELECT: 27 queries
  - SUM: 7 queries

## 2. Overall Results

| Metric | Score |
|--------|-------|
| Intent Accuracy | 79.44% |
| Valid SQL | 92.22% |
| Execution Success | 92.22% |
| Result Match Accuracy | 60.56% |
| Exact SQL Match | 0.00% |
| Macro F1 | 73.83% |
| Avg SQL Generation Time | 0.01 ms |
| Avg Execution Time | 0.96 ms |
| Total Passed | 109 |
| Total Failed | 71 |

![Overall Metrics](chart_overall_metrics.png)

### 2.1 Method Comparison

| Method | Description | Accuracy |
|--------|-------------|----------|
| Reference SQL | Ground-truth SQL executed directly | 100.00% |
| NL2SQL-366 | Natural language to SQL pipeline | 60.56% |

> Reference SQL is treated as ground truth. NL2SQL-366 is correct when generated SQL produces the same result as the reference SQL.

![Pipeline Funnel](chart_pipeline_funnel.png)

## 3. Per-Intent Results

| Intent | Queries | Intent Acc. | Result Match | Exact SQL | Valid SQL | Exec Success |
|--------|---------|-------------|--------------|-----------|-----------|-------------|
| AVG | 44 | 88.64% | 86.36% | 0.00% | 88.64% | 88.64% |
| COUNT | 69 | 71.01% | 47.83% | 0.00% | 97.10% | 97.10% |
| MAX | 17 | 88.24% | 70.59% | 0.00% | 94.12% | 94.12% |
| MIN | 16 | 93.75% | 75.00% | 0.00% | 93.75% | 93.75% |
| SELECT | 27 | 77.78% | 37.04% | 0.00% | 88.89% | 88.89% |
| SUM | 7 | 57.14% | 57.14% | 0.00% | 71.43% | 71.43% |

![Intent Accuracy](chart_intent_accuracy.png)

![Result Match by Intent](chart_result_match.png)

## 4. Per-Dataset Results

| Dataset | Queries | Intent Acc. | Result Match | Exact SQL |
|---------|---------|-------------|--------------|-----------|
| dengue_dataset | 30 | 100.00% | 80.00% | 0.00% |
| ecommerce_dataset | 30 | 46.67% | 46.67% | 0.00% |
| employee_dataset | 30 | 90.00% | 60.00% | 0.00% |
| housing_dataset | 30 | 90.00% | 73.33% | 0.00% |
| student_performance_dataset | 30 | 76.67% | 50.00% | 0.00% |
| temp_and_rain_dataset | 30 | 73.33% | 53.33% | 0.00% |

![Dataset Accuracy](chart_dataset_accuracy.png)

## 5. Precision, Recall, F1 by Intent

| Intent | Precision | Recall | F1 | Support |
|--------|-----------|--------|-----|---------|
| AVG | 100.00% | 86.36% | 92.68% | 44 |
| COUNT | 100.00% | 47.83% | 64.71% | 69 |
| MAX | 100.00% | 70.59% | 82.76% | 17 |
| MIN | 100.00% | 75.00% | 85.71% | 16 |
| SELECT | 100.00% | 37.04% | 54.05% | 27 |
| SUM | 100.00% | 57.14% | 72.73% | 7 |

## 6. Error Analysis

**Total Failed Queries:** 71

**Error Distribution:**

| Error Category | Count |
|----------------|-------|
| intent_error | 25 |
| reference_error | 12 |
| result_mismatch | 34 |

![Error Distribution](chart_error_distribution.png)

**Failed Query Details:**

| ID | Dataset | Question | Expected Intent | Predicted | Error |
|----|---------|----------|-----------------|-----------|-------|
| 16 | dengue_dataset | count patients with NS1 positive | COUNT | COUNT | result_mismatch |
| 17 | dengue_dataset | count patients with IgG positive | COUNT | COUNT | result_mismatch |
| 18 | dengue_dataset | count patients with IgM positive | COUNT | COUNT | result_mismatch |
| 23 | dengue_dataset | count patients with headache | COUNT | COUNT | result_mismatch |
| 24 | dengue_dataset | count patients with myalgia | COUNT | COUNT | result_mismatch |
| 30 | dengue_dataset | top 5 highest platelet count | SELECT | SELECT | result_mismatch |
| 35 | ecommerce_dataset | total purchase amount | SUM | None | reference_error |
| 36 | ecommerce_dataset | average purchase amount | AVG | None | reference_error |
| 37 | ecommerce_dataset | maximum purchase amount | MAX | None | reference_error |
| 38 | ecommerce_dataset | minimum purchase amount | MIN | None | reference_error |
| 39 | ecommerce_dataset | average time spent on website | AVG | None | reference_error |
| 40 | ecommerce_dataset | average delivery time | AVG | None | reference_error |
| 41 | ecommerce_dataset | average review score | AVG | None | reference_error |
| 42 | ecommerce_dataset | total number of items purchased | SUM | COUNT | intent_error |
| 46 | ecommerce_dataset | show customers with purchase amount greater than 5 | SELECT | None | reference_error |
| 47 | ecommerce_dataset | count customers who availed discount | COUNT | SELECT | intent_error |
| 48 | ecommerce_dataset | count return customers | COUNT | SELECT | intent_error |
| 52 | ecommerce_dataset | count customers who paid with credit card | COUNT | SELECT | intent_error |
| 55 | ecommerce_dataset | total purchase amount by product category | SUM | None | reference_error |
| 56 | ecommerce_dataset | average purchase amount by gender | AVG | None | reference_error |
| 59 | ecommerce_dataset | top 5 highest purchase amount | SELECT | None | reference_error |
| 60 | ecommerce_dataset | lowest 5 purchase amount | SELECT | None | reference_error |
| 70 | employee_dataset | total employees in R and D | COUNT | SUM | intent_error |
| 73 | employee_dataset | top 5 highest monthly income | SELECT | SELECT | result_mismatch |
| 74 | employee_dataset | how many female employees | COUNT | COUNT | result_mismatch |
| 75 | employee_dataset | how many male employees | COUNT | COUNT | result_mismatch |
| 77 | employee_dataset | employees with age between 30 and 40 | SELECT | COUNT | intent_error |
| 79 | employee_dataset | employees with masters degree | SELECT | SELECT | result_mismatch |
| 80 | employee_dataset | employees in Software Development | COUNT | COUNT | result_mismatch |
| 83 | employee_dataset | count employees by gender | COUNT | COUNT | result_mismatch |
| 86 | employee_dataset | employees with single marital status | SELECT | SELECT | result_mismatch |
| 88 | employee_dataset | average performance rating by marital status | AVG | AVG | result_mismatch |
| 89 | employee_dataset | female employees with salary greater than 4000 | SELECT | SELECT | result_mismatch |
| 90 | employee_dataset | total employees by department | COUNT | SUM | intent_error |
| 101 | housing_dataset | top 10 highest priced houses | SELECT | SELECT | result_mismatch |
| 105 | housing_dataset | maximum number of stories | MAX | COUNT | intent_error |
| 108 | housing_dataset | lowest 5 house prices | SELECT | SELECT | result_mismatch |
| 114 | housing_dataset | minimum price by number of stories | MIN | MIN | result_mismatch |
| 115 | housing_dataset | houses on main road | SELECT | COUNT | intent_error |
| 116 | housing_dataset | price between 5000000 and 7000000 | SELECT | MIN | intent_error |
| 117 | housing_dataset | houses with air conditioning and guest room | SELECT | SELECT | result_mismatch |
| 119 | housing_dataset | top 5 most expensive semi furnished houses | SELECT | SELECT | result_mismatch |
| 130 | student_performance_dataset | how many female students | COUNT | COUNT | result_mismatch |
| 131 | student_performance_dataset | how many male students | COUNT | COUNT | result_mismatch |
| 132 | student_performance_dataset | count students with tutoring | COUNT | COUNT | result_mismatch |
| 133 | student_performance_dataset | count students without tutoring | COUNT | COUNT | result_mismatch |
| 134 | student_performance_dataset | count students with extracurricular activities | COUNT | COUNT | result_mismatch |
| 135 | student_performance_dataset | count students who play sports | COUNT | COUNT | result_mismatch |
| 136 | student_performance_dataset | students with GPA greater than 3.5 | COUNT | SELECT | intent_error |
| 137 | student_performance_dataset | students with GPA less than 1.0 | COUNT | SELECT | intent_error |

## 7. Reference vs Generated SQL Analysis

| Category | Count | Percentage |
|----------|-------|------------|
| SQL exactly identical, result correct | 0 | 0.00% |
| SQL different, but result identical | 109 | 60.56% |
| SQL valid but result incorrect | 57 | 31.67% |
| SQL invalid | 14 | 7.78% |
| SQL execution failed | 0 | 0.00% |

### Examples

**Correct Result (ID 1):**
- Question: count all patients
- Reference: `SELECT COUNT(*) FROM dengue_dataset`
- Generated: `SELECT COUNT(*) FROM "dengue"`

**Valid SQL + Wrong Result (ID 16):**
- Question: count patients with NS1 positive
- Reference: `SELECT COUNT(*) FROM dengue_dataset WHERE NS1 = 1`
- Generated: `SELECT COUNT(*) FROM "dengue"`
- Error: result_mismatch
