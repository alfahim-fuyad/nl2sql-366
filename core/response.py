"""
Formats SQL query results as a human-readable ASCII table for CLI output.
"""


def format_result(column_names, rows):
    """
    Render query results as a column-aligned text table.

    Column widths are computed from the maximum of the header length
    and the longest value in each column. Returns a "no results" message
    if the row list is empty.
    """
    if not rows:
        return "No results found."

    col_widths = []
    for i, col in enumerate(column_names):
        max_data_width = max((len(str(row[i])) for row in rows), default=0)
        col_widths.append(max(len(col), max_data_width))

    def fmt_row(values):
        return " | ".join(
            str(v).ljust(col_widths[i]) for i, v in enumerate(values)
        )

    header    = fmt_row(column_names)
    separator = "-" * len(header)

    lines = [header, separator] + [fmt_row(row) for row in rows]
    return "\n".join(lines)


def print_result(column_names, rows):
    """Print the formatted result table to stdout."""
    print(format_result(column_names, rows))
