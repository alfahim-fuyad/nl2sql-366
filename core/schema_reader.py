# core/schema_reader.py

"""
schema_reader.py

Reads dataframe schema information for the NL2SQL pipeline.

Responsibilities:
    - Detect column data types
    - Store representative categorical values
    - Provide numeric/text column lists
    - Print schema information
"""

import pandas as pd


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

MAX_SAMPLE_VALUES = 100


# ---------------------------------------------------------
# Data type helpers
# ---------------------------------------------------------

def is_numeric_dtype(dtype_str):
    """
    Return True when dtype is numeric.

    Supports:
        int
        uint
        float
        double
        decimal
        numeric
        number
    """

    dtype = str(dtype_str).lower()

    return (
        "int" in dtype
        or "uint" in dtype
        or "float" in dtype
        or "double" in dtype
        or "decimal" in dtype
        or "numeric" in dtype
        or "number" in dtype
    )


def is_text_dtype(dtype_str):
    """
    Return True for text/categorical columns.
    """

    dtype = str(dtype_str).lower()

    return (
        dtype in {
            "object",
            "str",
            "string",
            "category",
        }
        or "string" in dtype
        or "object" in dtype
        or "category" in dtype
    )


# ---------------------------------------------------------
# Schema reader
# ---------------------------------------------------------

def read_schema(df):
    """
    Build schema metadata from a pandas DataFrame.

    Example output:

        {
            "gender": {
                "dtype": "object",
                "sample_values": [
                    "Male",
                    "Female"
                ]
            }
        }
    """

    if df is None:
        return {}

    schema = {}

    for column in df.columns:

        series = df[column]

        # ---------------------------------------------
        # Remove null values
        # ---------------------------------------------

        non_null = series.dropna()

        # ---------------------------------------------
        # Get unique values
        # ---------------------------------------------

        try:
            unique_values = (
                non_null
                .unique()
                .tolist()
            )
        except Exception:
            unique_values = []

        # ---------------------------------------------
        # Keep only representative samples
        # ---------------------------------------------

        sample_values = unique_values[
            :MAX_SAMPLE_VALUES
        ]

        schema[column] = {
            "dtype": str(
                series.dtype
            ),
            "sample_values": sample_values,
        }

    return schema


# ---------------------------------------------------------
# Column helpers
# ---------------------------------------------------------

def get_column_names(df):
    """
    Return all dataframe column names.
    """

    if df is None:
        return []

    return list(
        df.columns
    )


def get_numeric_columns(schema):
    """
    Return numeric column names.
    """

    if not schema:
        return []

    return [
        column
        for column, info in schema.items()
        if is_numeric_dtype(
            info.get("dtype", "")
        )
    ]


def get_text_columns(schema):
    """
    Return text/categorical column names.
    """

    if not schema:
        return []

    return [
        column
        for column, info in schema.items()
        if is_text_dtype(
            info.get("dtype", "")
        )
    ]


# ---------------------------------------------------------
# Optional helpers
# ---------------------------------------------------------

def get_categorical_columns(schema):
    """
    Return text/categorical columns that have
    sample values.
    """

    if not schema:
        return []

    return [
        column
        for column, info in schema.items()
        if (
            is_text_dtype(
                info.get("dtype", "")
            )
            and info.get(
                "sample_values",
                []
            )
        )
    ]


def get_column_info(
    schema,
    column
):
    """
    Safely return metadata for a column.
    """

    if not schema:
        return None

    return schema.get(
        column
    )


# ---------------------------------------------------------
# Debug / display
# ---------------------------------------------------------

def print_schema(schema):
    """
    Print readable schema information.
    """

    if not schema:
        print("Schema is empty.")
        return

    print(
        "\n" + "=" * 60
    )
    print("DATABASE SCHEMA")
    print(
        "=" * 60
    )

    for column, info in schema.items():

        print(
            "Column:",
            column
        )

        print(
            "  Type:",
            info.get(
                "dtype",
                "unknown"
            )
        )

        samples = info.get(
            "sample_values",
            []
        )

        print(
            "  Samples:",
            samples[:10]
        )

    print(
        "=" * 60
    )