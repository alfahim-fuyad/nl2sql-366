"""
Extracts schema information from a pandas DataFrame.

Builds a dictionary mapping each column name to its data type and a sample
of unique values, which the rest of the pipeline uses for column and value matching.
"""

MAX_SAMPLE_VALUES = 100


def read_schema(df):
    """
    Build a schema dictionary from a DataFrame.

    Format:
        {
            "Age":    {"dtype": "int64",  "sample_values": [45, 30, 52, ...]},
            "Gender": {"dtype": "object", "sample_values": ["Male", "Female"]},
        }

    Up to MAX_SAMPLE_VALUES unique non-null values are stored per column.
    A larger sample improves categorical matching accuracy.
    """
    schema = {}
    for column in df.columns:
        unique_values = df[column].dropna().unique()
        schema[column] = {
            "dtype":         str(df[column].dtype),
            "sample_values": unique_values[:MAX_SAMPLE_VALUES].tolist(),
        }
    return schema


def get_column_names(df):
    """Return the list of column names from a DataFrame."""
    return list(df.columns)


def is_numeric_dtype(dtype_str):
    """Return True if the dtype string represents a numeric (int or float) type."""
    return "int" in dtype_str or "float" in dtype_str


def is_text_dtype(dtype_str):
    """Return True if the dtype string represents a text or categorical type."""
    return dtype_str in ("object", "str", "string", "category")


def get_numeric_columns(schema):
    """Return the names of all numeric columns in the schema."""
    return [col for col, info in schema.items() if is_numeric_dtype(info["dtype"])]


def get_text_columns(schema):
    """Return the names of all text/categorical columns in the schema."""
    return [col for col, info in schema.items() if is_text_dtype(info["dtype"])]


def print_schema(schema):
    """Print a human-readable summary of the schema (for debugging)."""
    for column, info in schema.items():
        print("Column:", column)
        print("  Type:", info["dtype"])
        print("  Samples:", info["sample_values"][:10])
