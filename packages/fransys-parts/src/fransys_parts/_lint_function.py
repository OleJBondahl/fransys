"""Checks of the `[[function]]` entries of one part file and their facets (`FUNCTION_*`, `PORT_NAME_SHARED`, `CONNECTOR_*`, `PLC_*`)."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.derive import connector_label, connector_segments

from . import _changeover, _fields, _function_facts, _joins, _lint_ports, _port_connector, _ratings, _toml

if TYPE_CHECKING:
    from fransys_model.kernel import Finding

_SYMBOL_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@dataclass(slots=True)
class _FunctionState:
    """What one part's functions are checked against each other with, in function order."""

    names_seen: set[str]
    plc_seen: set[tuple[object, object]]
    port_holders: dict[str, list[tuple[str, str]]]
    labels_seen: dict[str, str]
    segments: tuple[str, ...]


def check_functions(data: _toml.Table, path: str, origins: _toml.Origins) -> list[Finding]:
    if "function" not in data:
        return []
    functions = data["function"]
    if type(functions) is not list:
        return [_toml.finding("FIELD_TYPE", path, 1, "function must be an array of tables")]
    findings: list[Finding] = []
    segments = connector_segments(_connector_label(e) if type(e) is dict else None for e in functions)
    state = _FunctionState(names_seen=set(), plc_seen=set(), port_holders={}, labels_seen={}, segments=segments)
    for index, entry in enumerate(functions):
        line = origins.get(("function", index), 1)
        if not isinstance(entry, dict):  # isinstance narrows to a dict ty accepts as a Table
            findings.append(_toml.finding("FIELD_TYPE", path, line, "function entry must be a table"))
            continue
        findings.extend(_check_function_entry(entry, path, line, state, index))
        findings.extend(_ratings.check_function_tables(entry, path, origins, index, line))
    return [*findings, *_joins.check(functions, path, origins), *_port_connector.refusals(functions, path, origins)]


def _check_function_entry(entry: _toml.Table, path: str, line: int, state: _FunctionState, index: int) -> list[Finding]:
    sub_tables = ("connector", "plc_channel", "rating", "operating", "block")
    body = {k: v for k, v in entry.items() if k not in sub_tables}
    findings = _fields.check_fields(body, _fields.FUNCTION_FIELDS, path=path, line=line, table_name="function")
    findings.extend(_check_name_and_symbol(entry, path, line, state))
    findings.extend(_lint_ports.check_ports(entry, entry.get("symbol"), path, line))
    findings.extend(_check_port_names_shared(entry, path, line, state, index))
    findings.extend(_lint_ports.check_links(entry, path, line))
    findings.extend(_changeover.check(entry, path, line))
    findings.extend(_function_facts.check(entry, path, line))
    findings.extend(_check_connector_facet(entry, path, line))
    findings.extend(_check_connector_marking_reused(entry, path, line, state))
    findings.extend(_check_plc_channel_facet(entry, path, line, state.plc_seen))
    return findings


def _check_name_and_symbol(entry: _toml.Table, path: str, line: int, state: _FunctionState) -> list[Finding]:
    findings: list[Finding] = []
    name = entry.get("name")
    if type(name) is str:
        if name in state.names_seen:
            findings.append(_toml.finding("FUNCTION_NAME_DUPLICATE", path, line, f"function name {name!r} repeats within this part"))
        state.names_seen.add(name)
    symbol = entry.get("symbol")
    if type(symbol) is str and _SYMBOL_SLUG.fullmatch(symbol) is None:
        findings.append(_toml.finding("SYMBOL_SLUG", path, line, f"symbol {symbol!r} must be a lowercase, hyphenated slug"))
    return findings


