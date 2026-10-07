"""Build one `[[function]]` entry's records into a Draft: template, ports, links, facets."""

from dataclasses import dataclass

from fransys_model.kernel import Draft, Id, Origin, make_id
from fransys_model.layout import SymbolChoice
from fransys_model.vocab import (
    ConnectorFacet,
    Energy,
    FunctionKind,
    FunctionTemplate,
    Gender,
    InternalLink,
    LinkKind,
    LinkRest,
    Part,
    PlcChannelFacet,
    PortRole,
    PortTemplate,
    ProtectionType,
    SignalType,
)

from . import _joins, _pole_facts, _ratings, _toml


@dataclass(frozen=True, slots=True)
class _PartContext:
    """A part's authoring key and id, threaded into its function builder."""

    key: tuple[str, ...]
    id: Id[Part]


def _protection_type(entry: _toml.Table) -> ProtectionType | None:
    table = entry.get("protection")
    return ProtectionType(table["type"]) if type(table) is dict and "type" in table else None


def _add_function_template(
    draft: Draft,
    entry: _toml.Table,
    function_key: tuple[str, ...],
    part_id: Id[Part],
    origin: Origin,
) -> None:
    draft.add(
        FunctionTemplate(
            id=make_id(FunctionTemplate, function_key),
            key=function_key,
            part=part_id,
            name=entry["name"],
            kind=FunctionKind(entry["kind"]),
            protection_type=_protection_type(entry),
            energy=Energy(entry["energy"]) if "energy" in entry else None,
        ),
        origin=origin,
    )


def _add_ports(
    draft: Draft,
    entry: _toml.Table,
    function_key: tuple[str, ...],
    function_id: Id[FunctionTemplate],
    origin: Origin,
) -> dict[str, Id[PortTemplate]]:
    port_ids: dict[str, Id[PortTemplate]] = {}
    for port in entry["ports"]:
        pole_side, conductor_mark = _pole_facts.facts(entry, port)
        port_key = (*function_key, "port", port["name"])
        port_id = make_id(PortTemplate, port_key)
        port_ids[port["name"]] = port_id
        draft.add(
            PortTemplate(
                id=port_id,
                key=port_key,
                function=function_id,
                name=port["name"],
                role=PortRole(port["role"]),
                # model-0053 (F2): the part's own pin marking, when it differs from the name
                marking=port.get("marking"),
                pole_side=pole_side,
                conductor_mark=conductor_mark,
                joins=_joins.target_id(function_key[:-2], port["joins"])
                if "joins" in port
                else None,
            ),
            origin=origin,
        )
    return port_ids


def _add_links(
    draft: Draft,
    entry: _toml.Table,
    function_key: tuple[str, ...],
    port_ids: dict[str, Id[PortTemplate]],
    origin: Origin,
) -> None:
    for link in entry.get("links", ()):
        link_key = (*function_key, "link", link["a"], link["b"])
        draft.add(
            InternalLink(
                id=make_id(InternalLink, link_key),
                key=link_key,
                a=port_ids[link["a"]],
                b=port_ids[link["b"]],
                kind=LinkKind(link["kind"]),
                rest=LinkRest(link["rest"]) if "rest" in link else None,
            ),
            origin=origin,
        )


def _add_symbol_choice(
    draft: Draft,
    entry: _toml.Table,
    function_key: tuple[str, ...],
    function_id: Id[FunctionTemplate],
    origin: Origin,
) -> None:
    symbol = entry.get("symbol")
    if symbol is None:
        return
    port_map = {
        port["name"]: port["symbol_port"]
        for port in entry["ports"]
        if "symbol_port" in port and port["symbol_port"] != port["name"]
    }
    choice_key = (*function_key, "symbol_choice")
    draft.add(
        SymbolChoice(
            id=make_id(SymbolChoice, choice_key),
            key=choice_key,
            function=None,
            template=function_id,
            part=None,
            kind=None,
            symbol=symbol,
            port_map=frozendict(port_map),
        ),
        origin=origin,
    )


def _add_connector(
    draft: Draft,
    entry: _toml.Table,
    function_key: tuple[str, ...],
    function_id: Id[FunctionTemplate],
    origin: Origin,
) -> None:
    connector = entry.get("connector")
    if connector is None:
        return
    key = (*function_key, "connector")
    draft.add(
        ConnectorFacet(
            id=make_id(ConnectorFacet, key),
            key=key,
            subject=function_id,
            style=connector["style"],
            pincount=connector["pincount"],
            gender=Gender(connector["gender"]) if "gender" in connector else None,
            marking=connector.get("marking"),
            mates=tuple(connector.get("mates", ())),
        ),
        origin=origin,
    )


def _add_plc_channel(
    draft: Draft,
    entry: _toml.Table,
    function_key: tuple[str, ...],
    function_id: Id[FunctionTemplate],
    origin: Origin,
) -> None:
    plc_channel = entry.get("plc_channel")
    if plc_channel is None:
        return
    key = (*function_key, "plc_channel")
    draft.add(
        PlcChannelFacet(
            id=make_id(PlcChannelFacet, key),
            key=key,
            subject=function_id,
            signal=SignalType(plc_channel["signal"]),
            channel=plc_channel["channel"],
        ),
        origin=origin,
    )


def _origin(parsed: _toml.ParsedFile, index: int, *path: object) -> Origin:
    function_line = parsed.origins.get(("function", index), 1)
    line = parsed.origins.get(("function", index, *path), function_line)
    return Origin(file=parsed.path, line=line, note="")


def _build_function(
    draft: Draft, entry: _toml.Table, index: int, part: _PartContext, parsed: _toml.ParsedFile
) -> None:
    origin = _origin(parsed, index)
    function_key = (*part.key, "function", entry["name"])
    function_id = make_id(FunctionTemplate, function_key)
    _add_function_template(draft, entry, function_key, part.id, origin)
    port_ids = _add_ports(draft, entry, function_key, function_id, origin)
    _add_links(draft, entry, function_key, port_ids, origin)
    _add_symbol_choice(draft, entry, function_key, function_id, origin)
    _add_connector(draft, entry, function_key, function_id, _origin(parsed, index, "connector"))
    _add_plc_channel(draft, entry, function_key, function_id, _origin(parsed, index, "plc_channel"))
    table_origins = {table: _origin(parsed, index, table) for table in ("rating", "operating")}
    _ratings.add_function_tables(draft, entry, function_id, function_key, table_origins)
