"""Schematic engine, reading: the steps of `read_inputs`, one helper each (docs/design/engine.md 7).

Each step takes and returns the three ref-carrying tuples as one `Refs`, so a re-pin or a
re-item is one `_remap`.
"""

import dataclasses
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Callable, Mapping
lazy from collections.abc import Set as AbstractSet

from fransys_layout.engines.schematic.read import labels, offstubs, reading
from fransys_layout.engines.schematic.read.connections import (
    split_connections,
    split_net_groups,
    split_rails,
)
from fransys_layout.engines.schematic.read.item_sides import pin_sides
from fransys_layout.engines.schematic.read.labels import LabelText
from fransys_layout.engines.schematic.read.offstubs import far_maps, off_reads
from fransys_layout.engines.schematic.read.rails import (
    mark_boundary_rails,
    rail_groups,
    rail_terminal_functions,
    rail_wires,
)
from fransys_layout.engines.schematic.read.unused import without_unused
from fransys_layout.engines.schematic.read.views import (
    item_text,
    item_views,
    pin_mates,
    pin_text,
    pin_views,
    reitem,
    repin,
    without_idle_pins,
)
from fransys_layout.stages import (
    Connection,
    FunctionSpec,
    LabelKind,
    NetGroup,
    Profile,
    Rail,
    RailEnd,
    SymbolChoice,
)
from fransys_layout.stages.offstubs import OffEnd, PortText, by_location, groups_by_location
from fransys_model.kernel import Finding, Id

if TYPE_CHECKING:
    from fransys_model.derive.indexes import Indexes
    from fransys_model.kernel import Model

type Specs = tuple[FunctionSpec, ...]
type Refs = tuple[tuple[Connection, ...], tuple[NetGroup, ...], tuple[RailEnd, ...]]
type Views = dict[Id[Any], Id[Any]]


def boxed(specs: Specs, view_of: Mapping[Id[Any], Id[Any]]) -> Specs:
    """The specs with a port in an item box."""
    return tuple(s for s in specs if any(p.port in view_of for p in s.ports))


def rail_reads(
    model: Model, indexes: Indexes
) -> tuple[Specs, frozenset[Id[Any]], tuple[Connection, ...], tuple[RailEnd, ...]]:
    """The drawn specs, the undrawn rail terminals, and the wires and rail ends (V3)."""
    specs = reading.drawn_functions(model, indexes)
    # V3: a rail terminal is not drawn; its wires and the pins' rail wires become `rail_ends`
    undrawn = rail_terminal_functions(model, specs)
    specs = mark_boundary_rails(model, specs, undrawn)  # RB2: the parent's page draws these
    specs = tuple(spec for spec in specs if spec.function not in undrawn or spec.rail)
    wires, rail_ends = rail_wires(model, reading.connections(model, indexes), specs, undrawn)
    return specs, undrawn, wires, rail_ends


def split_reads(
    model: Model,
    specs: Specs,
    undrawn: frozenset[Id[Any]],
    wires: tuple[Connection, ...],
    rail_ends: tuple[RailEnd, ...],
) -> tuple[Refs, tuple[Rail, ...], tuple[Finding, ...], set[Id[Any]]]:
    """The kept connections, net groups and rails, their findings, and the one wired set."""
    drawn = {spec.function for spec in specs}
    connections, connection_findings, stranded = split_connections(model, wires, drawn)
    net_groups, group_findings, stranded_groups = split_net_groups(
        model, rail_groups(reading.net_groups(model), undrawn, rail_ends), drawn
    )
    rails = split_rails(model, reading.rails(model), drawn)
    # the one wired set: a port on a kept connection or net group, or on one dropped for an
    # undrawn far end (`stranded`, `stranded_groups`), is wired, not idle
    wired = {ref.port for c in connections for ref in (c.a, c.b)} | stranded | stranded_groups
    wired |= {ref.port for g in net_groups for ref in g.ports}
    wired |= {end.ref.port for end in rail_ends}
    findings = (*connection_findings, *group_findings)
    return (connections, net_groups, rail_ends), rails, findings, wired


def _remap(fn: Callable[[Any], Any], refs: Refs) -> Refs:
    """The three ref tuples with `fn` (a repin or a reitem) applied to every ref."""
    connections, net_groups, rail_ends = refs
    return (
        tuple(dataclasses.replace(c, a=fn(c.a), b=fn(c.b)) for c in connections),
        tuple(dataclasses.replace(g, ports=tuple(fn(r) for r in g.ports)) for g in net_groups),
        tuple(dataclasses.replace(e, ref=fn(e.ref)) for e in rail_ends),
    )


