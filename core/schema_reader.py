# core/schema_reader.py

MAX_SAMPLE_VALUES = 100


def read_schema(df):
    schema = {}
    for column in df.columns:
        unique_values = df[column].dropna().unique()
        schema[column] = {
            "dtype":         str(df[column].dtype),
            "sample_values": unique_values[:MAX_SAMPLE_VALUES].tolist(),
        }
    return schema


def get_column_names(df):
    return list(df.columns)


def is_numeric_dtype(dtype_str):
    return "int" in dtype_str or "float" in dtype_str


def is_text_dtype(dtype_str):
    return dtype_str in ("object", "str", "string", "category")


def get_numeric_columns(schema):
    return [col for col, info in schema.items() if is_numeric_dtype(info["dtype"])]


def get_text_columns(schema):
    return [col for col, info in schema.items() if is_text_dtype(info["dtype"])]


def print_schema(schema):
    for column, info in schema.items():
        print("Column:", column)
        print("  Type:", info["dtype"])
        print("  Samples:", info["sample_values"][:10])
