"""The fields each list output prints of a row shape: the PDF lists and the CSVs read them here.

The columns are the `[lists.<name>]` settings tables, held by the `Lists` house record. A column
is a row field name, in the row's field order, with the `[words]` keys of its PDF heading and its
CSV header. An `Id` field is left out where the row carries its rendered twin.
"""

lazy from collections.abc import Mapping

from fransys_model.kernel import Model, SchemaError

from .facts.house_settings import lists_of, word

__all__ = ["list_columns", "list_csv_header", "list_pdf_columns", "list_pdf_heading"]


def _of[T](table: Mapping[str, T], name: str) -> T:
    if name not in table:
        msg = f'[lists] has no list "{name}"; known: {", ".join(table)}'
        raise SchemaError(msg, kind="layout.lists")
    return table[name]


def list_columns(model: Model, name: str) -> tuple[str, ...]:
    """The row fields the list `name` prints, in order (`[[lists.<name>.columns]] field`)."""
    return _of(lists_of(model).columns, name)


def list_pdf_columns(model: Model, name: str) -> tuple[str, ...]:
    """The row fields the PDF of list `name` prints (`pdf_columns`); raises when it has none."""
    table = lists_of(model).pdf_columns
    if name not in table:
        msg = f"[lists.{name}] has no pdf_columns; known: {', '.join(table)}"
        raise SchemaError(msg, kind="layout.lists")
    return table[name]


def _heading(model: Model, name: str, field: str, words: Mapping[str, tuple[str, ...]]) -> str:
    columns = list_columns(model, name)
    if field not in columns:
        msg = f'[lists.{name}] has no column "{field}"; known: {", ".join(columns)}'
        raise SchemaError(msg, kind="layout.lists")
    return word(model, _of(words, name)[columns.index(field)])


def list_pdf_heading(model: Model, name: str, field: str) -> str:
    """The PDF heading of `field` in list `name`: the `[words]` text of its `pdf` key."""
    return _heading(model, name, field, lists_of(model).pdf_words)


def list_csv_header(model: Model, name: str, field: str) -> str:
    """The CSV header of `field` in list `name`: the `[words]` text of its `csv` key."""
    return _heading(model, name, field, lists_of(model).csv_words)
