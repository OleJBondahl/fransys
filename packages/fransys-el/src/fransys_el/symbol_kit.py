"""The symbol kit of a model: the symbol that draws each function drawn alone (el-0005).

A copy of the schematic engine's pick (`stages/resolve`, `read/functions`), kept until the flip
(SB9). A function that draws as a box, and an item box, are `symbol_boxes` (el-0006). The pin
and pole-group views are not here.
"""

from typing import TYPE_CHECKING

from fransys_layout.symbols import library_symbol
from fransys_model.derive import (
    actuated_group,
    actuator_each_contact,
    changeover_throws,
    connected_ports,
    connector_facets,
    function_ports,
    lead_switch,
    link_state,
    operated_by,
    pole_gangs,
    schematic_functions,
    undrawn_functions,
)
from fransys_model.derive.drawing_text import pole_prefix
from fransys_model.kernel import UnionFind
from fransys_model.vocab import (
    FunctionKind,
    LinkKind,
    function_poles,
    function_templates,
    functions,
    internal_links,
    items,
    pole_order,
    port_templates,
    ports,
)

from .placement_ids import symbol_key
from .placement_kit import Pick, SymbolKit, refuse
from .symbol_bind import Part, Shape, Target, member_of, port_of, through_ports
from .symbol_boxes import box_picks
from .symbol_pins import Choice, pin_picks
from .symbol_rules import Facts, symbol_for
from .symbol_unknown import is_unknown

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library
    from fransys_layout.symbols import LibrarySymbol
    from fransys_model.derive import PoleGang
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function, Pole, Port

__all__ = ["symbol_kit", "unknown_symbols"]

# Drawn as a pin view or a channel of a module box, never alone: the view facts are KIT-FACTS.
PIN, CHANNEL = "pin", "channel"
_VIEWED = {FunctionKind.CONNECTOR: PIN, FunctionKind.PLC_CHANNEL: CHANNEL}


def _function_poles(model: Model, function: Function) -> tuple[Pole, ...]:
    own = {t.id: t for t in port_templates(model).values() if t.function == function.template}
    links = [k for k in internal_links(model).values() if k.a in own and k.b in own]
    return function_poles(function.kind, links, own) or pole_order(links, own)


def _rest(model: Model, function: Function) -> str | None:
    own = {t.id: t for t in port_templates(model).values() if t.function == function.template}
    switched = [
        k
        for k in internal_links(model).values()
        if k.kind is LinkKind.SWITCHED and k.a in own and k.b in own
    ]
    if not switched:
        return None
    ends = {end.id for end in pole_order(switched, own)[0].ends}
    first = next(k for k in switched if {k.a, k.b} == ends)
    return link_state(model, function.id, first.id)


def _actuator(model: Model, function: Function) -> bool:
    """Whether the switch draws its device's actuator (ACTUATOR-ONCE, layout-0237)."""
    unit = items(model)[function.item].unit
    if actuator_each_contact(model, unit) or len(actuated_group(model, function.id)) < 2:  # noqa: PLR2004 -- a group of one draws as a single
        return True
    return lead_switch(model, function.id) == function.id


def _facts(model: Model, function: Function) -> Facts:
    template = function.template
    protection = None if template is None else function_templates(model)[template].protection_type
    facet = None if template is None else connector_facets(model).get(template)
    operator = operated_by(model, function.id)
    return Facts(
        function.kind.value,
        _rest(model, function),
        None if protection is None else protection.value,
        None if facet is None or facet.gender is None else facet.gender.value,
        None if operator is None else operator.value,
        _actuator(model, function),
    )


def _shape(model: Model, function: Function, found: tuple[Pole, ...]) -> Shape:
    """The pole count and pole pairs `poles_and_pairs` gives, and each changeover port's throw."""
    names = [(p.ends[0].name, p.ends[1].name) for p in found]
    linked: UnionFind[str] = UnionFind()
    for line, load in names:
        linked.union(line, load)
    groups: dict[str, list[tuple[str, str]]] = {linked.find(a): [] for a, _ in names}
    for line, load in names:
        groups[linked.find(line)].append((line, load))
    pairs = tuple(
        (i, g[0][0], g[0][1])
        for i, g in enumerate(groups.values())
        if len({n for pole in g for n in pole}) == 2  # noqa: PLR2004 -- a pair is two names
    )
    return Shape(len(groups) or 1, pairs, _throws(model, function, found))


