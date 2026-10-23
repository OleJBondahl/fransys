"""The key-by-key merge of a consumer's settings file over our defaults, with its refusals (ST2)."""

from typing import TYPE_CHECKING, cast

from fransys_model.vocab import PageKind

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

type Table = Mapping[str, object]

__all__ = ["SettingsError", "Table", "known", "merged_tables", "paper_by_kind"]

# A table whose reader has not landed: a consumer key there raises, naming the landing order.
_NOT_READ = {"pdf": "SETTINGS-LOOK", "look": "SETTINGS-LOOK", "layout": "SETTINGS-B"}
_READ = {"layout": ("contact_tables",)}  # a key of a not-yet-read table that a build already reads
_PAPER_KEYS = ("default", "formats")
_TABLES = ("paper", "pdf", "look", "layout", "grid", "font")


class SettingsError(Exception):
    """A settings file or `paper=` is wrong; the message names the file, the key and the fix."""


def known(keys: Iterable[str]) -> str:
    return ", ".join(keys) or "none yet"


def _sub(table: Table, key: str) -> Table:
    """The sub-table `key` of `table`, empty when absent."""
    return cast("Table", table.get(key, {}))


def _refuse_unread(ours: Table, consumer: Table, where: str) -> None:
    """Raise for a consumer key in a table nothing reads yet, or one we do not know."""
    for table, order in _NOT_READ.items():
        for key in _sub(consumer, table):
            if key in _READ.get(table, ()):
                continue
            if key not in _sub(ours, table):
                names = known(_sub(ours, table))
                msg = f'{where} [{table}] "{key}" is not a setting; known: {names}'
            else:
                msg = f'{where} [{table}] "{key}" is not read yet: it arrives with {order}'
            raise SettingsError(msg)


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


def _merged_layout(given: Table, where: str) -> dict[str, object]:
    """The `[layout]` keys a build reads today: `contact_tables`, a boolean."""
    for key, value in given.items():
        if key in _READ["layout"] and not isinstance(value, bool):
            msg = f'{where} [layout] "{key}" must be true or false, got {value!r}'
            raise SettingsError(msg)
    return {key: value for key, value in given.items() if key in _READ["layout"]}


def merged_tables(ours: Table, consumer: Table, where: str) -> dict[str, dict[str, object]]:
    """Our tables with the consumer's file on top, key by key; raises `SettingsError`."""
    for table in consumer:
        if table not in _TABLES:
            msg = f"{where} table [{table}] is not a settings table; known: {known(_TABLES)}"
            raise SettingsError(msg)
    _refuse_unread(ours, consumer, where)
    tables = {name: dict(_sub(ours, name)) for name in ("pdf", "look", "layout")}
    tables["layout"] |= _merged_layout(_sub(consumer, "layout"), where)
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
