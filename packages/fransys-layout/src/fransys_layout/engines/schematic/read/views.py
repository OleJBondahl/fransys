"""Reads of the model for the item and pin views `read_inputs` draws (R7).

A connector is drawn as one view per pin (`pin_views`), an item of two or more defaulted
functions as one box (`item_views`); the `*_text` and `re*` helpers carry the views' tags and
the connections' ends over to them. `is_board_internal` and `item_of` are the board test the
connection filters in `connections.py` share.
"""

import dataclasses
from collections import defaultdict
from functools import partial
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Mapping
lazy from collections.abc import Set as AbstractSet

from fransys_layout.engines.schematic.defaults import DEFAULT_RULES, kind_roles
from fransys_layout.engines.schematic.read.item_sides import function_groups
from fransys_layout.lint.chains import mate_map
from fransys_layout.stages import FunctionSpec, PortRef, SymbolChoice
from fransys_layout.stages.resolve import _symbol_for, choice_index, throw_port
from fransys_layout.stages.types import MatedFunctions
from fransys_model.derive import enclosing_boards, is_sole_unit_root
from fransys_model.derive.designation import port_designation
from fransys_model.derive.drawing_text import item_tag_text
from fransys_model.kernel import SchemaError, parent_chain
from fransys_model.vocab import cable_items
from fransys_model.vocab.membership import boundary
from fransys_model.vocab.membership import units as unit_ids
from fransys_model.vocab.tables import functions as functions_table
from fransys_model.vocab.tables import items as items_table
from fransys_model.vocab.tables import mates as mates_table
from fransys_model.vocab.tables import ports as ports_table
from fransys_model.vocab.tables import unused_boundaries

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_layout.stages.resolve import ChoiceIndex
    from fransys_layout.stages.types import SymbolRule
    from fransys_model.kernel import AuthoringKey, Id, Model
    from fransys_model.vocab.core import Item


def box_drawn(
    spec: FunctionSpec,
    table: Mapping[tuple[str, str | None, str | None], SymbolRule],
    index: ChoiceIndex,
) -> bool:
    """Whether `spec` is a generic box: a PLC channel or a function no symbol rule names."""
    return spec.pin_function is None and (
        spec.kind == "plc_channel" or _symbol_for(spec, table, index, None)[0] is None
    )


