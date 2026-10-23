"""The key-by-key merge of a consumer's settings file over our defaults, with its refusals (ST2)."""

from collections.abc import Iterable, Mapping
from typing import cast

from fransys_model.vocab import PageKind

from ._settings_types import fits, type_word

type Table = Mapping[str, object]

__all__ = ["SettingsError", "Table", "known", "merged_tables", "paper_by_kind"]

_PAPER_KEYS = ("default", "formats")
# Nested tables keyed by data, not by setting names: a consumer's new key is accepted there.
# A dotted path, as the refusal message prints it (`designation.classes`). One place to list them.
OPEN_TABLES: tuple[str, ...] = ("designation.classes",)
# Tables read by their own code in settings.py, not by the generic merge. `[font]` is read by it
# for `name` and `files` only: its `heights` table is a generic one.
_LIBRARY_TABLES = ("grid", "font")
_GENERIC_FONT_KEYS = ("heights",)


class SettingsError(Exception):
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


def _open_value(table: str, key: str, ours: Table, value: object, where: str) -> object:
    """A new key of an open table: its value must have the type of the table's existing entries."""
    first = next(iter(ours.values()), None)
    if first is not None and not fits(first, value):
        msg = f'{where} [{table}] "{key}" must be {type_word(first)}, got {value!r}'
        raise SettingsError(msg)
    return value


def _merged_flat(table: str, ours: Table, given: Table, where: str) -> dict[str, object]:
    """`ours` with the consumer's keys on top; refuses an unknown key or a value of another type."""
    merged = dict(ours)
    for key, value in given.items():
        if key in ours:
            merged[key] = _merged_value(table, key, ours[key], value, where)
        elif table in OPEN_TABLES:
            merged[key] = _open_value(table, key, ours, value, where)
        else:
            msg = f'{where} [{table}] "{key}" is not a setting; known: {known(ours)}'
            raise SettingsError(msg)
    return merged


def _format_table(name: str, ours: Table, given: Table, where: str) -> dict[str, object]:
    """One paper format with the consumer's keys over ours; refuses an unknown key or type."""
    merged = dict(ours)
    for key, value in given.items():
        if key not in ours:
            msg = f'{where} [paper.formats.{name}] "{key}" is not a setting; known: {known(ours)}'
            raise SettingsError(msg)
        if type(value) is not type(ours[key]):
            msg = (
                f'{where} [paper.formats.{name}] "{key}" must be a {type(ours[key]).__name__}, '
                f"got {value!r}"
            )
            raise SettingsError(msg)
        merged[key] = value
    return merged


def _merged_paper(ours: Table, given: Table, where: str) -> dict[str, object]:
    """The `[paper]` table: `default` and the known formats' keys; no per-kind key."""
    for key in given:
        if key not in _PAPER_KEYS:
            hint = " (the paper per drawing type is set in Python: `fr.settings(paper=...)`)"
            msg = f'{where} [paper] "{key}" is not a setting; known: {known(_PAPER_KEYS)}{hint}'
            raise SettingsError(msg)
    given_formats = _sub(given, "formats")
    our_formats = _sub(ours, "formats")
    for name in given_formats:
        if name not in our_formats:
            msg = (
                f'{where} [paper.formats] "{name}" is not a format; known: {known(our_formats)} '
                "(your own formats arrive with SETTINGS-C)"
            )
            raise SettingsError(msg)
    formats = {
        name: _format_table(name, cast("Table", table), _sub(given_formats, name), where)
        for name, table in our_formats.items()
    }
    default = given.get("default", ours["default"])
    _check_format(default, formats, f"{where} [paper] default")
    return {"default": default, "formats": formats}


def _check_format(name: object, formats: Table, where: str, kind: str = "") -> None:
    if name not in formats:
        label = f"{where} {kind}" if kind else where
        msg = f'{label} "{name}" is not a paper format; known: {known(formats)}'
        raise SettingsError(msg)


def _generic(consumer: Table, name: str) -> Table:
    """The consumer's table `name`; of `[font]` only the keys the generic merge reads."""
    given = _sub(consumer, name)
    if name != "font":
        return given
    return {key: value for key, value in given.items() if key in _GENERIC_FONT_KEYS}


def merged_tables(ours: Table, consumer: Table, where: str) -> dict[str, dict[str, object]]:
    """Every table of ours with the consumer's file on top, key by key; raises `SettingsError`.

    A table our TOML files hold merges with no code naming it; `[paper]` has its own rules.
    """
    names = (*ours, *_LIBRARY_TABLES)
    for table in consumer:
        if table not in names:
            msg = f"{where} table [{table}] is not a settings table; known: {known(names)}"
            raise SettingsError(msg)
    tables = {
        name: _merged_flat(name, _sub(ours, name), _generic(consumer, name), where)
        for name in ours
        if name != "paper"
    }
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