def _connector_label(entry: _toml.Table) -> str | None:
    """The label a connector function prints, or `None` (parts-0003, `derive.connector_label`).

    `None` too for a non-string `marking` (`FIELD_TYPE` reports it); the rule is `derive`'s.
    """
    name = entry.get("name")
    if entry.get("kind") != "connector" or type(name) is not str:
        return None
    connector = entry.get("connector")
    marking = connector.get("marking") if type(connector) is dict else None
    if marking is not None and type(marking) is not str:
        return None
    return connector_label(marking, name)


def _check_port_names_shared(entry: _toml.Table, path: str, line: int, state: _FunctionState, index: int) -> list[Finding]:
    """`PORT_NAME_SHARED`: same-named ports of two functions print one designation (parts-0005).

    A port prints `<item><segment>:<name>`; `derive.connector_segments` decides the segment.
    """
    ports = entry.get("ports")
    if type(ports) is not list:
        return []
    name = entry.get("name")
    function = name if type(name) is str else "<unnamed>"
    segment = state.segments[index]
    findings: list[Finding] = []
    named = (p.get("name") for p in ports if type(p) is dict)
    for port_name in dict.fromkeys(n for n in named if type(n) is str):
        holders = state.port_holders.setdefault(port_name, [])
        clash = next((h for h, other in holders if other == segment), None)
        if clash is not None:
            findings.append(
                _toml.finding(
                    "PORT_NAME_SHARED",
                    path,
                    line,
                    f"port name {port_name!r} is on both function {clash!r} and function "
                    f"{function!r}, which would print one designation, "
                    f"{f'<item>{segment}:{port_name}'!r}",
                )
            )
        holders.append((function, segment))
    return findings


def _check_connector_marking_reused(entry: _toml.Table, path: str, line: int, state: _FunctionState) -> list[Finding]:
    """`CONNECTOR_MARKING_REUSED`: two connector functions of one part print one label."""
    label = _connector_label(entry)
    if label is None:
        return []
    name = entry["name"]
    earlier = state.labels_seen.get(label)
    if earlier is None:
        state.labels_seen[label] = name
        return []
    return [
        _toml.finding(
            "CONNECTOR_MARKING_REUSED",
            path,
            line,
            f"connector label {label!r} is printed by both function {earlier!r} and function {name!r}",
        )
    ]


def _check_connector_facet(entry: _toml.Table, path: str, line: int) -> list[Finding]:
    if "connector" not in entry:
        return []
    connector = entry["connector"]
    findings = _fields.check_fields(connector, _fields.CONNECTOR_FIELDS, path=path, line=line, table_name="function.connector")
    well_formed = not findings
    if entry.get("kind") != "connector":
        findings.append(
            _toml.finding(
                "FACET_KIND_MISMATCH",
                path,
                line,
                "[function.connector] is set on a function whose kind is not connector",
            )
        )
    if well_formed:
        try:
            _fields.connector_of(connector)
        except TypeError as error:
            findings.append(_toml.finding("FIELD_TYPE", path, line, f"function.connector: {error}"))
    return findings


def _check_plc_channel_facet(entry: _toml.Table, path: str, line: int, plc_seen: set[tuple[object, object]]) -> list[Finding]:
    if "plc_channel" not in entry:
        return []
    plc = entry["plc_channel"]
    findings = _fields.check_fields(plc, _fields.PLC_CHANNEL_FIELDS, path=path, line=line, table_name="function.plc_channel")
    if entry.get("kind") != "plc_channel":
        findings.append(
            _toml.finding(
                "FACET_KIND_MISMATCH",
                path,
                line,
                "[function.plc_channel] is set on a function whose kind is not plc_channel",
            )
        )
    if type(plc) is dict:
        dup_key = (plc.get("channel"), plc.get("signal"))
        if dup_key in plc_seen:
            findings.append(
                _toml.finding(
                    "PLC_CHANNEL_DUPLICATE",
                    path,
                    line,
                    f"channel {dup_key[0]!r} signal {dup_key[1]!r} repeats within this part",
                )
            )
        else:
            plc_seen.add(dup_key)
    return findings
