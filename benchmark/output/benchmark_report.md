# NL2SQL-366 Benchmark Report

**Generated:** 2026-08-18 18:18 UTC
**Total Runtime:** 3.81 seconds

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
| Intent Accuracy | 78.89% |
| Valid SQL | 86.67% |
| Execution Success | 86.67% |
| Result Match Accuracy | 45.00% |
| Exact SQL Match | 0.00% |
| Macro F1 | 60.95% |
| Avg SQL Generation Time | 0.01 ms |
| Avg Execution Time | 1.03 ms |
| Total Passed | 81 |
| Total Failed | 99 |

![Overall Metrics](chart_overall_metrics.png)

### 2.1 Method Comparison

| Method | Description | Accuracy |
|--------|-------------|----------|
| Reference SQL | Ground-truth SQL executed directly | 100.00% |
| NL2SQL-366 | Natural language to SQL pipeline | 45.00% |

> Reference SQL is treated as ground truth. NL2SQL-366 is correct when generated SQL produces the same result as the reference SQL.

![Pipeline Funnel](chart_pipeline_funnel.png)

## 3. Per-Intent Results

| Intent | Queries | Intent Acc. | Result Match | Exact SQL | Valid SQL | Exec Success |
|--------|---------|-------------|--------------|-----------|-----------|-------------|
| AVG | 44 | 84.09% | 54.55% | 0.00% | 79.55% | 79.55% |
| COUNT | 69 | 72.46% | 40.58% | 0.00% | 95.65% | 95.65% |
| MAX | 17 | 88.24% | 52.94% | 0.00% | 76.47% | 76.47% |
| MIN | 16 | 93.75% | 68.75% | 0.00% | 81.25% | 81.25% |
| SELECT | 27 | 77.78% | 22.22% | 0.00% | 88.89% | 88.89% |
| SUM | 7 | 57.14% | 42.86% | 0.00% | 71.43% | 71.43% |

![Intent Accuracy](chart_intent_accuracy.png)

![Result Match by Intent](chart_result_match.png)

## 4. Per-Dataset Results

| Dataset | Queries | Intent Acc. | Result Match | Exact SQL |
|---------|---------|-------------|--------------|-----------|
| dengue_dataset | 30 | 100.00% | 73.33% | 0.00% |
| ecommerce_dataset | 30 | 46.67% | 46.67% | 0.00% |
| employee_dataset | 30 | 93.33% | 50.00% | 0.00% |
| housing_dataset | 30 | 83.33% | 53.33% | 0.00% |
| student_performance_dataset | 30 | 76.67% | 40.00% | 0.00% |
| temp_and_rain_dataset | 30 | 73.33% | 6.67% | 0.00% |

![Dataset Accuracy](chart_dataset_accuracy.png)

## 5. Precision, Recall, F1 by Intent

| Intent | Precision | Recall | F1 | Support |
|--------|-----------|--------|-----|---------|
| AVG | 100.00% | 54.55% | 70.59% | 44 |
| COUNT | 100.00% | 40.58% | 57.73% | 69 |
| MAX | 100.00% | 52.94% | 69.23% | 17 |
| MIN | 100.00% | 68.75% | 81.48% | 16 |
| SELECT | 100.00% | 22.22% | 36.36% | 27 |
| SUM | 100.00% | 42.86% | 60.00% | 7 |

## 6. Error Analysis

**Total Failed Queries:** 99

**Error Distribution:**

| Error Category | Count |
|----------------|-------|
| intent_error | 26 |
| reference_error | 12 |
| result_mismatch | 52 |
| sql_validation_error | 9 |

![Error Distribution](chart_error_distribution.png)

**Failed Query Details:**

| ID | Dataset | Question | Expected Intent | Predicted | Error |
|----|---------|----------|-----------------|-----------|-------|
| 16 | dengue_dataset | count patients with NS1 positive | COUNT | COUNT | result_mismatch |
| 17 | dengue_dataset | count patients with IgG positive | COUNT | COUNT | result_mismatch |
| 18 | dengue_dataset | count patients with IgM positive | COUNT | COUNT | result_mismatch |
| 22 | dengue_dataset | count patients with outcome 1 | COUNT | COUNT | result_mismatch |
| 23 | dengue_dataset | count patients with headache | COUNT | COUNT | result_mismatch |
| 24 | dengue_dataset | count patients with myalgia | COUNT | COUNT | result_mismatch |
| 29 | dengue_dataset | count patients by area type | COUNT | COUNT | result_mismatch |
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
| 70 | employee_dataset | total employees in R and D | COUNT | COUNT | result_mismatch |
| 71 | employee_dataset | employees with salary greater than 5000 | SELECT | SELECT | result_mismatch |
| 72 | employee_dataset | average salary hike by department | AVG | AVG | sql_validation_error |
| 73 | employee_dataset | top 5 highest monthly income | SELECT | SELECT | result_mismatch |
| 74 | employee_dataset | how many female employees | COUNT | COUNT | result_mismatch |
| 75 | employee_dataset | how many male employees | COUNT | COUNT | result_mismatch |
| 76 | employee_dataset | employees with performance rating 5 | SELECT | SELECT | result_mismatch |
| 77 | employee_dataset | employees with age between 30 and 40 | SELECT | COUNT | intent_error |
| 79 | employee_dataset | employees with masters degree | SELECT | SELECT | result_mismatch |
| 80 | employee_dataset | employees in Software Development | COUNT | COUNT | result_mismatch |
| 81 | employee_dataset | employees with salary less than 3000 | SELECT | SELECT | result_mismatch |
| 82 | employee_dataset | maximum salary hike | MAX | MAX | sql_validation_error |
| 86 | employee_dataset | employees with single marital status | SELECT | SELECT | result_mismatch |
| 89 | employee_dataset | female employees with salary greater than 4000 | SELECT | SELECT | result_mismatch |
| 90 | employee_dataset | total employees by department | COUNT | SUM | intent_error |
| 98 | housing_dataset | average number of bedrooms | AVG | COUNT | intent_error |
| 99 | housing_dataset | average number of bathrooms | AVG | COUNT | intent_error |
| 100 | housing_dataset | houses with 4 bedrooms | SELECT | SELECT | result_mismatch |
| 102 | housing_dataset | average area of houses with air conditioning | AVG | AVG | result_mismatch |
| 103 | housing_dataset | how many houses have guest room | COUNT | COUNT | result_mismatch |
| 105 | housing_dataset | maximum number of stories | MAX | COUNT | intent_error |
| 109 | housing_dataset | houses with basement | SELECT | SELECT | result_mismatch |
| 110 | housing_dataset | average price of houses with hot water heating | AVG | AVG | result_mismatch |
| 111 | housing_dataset | houses with 2 bathrooms | SELECT | SELECT | result_mismatch |
| 115 | housing_dataset | houses on main road | SELECT | COUNT | intent_error |
| 116 | housing_dataset | price between 5000000 and 7000000 | SELECT | MIN | intent_error |

## 7. Reference vs Generated SQL Analysis

| Category | Count | Percentage |
|----------|-------|------------|
| SQL exactly identical, result correct | 0 | 0.00% |
| SQL different, but result identical | 81 | 45.00% |
| SQL valid but result incorrect | 75 | 41.67% |
| SQL invalid | 24 | 13.33% |
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
