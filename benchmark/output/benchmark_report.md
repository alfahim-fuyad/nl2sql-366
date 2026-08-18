# NL2SQL-366 Benchmark Report

**Generated:** 2026-08-18 15:01 UTC
**Total Runtime:** 12.27 seconds

## 1. Benchmark Overview

- **Total SQL Queries Evaluated:** 271
- **Number of Datasets/Schemas:** 5
- **Datasets:** dengue, employee_dataset, housing, student_performance, temp_and_rain
- **Intent Distribution:**
  - AVG: 71 queries
  - COUNT: 141 queries
  - MAX: 26 queries
  - MIN: 18 queries
  - SELECT: 3 queries
  - SUM: 12 queries

## 2. Overall Results

| Metric | Score |
|--------|-------|
| Intent Accuracy | 90.04% |
| Valid SQL | 97.42% |
| Execution Success | 97.42% |
| Result Match Accuracy | 51.29% |
| Exact SQL Match | 0.00% |
| Macro F1 | 66.65% |
| Avg SQL Generation Time | 0.01 ms |
| Avg Execution Time | 0.77 ms |
| Total Passed | 139 |
| Total Failed | 132 |

![Overall Metrics](chart_overall_metrics.png)

### 2.1 Method Comparison

| Method | Description | Accuracy |
|--------|-------------|----------|
| Reference SQL | Ground-truth SQL executed directly on the database | 100.00% (by definition) |
| NL2SQL-366 | Natural language converted to SQL by the NL2SQL-366 pipeline | 51.29% |

> The Reference SQL serves as the ground truth. NL2SQL-366 is evaluated on whether its generated SQL produces the same database result as the reference query.

![Pipeline Funnel](chart_pipeline_funnel.png)

## 3. Per-Intent Results

| Intent | Queries | Intent Acc. | Result Match | Exact SQL | Valid SQL | Exec Success |
|--------|---------|-------------|--------------|-----------|-----------|-------------|
| AVG | 71 | 98.59% | 59.15% | 0.00% | 97.18% | 97.18% |
| COUNT | 141 | 88.65% | 40.43% | 0.00% | 98.58% | 98.58% |
| MAX | 26 | 84.62% | 73.08% | 0.00% | 96.15% | 96.15% |
| MIN | 18 | 83.33% | 66.67% | 0.00% | 94.44% | 94.44% |
| SELECT | 3 | 33.33% | 0.00% | 0.00% | 66.67% | 66.67% |
| SUM | 12 | 91.67% | 75.00% | 0.00% | 100.00% | 100.00% |

![Intent Accuracy](chart_intent_accuracy.png)

![Result Match by Intent](chart_result_match.png)

## 4. Per-Dataset Results

| Dataset | Queries | Intent Acc. | Result Match | Exact SQL |
|---------|---------|-------------|--------------|-----------|
| dengue | 50 | 88.00% | 44.00% | 0.00% |
| employee_dataset | 32 | 90.62% | 43.75% | 0.00% |
| housing | 67 | 95.52% | 65.67% | 0.00% |
| student_performance | 63 | 85.71% | 33.33% | 0.00% |
| temp_and_rain | 59 | 89.83% | 64.41% | 0.00% |

![Dataset Accuracy](chart_dataset_accuracy.png)

## 5. Precision, Recall, F1 by Intent

| Intent | Precision | Recall | F1 | Support |
|--------|-----------|--------|-----|---------|
| AVG | 100.00% | 59.15% | 74.34% | 71 |
| COUNT | 100.00% | 40.43% | 57.58% | 141 |
| MAX | 100.00% | 73.08% | 84.44% | 26 |
| MIN | 100.00% | 66.67% | 80.00% | 18 |
| SELECT | 0.00% | 0.00% | 0.00% | 3 |
| SUM | 100.00% | 75.00% | 85.71% | 12 |

## 6. Error Analysis

**Total Failed Queries:** 132

**Error Distribution:**

| Error Category | Count |
|----------------|-------|
| intent_error | 26 |
| result_mismatch | 102 |
| sql_validation_error | 4 |

![Error Distribution](chart_error_distribution.png)

**Failed Query Details:**

