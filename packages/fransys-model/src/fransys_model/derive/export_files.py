"""The one home of an export file's place, bytes and CSV form, read from the `[export]` record.

Facade and reports call these with the model's `ExportForm`; none keeps a copy of the rule.
"""

import csv

lazy from fransys_model.layout import ExportForm

__all__ = ["csv_dialect", "export_bytes", "export_path"]


def export_path(form: ExportForm, name: str) -> str:
    """`name` as its path from `out_dir`: a `data_suffixes` file goes into `data_dir`."""
    return f"{form.data_dir}/{name}" if name.endswith(tuple(form.data_suffixes)) else name


def export_bytes(form: ExportForm, name: str, text: str) -> bytes:
    """`text` as the bytes of file `name`: a `.csv` in `csv_encoding`, every other file in UTF-8."""
    return text.encode(form.csv_encoding if name.endswith(".csv") else "utf-8")


def csv_dialect(form: ExportForm) -> type[csv.Dialect]:
    """The `csv` dialect of the CSV form: Excel's with the form's delimiter, quoting and newline."""
    return type(
        "ExportDialect",
        (csv.excel,),
        {
            "delimiter": form.csv_delimiter,
            "quoting": getattr(csv, f"QUOTE_{form.csv_quoting.upper()}"),
            "lineterminator": form.csv_newline,
        },
    )
