"""The changeover lints of one `contact_co` function: its roles, links and symbol ports (CS3)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import _toml

if TYPE_CHECKING:
    from fransys_model.kernel import Finding

_THROW_ROLES: frozenset[str] = frozenset({"common", "break", "make"})
_CHANGEOVER_PAIRS: tuple[set[str], ...] = ({"common", "break"}, {"common", "make"})


def check(entry: _toml.Table, path: str, line: int) -> list[Finding]:
    """`CHANGEOVER_ROLE`, `CHANGEOVER_LINK` and `CHANGEOVER_SYMBOL_PORT` of one function entry."""
    return [
        *_check_changeover_roles(entry, path, line),
        *_check_changeover_links(entry, path, line),
        *_check_changeover_symbol_port(entry, path, line),
    ]


def _check_changeover_roles(entry: _toml.Table, path: str, line: int) -> list[Finding]:
    """`CHANGEOVER_ROLE`: a `contact_co` port whose role is no throw role (parts-0007).

    A missing or non-string role is `FIELD_MISSING` / `FIELD_TYPE`'s to report, not this check's.
    """
    ports = entry.get("ports")
    if entry.get("kind") != "contact_co" or type(ports) is not list:
        return []
    return [
        _toml.finding(
            "CHANGEOVER_ROLE",
            path,
            line,
            f"port {port.get('name')!r} of a contact_co function has role {port['role']!r}, "
            f"not one of {', '.join(sorted(_THROW_ROLES))}",
        )
        for port in ports
        if type(port) is dict and type(port.get("role")) is str and port["role"] not in _THROW_ROLES
    ]


def _check_changeover_symbol_port(entry: _toml.Table, path: str, line: int) -> list[Finding]:
    """`CHANGEOVER_SYMBOL_PORT`: a `symbol_port` on a `contact_co` port (CS3, parts-0007).

    The drawing binds a changeover by its throw roles; a `symbol_port` would be a second fact.
    """
    ports = entry.get("ports")
    if entry.get("kind") != "contact_co" or type(ports) is not list:
        return []
    return [
        _toml.finding(
            "CHANGEOVER_SYMBOL_PORT",
            path,
            line,
            f"port {port.get('name')!r} of a contact_co function has symbol_port "
            f"{port['symbol_port']!r}: the drawing binds it by its role",
        )
        for port in ports
        if type(port) is dict and "symbol_port" in port
    ]


def _check_changeover_links(entry: _toml.Table, path: str, line: int) -> list[Finding]:
    """`CHANGEOVER_LINK`: a `switched` link of a `contact_co` that is not common-to-throw.

    Skipped: unknown port, no string role, one port at both ends (other codes report those).
    """
    ports, links = entry.get("ports"), entry.get("links")
    if entry.get("kind") != "contact_co" or type(ports) is not list or type(links) is not list:
        return []
    roles = {
        p["name"]: p["role"]
        for p in ports
        if type(p) is dict and type(p.get("name")) is str and type(p.get("role")) is str
    }
    findings: list[Finding] = []
    for link in links:
        if type(link) is not dict or link.get("kind") != "switched":
            continue
        a, b = link.get("a"), link.get("b")
        if type(a) is not str or type(b) is not str or a == b or a not in roles or b not in roles:
            continue
        if {roles[a], roles[b]} not in _CHANGEOVER_PAIRS:
            findings.append(
                _toml.finding(
                    "CHANGEOVER_LINK",
                    path,
                    line,
                    f"switched link ({a!r}, {b!r}) of a contact_co function joins roles "
                    f"{roles[a]!r} and {roles[b]!r}, not a common port to a break or make port",
                )
            )
    return findings