def _throws(
    model: Model, function: Function, found: tuple[Pole, ...]
) -> dict[str, tuple[str, int]]:
    """Each changeover port name to its throw and the pole of its common."""
    if function.kind is not FunctionKind.CONTACT_CO:
        return {}
    names = {pid: p.name for pid, p in ports(model).items()}
    first: dict[str, int] = {}
    for index, pole in enumerate(found):
        for end in pole.ends:
            first.setdefault(end.name, index)
    poles = sorted(changeover_throws(model, function.id), key=lambda t: first[names[t.common]])
    thrown: dict[str, tuple[str, int]] = {}
    for index, pole in enumerate(poles):
        thrown[names[pole.common]] = ("common", index)
        thrown.update((names[p], ("break", index)) for p in pole.breaks)
        thrown.update((names[p], ("make", index)) for p in pole.makes)
    return thrown


def _bind_part(
    part: Part, symbol: str, at: tuple[Model, set[str], LibrarySymbol], taken: set[str]
) -> dict[Id[Port], str]:
    """The symbol port of each model port of `part`, none already in `taken`."""
    model, symbol_ports, drawn = at
    names = {pid: ports(model)[pid].name for pid in function_ports(model, part.function)}
    through = {}
    ends = through_ports(drawn, part.shape.poles)
    if ends is not None:
        for index, first, second in part.shape.pairs:
            prefix = pole_prefix(index, part.shape.poles)
            through[first] = prefix + ends[0]
            through[second] = prefix + ends[1]
    bound = {}
    for pid, name in names.items():
        at_part = Target(symbol_ports, through, len(names))
        chosen = port_of(name, part.shape, part.port_map, at_part)
        if chosen not in symbol_ports or chosen in taken or chosen in bound.values():
            refuse(
                f"function {part.function} port {name}",
                f"no free port on symbol {symbol}",
                symbol_key(model, part.function),
            )
        bound[pid] = chosen
    return bound


def bind(
    symbol: str, parts: tuple[Part, ...], model_and_library: tuple[Model, Library]
) -> tuple[str, int, frozendict[Id[Port], str]]:
    """The symbol, its pole count and the port binding of every part (one function, or a gang)."""
    model, library = model_and_library
    poles = parts[0].shape.poles
    drawn = library_symbol(library, symbol, poles)
    symbol_ports = {p.id for p in drawn.ports}
    bound: dict[Id[Port], str] = {}
    for part in parts:
        bound.update(_bind_part(part, symbol, (model, symbol_ports, drawn), set(bound.values())))
    return symbol, poles, frozendict(bound)


def _parts(
    model: Model,
    table: Mapping[Id[Function], Function],
    function: Function,
    port_map: frozendict[str, str],
    gang: PoleGang | None,
) -> tuple[Part, ...]:
    """The function's binding part; a gang binds every member as one pole of the lead's symbol."""
    if gang is None:
        shape = _shape(model, function, _function_poles(model, function))
        return (Part(function.id, shape, port_map),)
    parts = []
    for pole, member in enumerate(table[f] for f in gang.members):
        shape = _shape(model, member, _function_poles(model, member))
        parts.append(
            Part(
                member.id,
                member_of(shape, pole, gang.poles),
                port_map if pole == 0 else frozendict(),
            )
        )
    return tuple(parts)


def _pick(bound: tuple[str, int, frozendict[Id[Port], str]], gang: PoleGang | None) -> Pick:
    """The pick of a bound symbol; a gang's later members ride on its lead."""
    return Pick(*bound, () if gang is None else gang.members[1:])


def _gangs(
    model: Model,
    order: list[Id[Function]],
    chosen: Mapping[Id[Function], tuple[str | None, object]],
) -> dict[Id[Function], PoleGang]:
    """Each gang whose lead draws as a library symbol, by its lead (`derive.pole_gangs`)."""
    return {
        g.lead: g for g in pole_gangs(model, frozenset(order)) if chosen.get(g.lead, (None,))[0]
    }


