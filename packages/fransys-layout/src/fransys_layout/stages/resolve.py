"""Stage 1, resolve: choose the symbol each function is drawn with (docs/design/stages.md 6.1)."""

from typing import TYPE_CHECKING, Any, NamedTuple
lazy from collections.abc import Set as AbstractSet

from fransys_layout.geometry import (
    Facing,
    HintError,
    Orientation,
    SymbolGeometry,
    SymbolPortError,
    generic_box_geometry,
    symbol_geometry,
)
from fransys_model.kernel import Finding, Severity, UnionFind

from .slices import by_key
from .types import DrawnFunction, DrawnPort, PolePair

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

    from fransys_model.kernel import Id

    from .types import FunctionSpec, PortSpec, SymbolChoice, SymbolRule

SYMBOL_DEFAULTED = "SYMBOL_DEFAULTED"
PIN_MAP_INCOMPLETE = "PIN_MAP_INCOMPLETE"
_POLE_PAIR_SIZE = 2
# The `change-over-contact` symbol's port for each throw (a test pins the three names,
# CONTACT-STATES CS3). `PortSpec.throw` holds the model's `PortRole` value as a string
# (`engines.schematic.read.roles`); the stage sees only strings, and finds a changeover by
# `KindRoles.contact_changeover`, never by kind.
THROW_SYMBOL_PORTS: Mapping[str, str] = frozendict({"common": "com", "break": "nc", "make": "no"})


# layout-0105: `(kind, rest, protection_type)` to a symbol key or `None`; the engine passes it
type DefaultSymbol = Callable[[str, str | None, str | None], str | None]


def resolve(
    functions: tuple[FunctionSpec, ...],
    *,
    rules: tuple[SymbolRule, ...],
    choices: tuple[SymbolChoice, ...],
    default_symbol: DefaultSymbol | None = None,
) -> tuple[tuple[DrawnFunction, ...], tuple[Finding, ...]]:
    """Choose symbol, pole count and port binding for every function (stages 6.1, step-1 rules)."""
    table = {(rule.kind, rule.category, rule.gender): rule for rule in rules}
    index = choice_index(choices)
    drawn = []
    findings = []
    for spec in sorted(functions, key=lambda spec: spec.function):
        symbol, port_map = _symbol_for(spec, table, index, default_symbol)
        if symbol is None:
            geometry = generic_box_geometry(tuple(port.name for port in spec.ports))
            findings.append(
                Finding(
                    code=SYMBOL_DEFAULTED,
                    severity=Severity.INFO,
                    subjects=(spec.function,),
                    message=f"no symbol for function kind {spec.kind!r}: drawn as a labelled box",
                )
            )
        else:
            geometry = symbol_geometry(symbol, poles=spec.poles, orientation=Orientation.R0)
        primary_in, primary_out = _primary_ports(geometry)
        bound_ports = _bind_ports(spec, geometry, port_map)
        bound_names = {dp.symbol_port for dp in bound_ports}
        findings.extend(
            Finding(
                code=PIN_MAP_INCOMPLETE,
                severity=Severity.ERROR,
                subjects=(spec.function,),
                message=f"symbol {geometry.key!r} has no model port bound to {'/'.join(group)!r}",
            )
            for group in _incomplete_nodes(geometry, bound_names)
        )
        drawn.append(
            DrawnFunction(
                function=spec.function,
                item=spec.item,
                key=spec.key,
                kind=spec.kind,
                geometry=geometry,
                ports=bound_ports,
                primary_in=primary_in,
                primary_out=primary_out,
                roles=spec.roles,
            )
        )
    return tuple(drawn), tuple(findings)


def _incomplete_nodes(
    geometry: SymbolGeometry, bound_names: AbstractSet[str]
) -> tuple[tuple[str, ...], ...]:
    """Every node of `geometry` with none of its ports in `bound_names`, sorted."""
    listed = {name for node in geometry.nodes for name in node}
    singletons = ((port.name,) for port in geometry.ports if port.name not in listed)
    groups = (*geometry.nodes, *singletons)
    return tuple(sorted(g for g in groups if not any(name in bound_names for name in g)))


class ChoiceIndex(NamedTuple):
    """The symbol choices grouped once by what they name, each group in the choices' order."""

    by_function: dict[Id[Any] | None, tuple[SymbolChoice, ...]]
    by_part: dict[Id[Any] | None, tuple[SymbolChoice, ...]]
    by_kind: dict[str | None, tuple[SymbolChoice, ...]]


def choice_index(choices: tuple[SymbolChoice, ...]) -> ChoiceIndex:
    """Group `choices` by function, part and kind (`slices.by_key`), keeping their order."""
    return ChoiceIndex(
        by_key(choices, lambda choice: choice.function),
        by_key(choices, lambda choice: choice.part),
        by_key(choices, lambda choice: choice.kind),
    )


