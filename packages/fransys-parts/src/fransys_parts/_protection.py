"""Protection lints: `PROTECTION_LINK_KIND`, `PROTECTION_WITHOUT_TYPE`, `SYMBOL_TYPE_MISMATCH`.

`PROTECTION_TYPE_ON_NON_PROTECTION` keeps the loader from reaching the model's refusal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fransys_model.kernel import Severity

from . import _fields, _toml

if TYPE_CHECKING:
    from fransys_model.kernel import Finding


# Each type's through-link kind, how its device reads in a message, and why it has that kind.
_OPENS = "opens the circuit"
_TYPE_KIND = {
    "fuse": ("protective", "a fuse", _OPENS),
    "mcb": ("protective", "an mcb", _OPENS),
    "motor_breaker": ("protective", "a motor breaker", _OPENS),
    "rcd": ("protective", "an rcd", _OPENS),
    "overload": ("conductive", "an overload", "never opens its main path"),
}


def _link_text(link: _toml.Table, declared: object) -> str | None:
    """The message for a link whose kind does not fit, else None."""
    kind = link.get("kind")
    head = f"link ({link.get('a')!r}, {link.get('b')!r}) of "
    if kind == "switched":
        return (
            f"{head}a protection function is switched: "
            "a fuse or breaker is closed in service, so its link is protective or conductive"
        )
    if type(declared) is not str or declared not in _TYPE_KIND:
        return None
    want, noun, why = _TYPE_KIND[declared]
    if kind == want or kind not in ("protective", "conductive"):
        return None
    return f'{head}{noun} is {kind}: {noun} {why}, so write kind = "{want}"'


def check_protection_links(entry: _toml.Table, path: str, line: int) -> list[Finding]:
    """`PROTECTION_LINK_KIND`: a through link is switched, or lacks its type's kind."""
    links = entry.get("links")
    if entry.get("kind") != "protection" or type(links) is not list:
        return []
    table = entry.get("protection")
    declared = table.get("type") if type(table) is dict else None
    texts = (_link_text(link, declared) for link in links if type(link) is dict)
    return [_toml.finding("PROTECTION_LINK_KIND", path, line, text) for text in texts if text]


# A symbol that is one protection type's; a symbol not in it is not checked.
_SYMBOL_TYPE = {"fuse": "fuse", "circuit-breaker": "mcb"}


def _type_off_protection(entry: _toml.Table, table: object, path: str, line: int) -> list[Finding]:
    """`PROTECTION_TYPE_ON_NON_PROTECTION`: the model refuses a type on any other kind."""
    if type(table) is not dict or table.get("type") is None:
        return []
    text = f"a {entry.get('kind')} function declares a [function.protection] type"
    return [_toml.finding("PROTECTION_TYPE_ON_NON_PROTECTION", path, line, text)]


def check_protection_type(entry: _toml.Table, path: str, line: int) -> list[Finding]:
    """The `[function.protection]` table, `PROTECTION_WITHOUT_TYPE` and `SYMBOL_TYPE_MISMATCH`."""
    table = entry.get("protection")
    findings = []
    if table is not None:
        findings = _fields.check_fields(
            table, _fields.PROTECTION_FIELDS, path=path, line=line, table_name="function.protection"
        )
    if entry.get("kind") != "protection":
        return [*findings, *_type_off_protection(entry, table, path, line)]
    declared = table.get("type") if type(table) is dict else None
    symbol = entry.get("symbol")
    if declared is None:
        text = "a protection function declares no [function.protection] type"
        warning = _toml.finding(
            "PROTECTION_WITHOUT_TYPE", path, line, text, severity=Severity.WARNING
        )
        return [*findings, warning]
    if symbol in _SYMBOL_TYPE and _SYMBOL_TYPE[symbol] != declared:
        text = f"symbol {symbol!r} is a {_SYMBOL_TYPE[symbol]!r} but the type is {declared!r}"
        findings.append(_toml.finding("SYMBOL_TYPE_MISMATCH", path, line, text))
    return findings