def pin_reads(
    model: Model, specs: Specs, wired: AbstractSet[Id[Any]], refs: Refs
) -> tuple[Specs, Views, Refs]:
    """The specs with pin views, the pin-view map, and the refs named by pin view."""
    # R7 A: connectors are drawn per pin; connections and nets name the pin views
    specs, pin_of = pin_views(specs)
    refs = _remap(lambda ref: repin(ref, pin_of), refs)
    # R7 B5: a pin with no conductor or net, whose mated pin has none either, is not drawn
    specs, pin_of = without_idle_pins(model, specs, pin_of, wired)
    return specs, pin_of, refs


def unused_reads(
    model: Model, specs: Specs, drawn: AbstractSet[Id[Any]], profile: Profile
) -> tuple[Specs, Specs, AbstractSet[Id[Any]]]:
    """The specs without unused pins, the spares, and `drawn` named by function."""
    # V1, layout-0112: an unwired contact is never drawn; the switch also drops other spares
    specs, spares = without_unused(
        model, specs, reading.symbol_choices(model), hide=profile.hide_unused_pins
    )
    # `drawn` keeps its pre-pin-view names, switch on or off: a pin view counts as its connector
    if profile.hide_unused_pins:
        return specs, spares, {s.pin_function or s.function for s in specs}
    return specs, spares, drawn - {s.function for s in spares}


def item_reads(
    model: Model, specs: Specs, wired: AbstractSet[Id[Any]], refs: Refs
) -> tuple[Specs, Views, tuple[SymbolChoice, ...], tuple[tuple[Id[Any], ...], ...], Refs]:
    """The specs with item boxes, the item map and choices, the box sides, and the refs by item."""
    # R7 B2: an item whose every drawn function is symbol-defaulted is one box
    drawn_specs = specs
    specs, view_of, view_choices = item_views(model, specs, reading.symbol_choices(model), wired)
    # V1: each item box's pins on the side of their function's rank; the functions that stand
    # apart from the box (a contact, a connector's pin views) are no part of it
    sides = pin_sides(model, boxed(drawn_specs, view_of), set(view_of.values()))
    return specs, view_of, view_choices, sides, _remap(lambda ref: reitem(ref, view_of), refs)


def off_reads_of(
    model: Model, specs: Specs, refs: Refs, pin_of: Views
) -> tuple[Refs, tuple[Connection, ...], tuple[PortText, ...], tuple[OffEnd, ...]]:
    """The refs with the boundary off-stubs, `crossing`, and the off-stub texts and ends."""
    connections, net_groups, rail_ends = refs
    # C21: a column never spans locations; a conductor between two is a stub at each end
    # (the engine takes them out after chain discovery, so rows still form across)
    maps = far_maps(model)  # the one build of the mate and port lookups every stub text reads
    reads = off_reads(model, maps)
    split = by_location(specs, connections, reads)
    # D4 (S15): a net group is its location parts, the parts joined by a stub pair each; a join
    # is in `crossing` only, never in `connections`, since it is no conductor of the model
    net_groups, joins = groups_by_location(specs, net_groups, reads)
    off_texts, off_ends = offstubs.off_texts(model, maps, split[1], joins)
    # W3 (designer's ruling): a unit's boundary pin mated outside the unit carries its mate's
    # off-stub (conductors only: `boundary_offs` reads each one's record)
    offs, off_more, ends_more = offstubs.boundary_offs(
        model, reads, specs, pin_mates(model, pin_of), split
    )
    return (
        ((*connections, *offs), net_groups, rail_ends),
        (*split[1], *joins, *offs),
        (*off_texts, *off_more),
        (*off_ends, *ends_more),
    )


def label_texts(
    model: Model, indexes: Indexes, drawn: AbstractSet[Id[Any]], pin_of: Views, view_of: Views
) -> tuple[LabelText, ...]:
    """The label texts of the functions, then of each pin view and each item box."""
    return (
        *labels.label_texts(model, indexes, drawn),
        *(
            LabelText(kind=LabelKind.TAG, subject=port, text=pin_text(model, port))
            for port in sorted(pin_of)
        ),
        *(
            LabelText(kind=LabelKind.TAG, subject=item, text=item_text(model, item))
            for item in sorted(set(view_of.values()))
        ),
    )