def item_views(
    model: Model,
    specs: tuple[FunctionSpec, ...],
    choices: tuple[SymbolChoice, ...],
    wired: AbstractSet[Id[Any]],
) -> tuple[tuple[FunctionSpec, ...], dict[Id[Any], Id[Any]], tuple[SymbolChoice, ...]]:
    """R7 B2: every item of two or more drawn functions, all symbol-defaulted, becomes one view."""
    table = {(rule.kind, rule.category, rule.gender): rule for rule in DEFAULT_RULES}
    index = choice_index(choices)
    first_choice = {function: found[0] for function, found in index.by_function.items()}
    by_item: dict[Id[Any], list[FunctionSpec]] = defaultdict(list)
    for spec in specs:
        by_item[spec.item].append(spec)
    found: list[FunctionSpec] = []
    view_of: dict[Id[Any], Id[Any]] = {}
    view_choices: list[SymbolChoice] = []
    for item, group in by_item.items():
        chosen = {spec.function: first_choice.get(spec.function) for spec in group}
        resolved = {function: one for function, one in chosen.items() if one is not None}
        named = (
            len(resolved) == len(chosen)
            and len({one.symbol for one in resolved.values()}) == 1
            and all(spec.pin_function is None for spec in group)
        )
        if named:  # one symbol shared by the functions: their ports map to distinct ports
            mapped = [
                throw_port(spec, port) or resolved[spec.function].port_map.get(port.name, port.name)
                for spec in group
                for port in spec.ports
            ]
            named = len(mapped) == len(set(mapped))
        defaulted = all(
            box_drawn(spec, table, index) for spec in group
        )  # C6: an unwired PLC channel stays a port of its module's box
        # D6 overrides D5's threshold: the lone unwired channel of a half-wired module is a
        # generic box of its own (an item view would stand on the item's min-id function, which
        # may be a wired channel's)
        lone = group[0]
        if len(group) == 1 and lone.kind == "plc_channel" and lone.ports[0].port not in wired:
            found.append(dataclasses.replace(lone, kind="item", roles=kind_roles("item")))
            continue
        lone_pair = len(group) == 1 and lone.kind == "plc_channel" and len(lone.ports) > 1
        if (len(group) < 2 and not lone_pair) or not (defaulted or named):  # noqa: PLR2004 -- the count is the rule's own size (a pair or triple), not a tunable
            found.extend(group)
            continue
        name = {spec.function: functions_table(model)[spec.function].name for spec in group}
        order = function_groups(model, tuple(group))
        view_ports = tuple(
            dataclasses.replace(
                port,
                name=f"{name[spec.function]}.{port.name}",
                group=order[spec.function],
                channel=spec.kind == "plc_channel",
            )
            for spec in group
            for port in spec.ports
        )
        view_of.update((port.port, item) for port in view_ports)
        first = min(group, key=lambda spec: spec.key)
        # C3 (a): the view takes the kind (so the band) its wired functions share, else "item"
        kinds = {spec.kind for spec in group if any(p.port in wired for p in spec.ports)}
        view_kind = kinds.pop() if len(kinds) == 1 and kinds != {"plc_channel"} else "item"
        found.append(
            dataclasses.replace(
                first,
                function=item,
                key=items_table(model)[item].key,
                kind=view_kind,
                roles=dataclasses.replace(
                    kind_roles(view_kind), plc_channel=all(s.kind == "plc_channel" for s in group)
                ),
                poles=1,
                pole_pairs=(),
                ports=view_ports,
            )
        )
        if named and not defaulted:
            one = next(iter(resolved.values()))
            view_choices.append(
                SymbolChoice(
                    choice=one.choice,
                    function=item,
                    part=None,
                    kind=None,
                    symbol=one.symbol,
                    port_map=frozendict(
                        {
                            f"{name[spec.function]}.{port.name}": resolved[
                                spec.function
                            ].port_map.get(port.name, port.name)
                            for spec in group
                            for port in spec.ports
                        }
                    ),
                )
            )
    return tuple(sorted(found, key=lambda spec: spec.function)), view_of, tuple(view_choices)


def reitem(ref: PortRef, view_of: Mapping[Id[Any], Id[Any]]) -> PortRef:
    """`ref` on the item view its port belongs to (`view_of`), else unchanged."""
    return PortRef(function=view_of[ref.port], port=ref.port) if ref.port in view_of else ref


def item_text(model: Model, item: Id[Any]) -> str:
    """An item view's tag, its item designation; empty before numbering."""
    try:
        return item_tag_text(model, item)
    except SchemaError:
        return ""


def pin_text(model: Model, port: Id[Any]) -> str:
    """A pin view's tag, "X5:2"; empty before numbering."""
    try:
        return port_designation(model, port)
    except SchemaError:
        return ""


def without_idle_pins(
    model: Model,
    specs: tuple[FunctionSpec, ...],
    pin_of: Mapping[Id[Any], Id[Any]],
    used: AbstractSet[Id[Any]],
) -> tuple[tuple[FunctionSpec, ...], dict[Id[Any], Id[Any]]]:
    """R7 B5: every pin view kept that is wired, or whose mated pin is wired (D5 for pins)."""
    mate_of = mate_map(pin_mates(model, pin_of))
    kept = {port for port in pin_of if port in used or mate_of.get(port) in used}
    live = {pin_of[port] for port in kept}
    edges = {f for unit in unit_ids(model) for f in boundary(model, unit)}
    edges -= {one.function for one in unused_boundaries(model).values()}
    kept |= {port for port, f in pin_of.items() if f in edges and f not in live}
    return (
        tuple(spec for spec in specs if spec.pin_function is None or spec.function in kept),
        {port: function for port, function in pin_of.items() if port in kept},
    )


def without_idle_terminals(
    model: Model,
    specs: tuple[FunctionSpec, ...],
    used: AbstractSet[Id[Any]],
) -> tuple[FunctionSpec, ...]:
    """Every spec except a terminal none of whose ports is on a connection, net group or mate."""
    mated = {f for mate in mates_table(model).values() for f in (mate.a, mate.b)}
    mated |= {f for unit in unit_ids(model) for f in boundary(model, unit)}
    return tuple(
        spec
        for spec in specs
        if spec.kind != "terminal"
        or spec.function in mated
        or any(port.port in used for port in spec.ports)
    )


