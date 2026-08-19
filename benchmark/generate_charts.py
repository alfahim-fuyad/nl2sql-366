#!/usr/bin/env python3
"""
generate_charts.py — generates publication-quality charts for the benchmark report.

Charts produced:
  1. Intent accuracy by intent type
  2. Result-match accuracy by intent type
  3. Exact SQL match vs Execution accuracy comparison
  4. Error distribution
  5. Per-dataset result accuracy
"""

import json
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

# Font setup
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
SUMMARY_PATH = os.path.join(OUTPUT_DIR, "benchmark_summary.json")

# Professional color palette (colorblind-friendly)
COLORS = {
    'primary': '#4472C4',
    'secondary': '#ED7D31',
    'success': '#70AD47',
    'danger': '#C00000',
    'info': '#5B9BD5',
    'purple': '#7030A0',
    'gray': '#A5A5A5',
}

INTENT_ORDER = ['COUNT', 'AVG', 'SUM', 'MAX', 'MIN', 'SELECT']
DATASET_ORDER = [
    'housing_dataset',
    'ecommerce_dataset',
    'diabetes_prediction_dataset',
    'dengue_dataset',
    'student_performance_dataset',
    'employee_dataset',
]


def load_data():
    with open(SUMMARY_PATH) as f:
        return json.load(f)


def _save_fig(fig, name):
    path = os.path.join(OUTPUT_DIR, name)
    fig.savefig(path, dpi=200, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)
    print(f"  Saved: {path}")


def chart_intent_accuracy(data):
    """Bar chart: Intent classification accuracy per intent."""
    by_intent = data['metrics']['by_intent']
    intents = [k for k in INTENT_ORDER if k in by_intent]
    values = [by_intent[k]['intent_accuracy'] for k in intents]

    fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    bars = ax.bar(intents, values, color=COLORS['primary'], edgecolor='white', width=0.6)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1.5,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.set_ylabel('Accuracy (%)', fontsize=11)
    ax.set_xlabel('Intent Type', fontsize=11)
    ax.set_title('Intent Classification Accuracy by Intent', fontsize=13, fontweight='bold')
    ax.set_ylim(0, 110)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, alpha=0.3)
    _save_fig(fig, 'chart_intent_accuracy.png')


def chart_result_match(data):
    """Bar chart: Result-match accuracy per intent."""
    by_intent = data['metrics']['by_intent']
    intents = [k for k in INTENT_ORDER if k in by_intent]
    values = [by_intent[k]['result_match_accuracy'] for k in intents]

    fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    colors = [COLORS['success'] if v >= 50 else COLORS['secondary'] if v >= 25 else COLORS['danger']
              for v in values]
    bars = ax.bar(intents, values, color=colors, edgecolor='white', width=0.6)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.set_ylabel('Accuracy (%)', fontsize=11)
    ax.set_xlabel('Intent Type', fontsize=11)
    ax.set_title('Result Match Accuracy by Intent', fontsize=13, fontweight='bold')
    ax.set_ylim(0, 110)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, alpha=0.3)
    _save_fig(fig, 'chart_result_match.png')


def chart_execution_vs_exact(data):
    """Grouped bar: Execution accuracy vs Exact SQL match vs Result match (overall)."""
    o = data['metrics']['overall']
    categories = ['Intent\nAccuracy', 'Valid\nSQL', 'Execution\nSuccess', 'Result\nMatch', 'Exact SQL\nMatch']
    values = [
        o['intent_accuracy'],
        o['valid_sql_rate'],
        o['execution_success_rate'],
        o['result_match_accuracy'],
        o['exact_sql_match_rate'],
    ]

    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    colors = [COLORS['primary'], COLORS['info'], COLORS['purple'], COLORS['success'], COLORS['gray']]
    bars = ax.bar(categories, values, color=colors, edgecolor='white', width=0.55)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1.5,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.set_ylabel('Rate (%)', fontsize=11)
    ax.set_title('Overall Benchmark Metrics Comparison', fontsize=13, fontweight='bold')
    ax.set_ylim(0, 115)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, alpha=0.3)
    _save_fig(fig, 'chart_overall_metrics.png')