def _symbol_for(
    spec: FunctionSpec,
    table: Mapping[tuple[str, str | None, str | None], SymbolRule],
    index: ChoiceIndex,
    default_symbol: DefaultSymbol | None,
) -> tuple[str | None, frozendict[str, str]]:
    """Return the symbol key (`None`: no rule, no choice) and port map for one function."""
    levels = (
        index.by_function.get(spec.function, ()),
        index.by_part.get(spec.part, ()) if spec.part is not None else (),
        index.by_kind.get(spec.kind, ()),
    )
    for level in levels:
        if len(level) > 1:
            msg = f"{len(level)} symbol choices of one specificity apply to one function"
            raise HintError(msg, subjects=(spec.function, *sorted(c.choice for c in level)))
        if level:
            return level[0].symbol, level[0].port_map
    named = (
        None
        if default_symbol is None
        else default_symbol(spec.kind, spec.rest, spec.protection_type)
    )
    if named is not None:
        return named, frozendict(dict[str, str]())
    rule = table.get((spec.kind, spec.category, None)) if spec.category is not None else None
    if rule is None and spec.roles.gendered:
        rule = table.get((spec.kind, None, spec.gender))
    if rule is None:
        rule = table.get((spec.kind, None, None))
    if rule is None:
        return None, frozendict(dict[str, str]())
    return rule.symbol, rule.port_map


def _bind_ports(
    spec: FunctionSpec, geometry: SymbolGeometry, port_map: frozendict[str, str]
) -> tuple[DrawnPort, ...]:
    """Bind each model port to a symbol port: its throw, `port_map`, same name, or its pole pair."""
    symbol_ports = {port.name for port in geometry.ports}
    through_ports = _through_ports(spec, geometry)
    bound = {}
    for port in spec.ports:
        symbol_port = _throw_port(spec, port, port_map) or _named_port(
            spec, port, symbol_ports, port_map, through_ports
        )
        if symbol_port is None or symbol_port not in symbol_ports:
            msg = f"model port {port.name!r} has no port on symbol {geometry.key!r}"
            raise SymbolPortError(msg, function=spec.function, port_name=port.name)
        if symbol_port in bound:
            msg = f"two model ports are drawn at port {symbol_port!r} of symbol {geometry.key!r}"
            raise HintError(msg, subjects=(spec.function, bound[symbol_port].port, port.port))
        bound[symbol_port] = port
    return tuple(
        DrawnPort(
            port=p.port,
            symbol_port=name,
            ac=p.current == "ac",
            group=p.group,
            channel=p.channel,
            stand=p.stand,
        )
        for name, p in bound.items()
    )


def _named_port(
    spec: FunctionSpec,
    port: PortSpec,
    symbol_ports: AbstractSet[str],
    port_map: frozendict[str, str],
    through_ports: Mapping[str, str],
) -> str | None:
    """The symbol port `port` is drawn at by `port_map`, same name or its pole pair, else `None`."""
    if port.name in port_map:
        return port_map[port.name]
    if port.name in symbol_ports:
        return port.name
    if len(spec.ports) == 1 and len(symbol_ports) == 1:
        return next(iter(symbol_ports))  # C6: one port on one port (a PLC channel)
    return through_ports.get(port.name)


def throw_port(spec: FunctionSpec, port: PortSpec) -> str | None:
    """The symbol port a changeover port's throw role binds it to, `None` when it has no throw."""
    if not spec.roles.contact_changeover or port.throw is None:
        return None
    return THROW_SYMBOL_PORTS[port.throw]


def _throw_port(spec: FunctionSpec, port: PortSpec, port_map: frozendict[str, str]) -> str | None:
    """`throw_port`, refusing a `port_map` entry for a port whose throw binds it."""
    bound = throw_port(spec, port)
    if bound is not None and port.name in port_map:
        msg = f"port {port.name!r} of a changeover is bound by its throw role, not a port map"
        raise HintError(msg, subjects=(spec.function, port.port))
    return bound


def _through_ports(spec: FunctionSpec, geometry: SymbolGeometry) -> dict[str, str]:
    """Each pole pair's two model port names at the symbol's through path, `{}` without one."""
    found: dict[str, str] = {}
    if geometry.through is not None:
        for pair in spec.pole_pairs:
            prefix = f"{pair.index + 1}." if spec.poles > 1 else ""
            found[pair.first] = prefix + geometry.through.start
            found[pair.second] = prefix + geometry.through.end
    return found


def _primary_ports(geometry: SymbolGeometry) -> tuple[str | None, str | None]:
    """The symbol ports that continue a column: the through path, else first N and first S."""
    if geometry.through is not None:
        prefix = "1." if geometry.poles > 1 else ""
        return prefix + geometry.through.start, prefix + geometry.through.end
    north = next((port.name for port in geometry.ports if port.facing is Facing.N), None)
    south = next((port.name for port in geometry.ports if port.facing is Facing.S), None)
    return north, south


def poles_and_pairs(poles: Iterable[tuple[str, str]]) -> tuple[int, tuple[PolePair, ...]]:
    """Pole count and pairs from `(line, load)` names in pole order; a chain is one bare pole."""
    ordered = tuple(poles)
    linked: UnionFind[str] = UnionFind()
    for line, load in ordered:
        linked.union(line, load)
    groups = {linked.find(line): [] for line, _ in ordered}
    for line, load in ordered:
        groups[linked.find(line)].append((line, load))
    pairs = tuple(
        PolePair(index=index, first=group[0][0], second=group[0][1])
        for index, group in enumerate(groups.values())
        if len({name for pole in group for name in pole}) == _POLE_PAIR_SIZE
    )
    return len(groups) or 1, pairs