def pin_views(
    specs: tuple[FunctionSpec, ...],
) -> tuple[tuple[FunctionSpec, ...], dict[Id[Any], Id[Any]]]:
    """R7 A: every connector function becomes one view per pin; a view's handle is the port."""
    found: list[FunctionSpec] = []
    pin_of: dict[Id[Any], Id[Any]] = {}
    for spec in specs:
        if spec.kind != "connector" or not spec.ports:  # a view per pin; no pin, no view
            found.append(spec)
            continue
        for port in spec.ports:
            pin_of[port.port] = spec.function
            found.append(
                dataclasses.replace(
                    spec,
                    function=port.port,
                    key=(*spec.key, "pin", port.name),
                    poles=1,
                    pole_pairs=(),
                    ports=(dataclasses.replace(port, name="in"),),
                    pin_function=spec.function,
                )
            )
    return tuple(sorted(found, key=lambda spec: spec.function)), pin_of


def repin(ref: PortRef, pin_of: Mapping[Id[Any], Id[Any]]) -> PortRef:
    """`ref` on the pin view its port is (`pin_of`), else unchanged."""
    return PortRef(function=ref.port, port=ref.port) if ref.port in pin_of else ref


def pin_mates(model: Model, pin_of: Mapping[Id[Any], Id[Any]]) -> tuple[MatedFunctions, ...]:
    """R7 A: each mate's equal-named pins, upper (plug) side first (mated-pair spec J3)."""
    pins: dict[Id[Any], dict[str, Id[Any]]] = defaultdict(dict)
    for port, function in pin_of.items():
        pins[function][ports_table(model)[port].name] = port
    found = []
    lower_rank = partial(_lower_rank, model, _cable_like(model))
    for mate in mates_table(model).values():
        if mate.a not in pins or mate.b not in pins:
            continue
        lower = max((mate.a, mate.b), key=lower_rank)
        upper = mate.b if lower == mate.a else mate.a
        found.extend(
            MatedFunctions(a=pins[upper][name], b=pins[lower][name])
            for name in sorted(pins[upper].keys() & pins[lower].keys())
        )
    return tuple(sorted(found, key=lambda pair: (pair.a, pair.b)))


def _lower_rank(
    model: Model, cable_like: frozenset[Id[Item]], function: Id[Any]
) -> tuple[bool, bool, AuthoringKey]:
    """J3: on or under a board first, then not on a cable or harness, then the later key."""
    record = functions_table(model)[function]
    return (
        bool(enclosing_boards(model, record.item)),
        not _on_cable(model, cable_like, record.item),
        record.key,
    )


def _cable_like(model: Model) -> frozenset[Id[Item]]:
    """Every cable item (`is_cable`) and every harness (a cable's parent)."""
    cables = cable_items(model)
    all_items = items_table(model)
    harnesses = {parent for c in cables if (parent := all_items[c].parent) is not None}
    return frozenset(cables | harnesses)


def _on_cable(model: Model, cable_like: frozenset[Id[Item]], item: Id[Item]) -> bool:
    """Whether `item` or an ancestor is in `cable_like`: a cable or a harness."""
    all_items = items_table(model)
    return any(
        node in cable_like for node in parent_chain(lambda node: all_items[node].parent, item)
    )


def item_of(model: Model, ref: PortRef) -> Id[Item]:
    """The item of the function `ref` is on."""
    return functions_table(model)[ref.function].item


def is_board_internal(model: Model, item_ids: Iterable[Id[Item]]) -> bool:
    """Whether one *opaque* board item is an ancestor-or-self of every one of `item_ids`."""
    common: frozenset[Id[Item]] | None = None
    for item_id in item_ids:
        boards = frozenset(
            board
            for board in enclosing_boards(model, item_id)
            if not is_sole_unit_root(model, board)
        )
        common = boards if common is None else common & boards
        if not common:
            return False
    return bool(common)