def chart_error_distribution(data):
    """Pie/donut chart: Error category distribution."""
    categories = data['metrics']['error_analysis']['categories']
    if not categories:
        return

    labels = list(categories.keys())
    sizes = list(categories.values())
    total = sum(sizes)

    # Shorten labels for display
    label_map = {
        'result_mismatch': 'Result Mismatch',
        'intent_error': 'Intent Error',
        'sql_validation_error': 'SQL Validation Error',
        'sql_execution_error': 'SQL Execution Error',
        'reference_error': 'Reference Error',
        'schema_error': 'Schema Error',
        'unknown': 'Unknown',
    }
    display_labels = [label_map.get(l, l) for l in labels]

    fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
    pie_colors = ['#C00000', '#ED7D31', '#FFC000', '#5B9BD5', '#A5A5A5', '#7030A0', '#404040']

    wedges, texts, autotexts = ax.pie(
        sizes, labels=display_labels, autopct='%1.1f%%',
        colors=pie_colors[:len(sizes)], startangle=90,
        pctdistance=0.75, labeldistance=1.15,
        wedgeprops=dict(width=0.5, edgecolor='white'),
        textprops={'fontsize': 9}
    )
    for t in autotexts:
        t.set_fontsize(9)
        t.set_fontweight('bold')

    ax.set_title(f'Error Distribution (n={total})', fontsize=13, fontweight='bold')
    _save_fig(fig, 'chart_error_distribution.png')


def chart_per_dataset(data):
    """Bar chart: Result match accuracy per dataset."""
    by_dataset = data['metrics']['by_dataset']
    datasets = [k for k in DATASET_ORDER if k in by_dataset]
    values = [by_dataset[k]['result_match_accuracy'] for k in datasets]
    totals = [by_dataset[k]['total'] for k in datasets]

    fig, ax = plt.subplots(figsize=(9, 4.5), constrained_layout=True)
    colors = [COLORS['success'] if v >= 50 else COLORS['secondary'] if v >= 25 else COLORS['danger']
              for v in values]
    bars = ax.bar(datasets, values, color=colors, edgecolor='white', width=0.55)

    for bar, val, tot in zip(bars, values, totals):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                f'{val:.1f}%\n(n={tot})', ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_ylabel('Result Match Accuracy (%)', fontsize=11)
    ax.set_xlabel('Dataset', fontsize=11)
    ax.set_title('Result Match Accuracy by Dataset', fontsize=13, fontweight='bold')
    ax.set_ylim(0, 110)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, alpha=0.3)
    plt.xticks(rotation=15, ha='right')
    _save_fig(fig, 'chart_dataset_accuracy.png')


def chart_pipeline_funnel(data):
    """Horizontal bar: pipeline stage pass rates."""
    o = data['metrics']['overall']
    stages = ['Intent\nDetection', 'SQL\nValidation', 'SQL\nExecution', 'Result\nMatch']
    values = [
        o['intent_accuracy'],
        o['valid_sql_rate'],
        o['execution_success_rate'],
        o['result_match_accuracy'],
    ]

    fig, ax = plt.subplots(figsize=(8, 4), constrained_layout=True)
    colors = [COLORS['primary'], COLORS['info'], COLORS['purple'], COLORS['success']]

    y_pos = range(len(stages))
    bars = ax.barh(list(y_pos), values, color=colors, edgecolor='white', height=0.5)

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height()/2.,
                f'{val:.1f}%', ha='left', va='center', fontsize=10, fontweight='bold')

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(stages, fontsize=10)
    ax.set_xlabel('Rate (%)', fontsize=11)
    ax.set_title('NL2SQL Pipeline Pass Rates', fontsize=13, fontweight='bold')
    ax.set_xlim(0, 115)
    ax.invert_yaxis()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.xaxis.grid(True, alpha=0.3)
    _save_fig(fig, 'chart_pipeline_funnel.png')


def main():
    print("Generating benchmark charts...")
    data = load_data()

    chart_intent_accuracy(data)
    chart_result_match(data)
    chart_execution_vs_exact(data)
    chart_error_distribution(data)
    chart_per_dataset(data)
    chart_pipeline_funnel(data)

    print("All charts generated.")


if __name__ == "__main__":
    main()