| ID | Dataset | Question | Expected Intent | Predicted | Error |
|----|---------|----------|-----------------|-----------|-------|
| 3 | housing | How many houses are over the 10,000,000 mark? | COUNT | COUNT | result_mismatch |
| 8 | housing | Can you tell me how many houses are on the main ro | COUNT | COUNT | result_mismatch |
| 10 | housing | How many properties are located in a preferred are | COUNT | COUNT | result_mismatch |
| 11 | housing | How many houses have a guest room? | COUNT | COUNT | result_mismatch |
| 15 | housing | Can you find how many houses have no parking space | COUNT | COUNT | result_mismatch |
| 18 | housing | How many houses have air conditioning and are also | COUNT | COUNT | result_mismatch |
| 29 | housing | On average, how much does a house in a preferred a | AVG | AVG | result_mismatch |
| 42 | housing | What's the total number of parking spots across al | SUM | COUNT | intent_error |
| 43 | housing | Which furnishing status appears most often in the  | COUNT | SELECT | intent_error |
| 44 | housing | How many bedrooms does the most common house confi | COUNT | COUNT | result_mismatch |
| 45 | housing | Which number of parking spaces is most common amon | COUNT | COUNT | result_mismatch |
| 46 | housing | Can you show me the price of the most expensive ho | SELECT | SELECT | result_mismatch |
| 47 | housing | What's the area of the cheapest house in the datas | SELECT | AVG | intent_error |
| 48 | housing | How many distinct furnishing statuses are there? | COUNT | COUNT | result_mismatch |
| 49 | housing | How many different bedroom counts appear in the da | COUNT | COUNT | result_mismatch |
| 50 | housing | How many houses have both a guest room and a basem | COUNT | COUNT | result_mismatch |
| 51 | housing | How many houses have neither air conditioning nor  | COUNT | COUNT | result_mismatch |
| 53 | housing | How many houses have fewer than 2 bathrooms? | COUNT | COUNT | result_mismatch |
| 54 | housing | How many houses have more than one bathroom? | COUNT | COUNT | result_mismatch |
| 60 | housing | How many houses are not located in a preferred are | COUNT | COUNT | result_mismatch |
| 63 | housing | How many houses have 5 or 6 bedrooms? | COUNT | COUNT | result_mismatch |
| 64 | housing | What's the minimum area among houses that are on t | MIN | MIN | result_mismatch |
| 65 | housing | How many unfurnished houses lack a main road conne | COUNT | COUNT | result_mismatch |
| 68 | student_performance | How many students are there in total? | COUNT | SUM | intent_error |
| 71 | student_performance | Can you tell me how many students receive tutoring | COUNT | COUNT | result_mismatch |
| 72 | student_performance | How many students do not receive tutoring? | COUNT | COUNT | result_mismatch |
| 73 | student_performance | How many students participate in extracurricular a | COUNT | COUNT | result_mismatch |
| 74 | student_performance | How many students play sports? | COUNT | COUNT | result_mismatch |
| 75 | student_performance | Could you check how many students are involved in  | COUNT | COUNT | result_mismatch |
| 76 | student_performance | How many students do volunteering work? | COUNT | COUNT | result_mismatch |
| 78 | student_performance | How many students have fewer than 5 absences? | COUNT | COUNT | result_mismatch |
| 79 | student_performance | How many students have zero absences? | COUNT | COUNT | result_mismatch |
| 82 | student_performance | How many students study more than 15 hours a week? | COUNT | COUNT | result_mismatch |
| 83 | student_performance | How many students study less than 5 hours a week? | COUNT | COUNT | result_mismatch |
| 86 | student_performance | How many students have the highest level of parent | COUNT | MAX | intent_error |
| 87 | student_performance | How many students report no parental support at al | COUNT | COUNT | result_mismatch |
| 89 | student_performance | On average, how many hours do students study per w | AVG | AVG | result_mismatch |
| 91 | student_performance | On average, what GPA do students who receive tutor | AVG | AVG | result_mismatch |
| 92 | student_performance | On average, what GPA do students without tutoring  | AVG | AVG | result_mismatch |
| 93 | student_performance | Can you find the average GPA of students who play  | AVG | AVG | result_mismatch |
| 94 | student_performance | What's the average study time for students in Grad | AVG | AVG | result_mismatch |
| 97 | student_performance | What's the average GPA of students with the highes | AVG | AVG | result_mismatch |
| 101 | student_performance | What's the minimum weekly study time recorded? | MIN | MIN | sql_validation_error |
| 102 | student_performance | What's the highest weekly study time among all stu | MAX | MAX | result_mismatch |
| 103 | student_performance | What's the oldest age recorded among students? | MAX | AVG | intent_error |
| 104 | student_performance | What's the youngest age among the students? | MIN | AVG | intent_error |
| 107 | student_performance | What's the combined weekly study time for every st | SUM | SUM | result_mismatch |
| 108 | student_performance | How many students in total participate in at least | COUNT | SUM | intent_error |
| 109 | student_performance | Which GradeClass has the most students in it? | COUNT | MIN | intent_error |
| 111 | student_performance | What's the most common parental education level am | COUNT | AVG | intent_error |
| ... | | | | | +82 more |

## 7. Reference vs Generated SQL Analysis

| Category | Count | Percentage |
|----------|-------|------------|
| SQL exactly identical, result correct | 0 | 0.00% |
| SQL different, but result identical | 139 | 51.29% |
| SQL valid but result incorrect | 125 | 46.13% |
| SQL invalid | 7 | 2.58% |
| SQL execution failed | 0 | 0.00% |

### Examples

**Different SQL + Same Result (ID 1):**
- Question: How many houses have air conditioning?
- Reference: `SELECT COUNT(*) FROM housing WHERE airconditioning='yes'`
- Generated: `SELECT COUNT(*) FROM "housing" WHERE "airconditioning" = 'yes'`

**Valid SQL + Wrong Result (ID 3):**
- Question: How many houses are over the 10,000,000 mark?
- Reference: `SELECT COUNT(*) FROM housing WHERE price>10000000`
- Generated: `SELECT COUNT(*) FROM "housing"`
- Error: result_mismatch