def _order(model: Model) -> list[Id[Function]]:
    """The drawn functions in schematic order: the accessory's own are not drawn."""
    accessory = undrawn_functions(model, hide_unused_pins=False, wired=frozenset()).accessory
    return [f for f in schematic_functions(model) if f not in accessory]


def _scope(model: Model) -> tuple[list[Id[Function]], Mapping[Id[Function], Function]]:
    """The drawn functions in order, and every function by id."""
    return _order(model), functions(model)


def _views(
    order: list[Id[Function]], table: Mapping[Id[Function], Function]
) -> dict[Id[Function], str | None]:
    """How each function is viewed: `PIN`, `CHANNEL` or `None` (drawn alone)."""
    return {f: _VIEWED.get(table[f].kind) for f in order}


def _raw_choices(
    model: Model, order: list[Id[Function]], table: Mapping[Id[Function], Function]
) -> dict[Id[Function], Choice]:
    """The symbol key and port map the choice or the table gives each function a symbol may draw."""
    viewed = _views(order, table)
    return {
        f: symbol_for(model, table[f], items(model)[table[f].item].part, _facts(model, table[f]))
        for f in order
        if viewed[f] != CHANNEL
    }


def _chosen(
    model: Model,
    library: Library,
    order: list[Id[Function]],
    table: Mapping[Id[Function], Function],
) -> dict[Id[Function], Choice]:
    """The choices, a key the library lacks as none: that function draws as a box (el-0039)."""
    return {
        f: (None, pm) if key is not None and is_unknown(library, key) else (key, pm)
        for f, (key, pm) in _raw_choices(model, order, table).items()
    }


def unknown_symbols(model: Model, library: Library) -> dict[Id[Function], str]:
    """Each function whose chosen symbol key `library` lacks, with that key."""
    return {
        f: key
        for f, (key, _) in _raw_choices(model, *_scope(model)).items()
        if key is not None and is_unknown(library, key)
    }


def _alone(
    model: Model,
    library: Library,
    order: list[Id[Function]],
    table: Mapping[Id[Function], Function],
) -> tuple[dict[Id[Function], Pick], list[Function], list[Function], dict[Id[Function], Choice]]:
    """The picks of the functions a symbol draws alone, those no symbol draws, and the channels."""
    viewed = _views(order, table)
    chosen = _chosen(model, library, order, table)
    gangs = _gangs(model, order, chosen)
    later = {m for gang in gangs.values() for m in gang.members[1:]}
    kit: dict[Id[Function], Pick] = {}
    boxed: list[Function] = []
    for function in (table[f] for f in chosen if f not in later and viewed[f] is None):
        symbol, port_map = chosen[function.id]
        if symbol is None:
            boxed.append(function)
        else:
            gang = gangs.get(function.id)
            parts = _parts(model, table, function, port_map, gang)
            kit[function.id] = _pick(bind(symbol, parts, (model, library)), gang)
    pins = {f: c for f, c in chosen.items() if viewed[f] == PIN}
    return kit, boxed, [table[f] for f in order if viewed[f] == CHANNEL], pins


def symbol_kit(model: Model, library: Library) -> SymbolKit:
    """The pick of each function of `model` a symbol draws alone (choice, then the table).

    `library` is the build's: the symbols are bound by the ports it holds (SETTINGS ST4). A pole
    group is the lead's pick, with the other members listed and bound as its later poles. A PLC
    channel joins the generic boxes (`symbol_boxes`) and a connector pin is its own pick keyed by
    its port (`symbol_pins`); both read `derive.connected_ports` (el-0014).
    """
    order, table = _scope(model)
    kit, boxed, channels, pins = _alone(model, library, order, table)
    wired = connected_ports(model)
    boxes = box_picks(model, [*boxed, *channels], {c.id for c in channels}, wired)
    return frozendict({**kit, **boxes, **pin_picks(model, library, wired, pins)})
