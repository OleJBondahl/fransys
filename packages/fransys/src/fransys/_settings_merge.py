"""The key-by-key merge of a consumer's settings file over our defaults, with its refusals (ST2)."""

from collections.abc import Iterable, Mapping
from typing import cast

from fransys_model.vocab import PageKind

from ._settings_types import fits, type_word
from .errors import FransysError

type Table = Mapping[str, object]

__all__ = ["SettingsError", "Table", "known", "merged_tables", "paper_by_kind"]

_PAPER_KEYS = ("default", "formats")
# Tables read by their own code in settings.py, not by the generic merge: `[font]`, `name` and `files`.
_LIBRARY_TABLES = ("font",)
# Our values only: each table stays in our TOML files, and a consumer's file may not name it (R1458, R1486).
INTERNAL_TABLES = (
    "layout",
    "profile",
    "pdf",
    "look",
    "lines",
    "dash",
    "reference",
    "frame",
    "stub",
    "wire_label",
    "harness",
    "title_block",
    "revision_table",
    "revision",
    "designation",
)
_REMOVED_TABLES = {
    "colours": "the [colours] table was removed in 0.22; delete it",
    "grid": "the grid is the library's fixed 2.5 mm; delete the table",
}


class SettingsError(FransysError):
    """A settings file or `paper=` is wrong; the message names the file, the key and the fix."""


def known(keys: Iterable[str]) -> str:
    return ", ".join(keys) or "none yet"


def _sub(table: Table, key: str) -> Table:
    """The sub-table `key` of `table`, empty when absent."""
    return cast("Table", table.get(key, {}))


def _merged_value(table: str, key: str, ours: object, value: object, where: str) -> object:
    """The value for `key`: the consumer's, a nested table merged, or a refusal of its type."""
    if isinstance(ours, Mapping) and isinstance(value, Mapping):
        return _merged_flat(f"{table}.{key}", cast("Table", ours), value, where)
    if not fits(ours, value):
        msg = f'{where} [{table}] "{key}" must be {type_word(ours)}, got {value!r}'
        raise SettingsError(msg)
    return value


def _merged_flat(table: str, ours: Table, given: Table, where: str) -> dict[str, object]:
    """`ours` with the consumer's keys on top; refuses an unknown key or a value of another type."""
    merged = dict(ours)
    for key, value in given.items():
        if key in ours:
            merged[key] = _merged_value(table, key, ours[key], value, where)
        else:
            msg = f'{where} [{table}] "{key}" is not a setting; known: {known(ours)}'
            raise SettingsError(msg)
    return merged


def _merged_paper(ours: Table, given: Table, where: str) -> dict[str, object]:
    """The `[paper]` table: `default` and the known formats' keys; no per-kind key."""
    for key in given:
        if key not in _PAPER_KEYS:
            hint = " (the paper per drawing type is set in Python: `fr.settings(paper=...)`)"
            msg = f'{where} [paper] "{key}" is not a setting; known: {known(_PAPER_KEYS)}{hint}'
            raise SettingsError(msg)
    if _sub(given, "formats"):
        msg = f"{where} [paper.formats] is closed: the formats are {known(_sub(ours, 'formats'))}, all landscape; choose one with [paper] default"
        raise SettingsError(msg)
    formats = _sub(ours, "formats")
    default = given.get("default", ours["default"])
    _check_format(default, formats, f"{where} [paper] default")
    return {"default": default, "formats": formats}


def _check_format(name: object, formats: Table, where: str, kind: str = "") -> None:
    if name not in formats:
        label = f"{where} {kind}" if kind else where
        msg = f'{label} "{name}" is not a paper format; known: {known(formats)}'
        raise SettingsError(msg)


def merged_tables(ours: Table, consumer: Table, where: str) -> dict[str, dict[str, object]]:
    """Every table of ours with the consumer's file on top, key by key; raises `SettingsError`.

    A table our TOML files hold merges with no code naming it; `[paper]` has its own rules.
    """
    names = (*ours, *_LIBRARY_TABLES)
    for table in consumer:
        if table in INTERNAL_TABLES:
            msg = f"{where} [{table}] is fixed in 0.22; remove it from your settings (a project sets only words, lists and export)"
            raise SettingsError(msg)
        if table not in names:
            fix = _REMOVED_TABLES.get(table, f"known: {known(names)}")
            msg = f"{where} table [{table}] is not a settings table; {fix}"
            raise SettingsError(msg)
    tables = {name: _merged_flat(name, _sub(ours, name), _sub(consumer, name), where) for name in ours if name != "paper"}
    tables["paper"] = _merged_paper(_sub(ours, "paper"), _sub(consumer, "paper"), where)
    return tables


def paper_by_kind(paper: Table, wanted: Mapping[PageKind, str]) -> dict[PageKind, str]:
    """`wanted` checked against the formats, as the build's paper per drawing type."""
    for kind, name in wanted.items():
        if not isinstance(kind, PageKind):
            msg = f"fr.settings(paper=) key {kind!r} is not a fr.PageKind, e.g. BLOCK_DIAGRAM"
            raise SettingsError(msg)
        _check_format(name, _sub(paper, "formats"), "fr.settings(paper=) for", kind.name)
    return dict(wanted)
