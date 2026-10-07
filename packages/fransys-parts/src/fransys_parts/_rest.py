"""Parts lints for the rest state of a switched link (spec F2).

Codes: `SWITCHED_LINK_WITHOUT_REST`, `REST_ON_UNSWITCHED_LINK`, `REST_DISAGREES_WITH_KIND`,
`CONTACT_WITHOUT_SWITCHED_LINK` and `SYMBOL_REST_MISMATCH`. The symbol table is static:
a symbol not in it is not checked.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import _toml

if TYPE_CHECKING:
    from fransys_model.kernel import Finding

# A contact kind that implies its rest state; a changeover implies it per throw, by roles.
_IMPLIED = {"contact_no": "open", "contact_nc": "closed"}
_DECLARES = frozenset({"switch", "generic"})
_CONTACTS = frozenset({"contact_no", "contact_nc", "contact_co", "switch"})
_SYMBOL_REST = {"make-contact": "open", "break-contact": "closed", "emergency-stop": "closed"}


def _switched(entry: _toml.Table) -> list[dict[str, object]]:
    links = entry.get("links")
    if type(links) is not list:
        return []
    return [link for link in links if type(link) is dict and link.get("kind") == "switched"]


def _unswitched(entry: _toml.Table) -> list[dict[str, object]]:
    links = entry.get("links")
    if type(links) is not list:
        return []
    return [link for link in links if type(link) is dict and link.get("kind") != "switched"]


def _link_text(link: dict[str, object]) -> str:
    return f"link ({link.get('a')!r}, {link.get('b')!r})"


def check_rest(entry: _toml.Table, path: str, line: int) -> list[Finding]:
    """The four rest-state lints of one function entry."""
    kind = entry.get("kind")
    links = _switched(entry)
    findings = [
        *_check_unswitched(entry, path, line),
        *_check_switched(kind, links, path, line),
    ]
    if kind in _CONTACTS and not links:
        text = f"a {kind} function has no switched link"
        findings.append(_toml.finding("CONTACT_WITHOUT_SWITCHED_LINK", path, line, text))
    return [*findings, *_check_symbol(entry, kind, links, path, line)]


def _check_unswitched(entry: _toml.Table, path: str, line: int) -> list[Finding]:
    return [
        _toml.finding(
            "REST_ON_UNSWITCHED_LINK",
            path,
            line,
            f"{_link_text(link)} declares rest but is not switched",
        )
        for link in _unswitched(entry)
        if link.get("rest") is not None
    ]


def _check_switched(
    kind: object, links: list[dict[str, object]], path: str, line: int
) -> list[Finding]:
    findings = []
    implied = _IMPLIED.get(str(kind))
    for link in links:
        rest = link.get("rest")
        if kind in _DECLARES and rest is None:
            text = f"switched {_link_text(link)} of a {kind} function declares no rest state"
            findings.append(_toml.finding("SWITCHED_LINK_WITHOUT_REST", path, line, text))
        if implied and rest in ("open", "closed") and rest != implied:
            text = f"{_link_text(link)} is rest {rest!r} but a {kind} contact is {implied!r}"
            findings.append(_toml.finding("REST_DISAGREES_WITH_KIND", path, line, text))
    return findings


def _check_symbol(
    entry: _toml.Table, kind: object, links: list[dict[str, object]], path: str, line: int
) -> list[Finding]:
    """`SYMBOL_REST_MISMATCH`: a named symbol of a single rest state must be that state's."""
    symbol = entry.get("symbol")
    rests = {link.get("rest") or _IMPLIED.get(str(kind)) for link in links}
    if type(symbol) is not str or symbol not in _SYMBOL_REST or kind == "contact_co":
        return []
    if len(rests) != 1 or None in rests or rests == {_SYMBOL_REST[symbol]}:
        return []
    text = f"symbol {symbol!r} is rest {_SYMBOL_REST[symbol]!r} but the function is {rests.pop()!r}"
    return [_toml.finding("SYMBOL_REST_MISMATCH", path, line, text)]
