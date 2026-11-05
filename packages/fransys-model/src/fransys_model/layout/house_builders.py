"""`house_records`: the house text records of the `settings.toml` tables, one path for all of them.

The key of each record is `("build", <table>)`, so a record is the same wherever it is built.
"""

from decimal import Decimal
from typing import Any, cast
lazy from collections.abc import Mapping

from fransys_model.kernel import Record, SchemaError, make_id

from .house_export import DesignationForm, ExportForm
from .house_lists import Lists
from .house_text import (
    FrameForm,
    HarnessText,
    HouseProfile,
    ReferenceText,
    RevisionForm,
    RevisionTableForm,
    StubText,
    TitleBlockForm,
    WireLabelText,
    Words,
)

__all__ = ["HOUSE_TABLES", "house_records"]

# The tables whose keys are the record's fields; `words` and `lists` are built below.
_FORMS = {
    "reference": ReferenceText,
    "frame": FrameForm,
    "stub": StubText,
    "wire_label": WireLabelText,
    "harness": HarnessText,
    "profile": HouseProfile,
    "title_block": TitleBlockForm,
    "revision_table": RevisionTableForm,
    "revision": RevisionForm,
}
_LAST = {"export": ExportForm, "designation": DesignationForm}
HOUSE_TABLES = (*_FORMS, "words", "lists", *_LAST)


def _field(key: str, value: object) -> object:
    """A `*_mm` length is an exact decimal of the mm; a list is a tuple."""
    if key.endswith("_mm"):
        return Decimal(str(float(cast("float", value))))
    return tuple(value) if isinstance(value, (list, tuple)) else value


def _column(name: str, table: Mapping[str, Any], key: str) -> tuple[str, ...]:
    """The `key` of each row of `table["columns"]`, in order; a row without it is refused."""
    out: list[str] = []
    for number, row in enumerate(table["columns"], start=1):
        if key not in row:
            msg = f"[lists.{name}.columns] row {number} has no `{key}` key; give every row of that table a `{key} = ...` line"
            raise SchemaError(msg, kind="layout.lists")
        out.append(str(row[key]))
    return tuple(out)


def _lists(tables: Mapping[str, Mapping[str, Any]]) -> Lists:
    """The `[lists]` record: per list name its `columns` rows and its `pdf_columns`."""
    key = ("build", "lists")
    return Lists(
        id=make_id(Lists, key),
        key=key,
        columns=frozendict({name: _column(name, t, "field") for name, t in tables.items()}),
        pdf_words=frozendict({name: _column(name, t, "pdf") for name, t in tables.items()}),
        csv_words=frozendict({name: _column(name, t, "csv") for name, t in tables.items()}),
        pdf_columns=frozendict({name: tuple(t["pdf_columns"]) for name, t in tables.items() if "pdf_columns" in t}),
    )


def _record(cls: type[Any], name: str, table: Mapping[str, Any]) -> Record:
    key = ("build", name)
    return cls(id=make_id(cls, key), key=key, **{k: _field(k, v) for k, v in table.items()})


def house_records(tables: Mapping[str, Mapping[str, object]]) -> tuple[Record, ...]:
    """One record per table of `HOUSE_TABLES` in `tables`, in that order; a table key is a record field."""
    key = ("build", "words")
    words = Words(id=make_id(Words, key), key=key, words=frozendict(cast("Mapping[str, str]", tables["words"])))
    return (
        *(_record(cls, name, tables[name]) for name, cls in _FORMS.items()),
        words,
        _lists(cast("Mapping[str, Mapping[str, Any]]", tables["lists"])),
        *(_record(cls, name, tables[name]) for name, cls in _LAST.items()),
    )
