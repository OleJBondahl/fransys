"""The build's house text records, one per `settings.toml` table: written once after `freeze()`."""

import codecs
from typing import TYPE_CHECKING, NoReturn, cast
lazy from collections.abc import Iterable

from fransys_model.derive import REPORT_KINDS
from fransys_model.kernel import Draft, Origin, SchemaError, evolve
from fransys_model.layout import CSV_QUOTINGS, HOUSE_TABLES, HOUSE_TEXT_KINDS, house_records
from fransys_model.vocab import DocumentPreset

from ._paper import refuse_authored_paper, with_paper
from ._settings_merge import SettingsError

if TYPE_CHECKING:
    from fransys_model.kernel import Model, Record

    from ._settings_merge import Table
    from .settings import Settings

__all__ = ["refuse_authored_house", "with_house"]

_ORIGIN = Origin(file="fransys/_house.py", line=0, note="the build's house text records")


def _str(table: Table, key: str) -> str:
    return cast("str", table[key])


def _refused(table: str, key: str, value: object, known: Iterable[str]) -> NoReturn:
    msg = f'[{table}] "{key}" is {value!r}; known: {", ".join(known)}'
    raise SettingsError(msg)


def _check_skip(skipped: tuple[str, ...]) -> None:
    """Refuse a `ring_out_skip` value that is no `DocumentPreset`."""
    presets = [p.value for p in DocumentPreset]
    for preset in skipped:
        if preset not in presets:
            _refused("export", "ring_out_skip", preset, presets)


def _check_export(table: Table) -> None:
    """Refuse a report kind, quoting, encoding or delimiter of `[export]`."""
    for kind in cast("tuple[str, ...]", table["reports"]):
        if kind not in REPORT_KINDS:
            _refused("export", "reports", kind, REPORT_KINDS)
    _check_skip(cast("tuple[str, ...]", table["ring_out_skip"]))
    if table["csv_quoting"] not in CSV_QUOTINGS:
        _refused("export", "csv_quoting", table["csv_quoting"], CSV_QUOTINGS)
    if len(_str(table, "csv_delimiter")) != 1:
        msg = f'[export] "csv_delimiter" is {table["csv_delimiter"]!r}: use one character'
        raise SettingsError(msg)
    try:
        codecs.lookup(_str(table, "csv_encoding"))
    except LookupError:
        msg = f'[export] "csv_encoding" is {table["csv_encoding"]!r}: not a Python codec name'
        raise SettingsError(msg) from None


def _records(settings: Settings) -> tuple[Record, ...]:
    """One record per settings table, built by the model's `house_records`."""
    tables = {name: settings.table(name) for name in HOUSE_TABLES}
    _check_export(tables["export"])
    return house_records(tables)


def refuse_authored_house(draft: Draft) -> None:
    """Raise when `draft` holds a paper or house text record: only the facade writes them."""
    refuse_authored_paper(draft)
    for record in draft.records():
        if isinstance(record, HOUSE_TEXT_KINDS):
            msg = f"an input authors a {type(record).__name__} record: the facade writes it"
            raise SchemaError(msg, kind="layout.house_text")


def with_house(model: Model, settings: Settings) -> Model:
    """`model` with the paper records and the house text records of `settings`."""
    return evolve(with_paper(model, settings), put=_records(settings), origin=_ORIGIN)
