"""Protection lints: `PROTECTION_LINK_KIND`, `PROTECTION_WITHOUT_TYPE`, `SYMBOL_TYPE_MISMATCH`.

`PROTECTION_TYPE_ON_NON_PROTECTION` keeps the loader from reaching the model's refusal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fransys_model.kernel import Severity

from . import _fields, _toml

if TYPE_CHECKING:
    from fransys_model.kernel import Finding


def check_protection_links(entry: _toml.Table, path: str, line: int) -> list[Finding]:
    """`PROTECTION_LINK_KIND`: a protection function's through link is protective or conductive."""
    links = entry.get("links")
    if entry.get("kind") != "protection" or type(links) is not list:
        return []
    return [
        _toml.finding(
            "PROTECTION_LINK_KIND",
            path,
            line,
            f"link ({link.get('a')!r}, {link.get('b')!r}) of a protection function is switched: "
            "a fuse or breaker is closed in service, so its link is protective or conductive",
        )
        for link in links
        if type(link) is dict and link.get("kind") == "switched"
    ]


# A symbol that is one protection type's; a symbol not in it is not checked (spec F3).
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
