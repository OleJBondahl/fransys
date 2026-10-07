"""Header joins (parts-0017, HA4): a header port's `joins = "<function>.<port>"` and its lints.

The part file spells a join `<function>.<port>` of the same part; the model stores the target
port template's id on the header port's template.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fransys_model.kernel import Id, make_id
from fransys_model.vocab import PortTemplate

from . import _toml

if TYPE_CHECKING:
    from fransys_model.kernel import Finding


def target_id(part_key: tuple[str, ...], joins: str) -> Id[PortTemplate]:
    """The id of the port template `joins` names, in the part whose key is `part_key`."""
    function, _, port = joins.rpartition(".")
    return make_id(PortTemplate, (*part_key, "function", function, "port", port))


def _port_names(entry: _toml.Table) -> set[str]:
    ports = entry.get("ports")
    names = (p.get("name") for p in ports if type(p) is dict) if type(ports) is list else ()
    return {name for name in names if type(name) is str}


def _joins_of(entry: _toml.Table) -> list[tuple[object, str]]:
    ports = entry.get("ports")
    if type(ports) is not list:
        return []
    return [
        (p.get("name"), p["joins"])
        for p in ports
        if type(p) is dict and type(p.get("joins")) is str
    ]


def _refusal(
    who: str, joins: str, ports_of: dict[str, set[str]], kind_of: dict[str, object]
) -> tuple[str, str] | None:
    function, _, target = joins.rpartition(".")
    if target not in ports_of.get(function, ()):
        return "JOIN_PORT_UNKNOWN", f"{who}, which is no port of this part"
    if kind_of[function] == "connector":
        return "JOIN_INTO_CONNECTOR", f"{who}, a port of a connector function"
    return None


def check(functions: list[object], path: str, origins: _toml.Origins) -> list[Finding]:
    """`JOIN_PORT_UNKNOWN`, `JOIN_INTO_CONNECTOR`, `JOIN_PORT_TWICE` over one part's functions."""
    tables = [t for t in functions if isinstance(t, dict) and isinstance(t.get("name"), str)]
    ports_of = {t["name"]: _port_names(t) for t in tables}
    kind_of = {t["name"]: t.get("kind") for t in tables}
    taken: set[str] = set()
    findings: list[Finding] = []
    for index, entry in enumerate(functions):
        line = origins.get(("function", index), 1)
        for port, joins in _joins_of(entry) if isinstance(entry, dict) else ():
            who = f"port {port!r} joins {joins!r}"
            refused = _refusal(who, joins, ports_of, kind_of)
            if refused is None and joins in taken:
                refused = "JOIN_PORT_TWICE", f"{who}, which another header pin already joins"
            taken.add(joins)
            if refused is not None:
                findings.append(_toml.finding(refused[0], path, line, refused[1]))
    return findings
