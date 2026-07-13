# core/response.py


def format_result(column_names, rows):
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
    print(format_result(column_names, rows))
