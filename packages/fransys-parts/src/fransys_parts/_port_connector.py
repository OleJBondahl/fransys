"""A port names its physical connector (parts-0025): `connector = "<function>.<pin>"` and its lints.

The part file spells the target like `joins`: a connector function of the same part, then the pin.
The model stores the function template's id and the pin on the port's template (model-0448).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fransys_model.elecdef import Connector
from fransys_model.kernel import Id, make_id
from fransys_model.vocab import FunctionTemplate

from . import _toml

if TYPE_CHECKING:
    from fransys_model.kernel import Finding


def target(part_key: tuple[str, ...], connector: str) -> tuple[Id[FunctionTemplate], str]:
    """The connector function template `connector` names, in the part whose key is `part_key`, and the pin."""
    function, _, pin = connector.rpartition(".")
    return make_id(FunctionTemplate, (*part_key, "function", function)), pin


def of_port(part_key: tuple[str, ...], port: _toml.Table) -> tuple[Id[FunctionTemplate] | None, str | None]:
    """The connector function template and pin a port's `connector` names, `(None, None)` when it names none."""
    return target(part_key, port["connector"]) if "connector" in port else (None, None)


def _ports(entry: _toml.Table) -> list[dict[str, object]]:
    ports = entry.get("ports")
    return [p for p in ports if type(p) is dict] if type(ports) is list else []


def _pins_of(entry: _toml.Table) -> tuple[str, ...] | None:
    """The pin names of a connector function's `[function.connector]`, `None` when it states no poles."""
    table = entry.get("connector")
    poles = table.get("poles") if type(table) is dict else None
    return tuple(pin.marking for pin in Connector(poles=poles).pins) if type(poles) is int and poles >= 1 else None


def _refusal(who: str, connector: str, pins_of: dict[str, tuple[str, ...] | None]) -> tuple[str, str] | None:
    function, _, pin = connector.rpartition(".")
    if function not in pins_of:
        return "PORT_PIN_NOT_ON_CONNECTOR", f"{who}, which is no connector function of this part"
    pins = pins_of[function]
    if pins is not None and pin not in pins:
        return "PORT_PIN_NOT_ON_CONNECTOR", f"{who}, but that connector has the pins {', '.join(pins)}"
    return None


def _port_refusal(
    entry: _toml.Table, port: dict[str, object], pins_of: dict[str, tuple[str, ...] | None], joined: set[object], taken: set[str]
) -> tuple[str, str] | None:
    connector = port.get("connector")
    if type(connector) is not str:
        return None
    who = f"port {port.get('name')!r} names connector {connector!r}"
    refused = _refusal(who, connector, pins_of)
    if refused is None and connector in taken:
        refused = "PORT_PIN_TAKEN", f"{who}, which another port already names"
    if refused is None and f"{entry['name']}.{port.get('name')}" in joined:
        refused = "PORT_CONNECTOR_AND_JOIN", f"{who}, and a header pin also joins it"
    taken.add(connector)
    return refused


def refusals(functions: list[object], path: str, origins: _toml.Origins) -> list[Finding]:
    """`PORT_PIN_NOT_ON_CONNECTOR`, `PORT_PIN_TAKEN`, `PORT_CONNECTOR_AND_JOIN` over one part's functions."""
    tables = {i: t for i, t in enumerate(functions) if isinstance(t, dict) and isinstance(t.get("name"), str)}
    pins_of = {t["name"]: _pins_of(t) for t in tables.values() if t.get("kind") == "connector"}
    joined = {p["joins"] for t in tables.values() for p in _ports(t) if type(p.get("joins")) is str}
    taken: set[str] = set()
    findings: list[Finding] = []
    for index, entry in tables.items():
        line = origins.get(("function", index), 1)
        refused = (_port_refusal(entry, port, pins_of, joined, taken) for port in _ports(entry))
        findings.extend(_toml.finding(found[0], path, line, found[1]) for found in filter(None, refused))
    return findings
