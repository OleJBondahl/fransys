"""Schematic engine, reading: model records to stage inputs (docs/design/engine.md 7).

The only place, with `write/`, where the model vocabulary meets the stages. The work of
reading each `StageInputs` field is in `reading.py`, `labels.py`, `views.py`, `connections.py`
and `offstubs.py`; this module orchestrates it. `labels.label_requests` builds the label
requests once `resolve` has chosen the symbols.
"""

import dataclasses
from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.read import labels, offstubs, reading
from fransys_layout.engines.schematic.read.connections import (
    split_connections,
    split_net_groups,
    split_rails,
)
from fransys_layout.engines.schematic.read.item_sides import pin_sides
from fransys_layout.engines.schematic.read.labels import LabelText
from fransys_layout.engines.schematic.read.offstubs import far_maps, off_reads
from fransys_layout.engines.schematic.read.pairs import box_feeds
from fransys_layout.engines.schematic.read.power import power_ends
from fransys_layout.engines.schematic.read.rails import (
    rail_groups,
    rail_terminal_functions,
    rail_wires,
)
from fransys_layout.engines.schematic.read.sheets import unused_sheet_findings
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
    without_idle_terminals,
)
from fransys_layout.stages import (
    BoxFeed,
    Chain,
    Connection,
    FunctionSpec,
    GroupInfo,
    LabelKind,
    LocationInfo,
    NetGroup,
    PageHints,
    PowerEnd,
    Profile,
    Rail,
    RailEnd,
    SheetFormat,
    SymbolChoice,
    UnitInfo,
)
from fransys_layout.stages.offstubs import OffEnd, PortText, by_location, groups_by_location
from fransys_layout.stages.terminal_rows import NO_CHAINS, TerminalChains
from fransys_layout.stages.types import MatedFunctions
from fransys_model.derive.indexes import build_indexes
from fransys_model.kernel import Finding, Id, value
from fransys_model.layout import POWER_SLOT

if TYPE_CHECKING:
    from fransys_model.kernel import Model


@value
class StageInputs:
    """Everything the stages need from one model. Every tuple is sorted by handle or key."""

    functions: tuple[FunctionSpec, ...]
    connections: tuple[Connection, ...]
    net_groups: tuple[NetGroup, ...]
    rails: tuple[Rail, ...]
    chains: tuple[Chain, ...]
    choices: tuple[SymbolChoice, ...]
    groups: tuple[GroupInfo, ...]
    locations: tuple[LocationInfo, ...]
    units: tuple[UnitInfo, ...]
    hints: PageHints
    label_texts: tuple[LabelText, ...]
    profile: Profile
    sheet: SheetFormat
    sheet_format: Id[Any] | None = None
    unused_sheet_formats: tuple[Id[Any], ...] = ()
    read_findings: tuple[Finding, ...] = ()
    mates: tuple[MatedFunctions, ...] = ()
    # C21: conductors between two locations (not laid out), D4: the joins of a net group's
    # location parts, and, per near port, the stub's `StubText`
    crossing: tuple[Connection, ...] = ()
    off_texts: tuple[PortText, ...] = ()
    off_ends: tuple[OffEnd, ...] = ()
    # M12: the terminal chains, derived once by the engine before the columns are joined
    terminal_chains: TerminalChains = NO_CHAINS
    # D5: each port on a power net with its symbol and text, by port (`power.power_ends`)
    power: tuple[PowerEnd, ...] = ()
    # D5: the slot of a power symbol's label, the model's one spelling (a stage may not import it)
    power_slot: str = ""
    # V3: each drawn pin end of a rail wire (not drawn); the pin takes the rail's power symbol
    rail_ends: tuple[RailEnd, ...] = ()
    # V1: the ports of item boxes that V1's side order puts on top, and those it puts below
    item_north: tuple[Id[Any], ...] = ()
    item_south: tuple[Id[Any], ...] = ()
    # V1: the functions the switch leaves off every page (the contact table lists them, later)
    spares: tuple[FunctionSpec, ...] = ()
    # layout-0107: the item boxes that stand over the pin group they feed
    feeds: tuple[BoxFeed, ...] = ()


def read_inputs(model: Model) -> StageInputs:
    """Read the drawn functions, their connections and every authored hint (WP13)."""
    indexes = build_indexes(model)
    specs = reading.drawn_functions(model, indexes)
    # V3: a rail terminal is not drawn; its wires and the pins' rail wires become `rail_ends`
    undrawn = rail_terminal_functions(model, specs)
    specs = tuple(spec for spec in specs if spec.function not in undrawn)
    drawn = {spec.function for spec in specs}
    wires, rail_ends = rail_wires(model, reading.connections(model, indexes), specs, undrawn)
    profile, sheet, sheet_format = reading.profile_and_sheet(model)
    unused_sheets = reading.unused_sheet_formats(model, sheet_format)

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
    # R6 D5: a terminal on no connection, net group or mate is not drawn (terminal list only)
    specs = without_idle_terminals(model, specs, wired)
    drawn = {spec.function for spec in specs}
    # R7 A: connectors are drawn per pin; connections and nets name the pin views
    specs, pin_of = pin_views(specs)
    connections = tuple(
        dataclasses.replace(c, a=repin(c.a, pin_of), b=repin(c.b, pin_of)) for c in connections
    )
    net_groups = tuple(
        dataclasses.replace(g, ports=tuple(repin(r, pin_of) for r in g.ports)) for g in net_groups
    )
    rail_ends = tuple(dataclasses.replace(e, ref=repin(e.ref, pin_of)) for e in rail_ends)
    # R7 B5: a pin with no conductor or net, whose mated pin has none either, is not drawn
    specs, pin_of = without_idle_pins(model, specs, pin_of, wired)
    # V1, layout-0112: an unwired contact is never drawn; the switch also drops other spares
    specs, spares = without_unused(
        model, specs, reading.symbol_choices(model), hide=profile.hide_unused_pins
    )
    # `drawn` keeps its pre-pin-view names, switch on or off: a pin view counts as its connector
    drawn = (
        {s.pin_function or s.function for s in specs}
        if profile.hide_unused_pins
        else drawn - {s.function for s in spares}
    )
    # R7 B2: an item whose every drawn function is symbol-defaulted is one box
    boxed = specs
    specs, view_of, view_choices = item_views(model, specs, reading.symbol_choices(model), wired)
    # V1: each item box's pins on the side of their function's rank
    north, south = pin_sides(model, boxed, set(view_of.values()))
    connections = tuple(
        dataclasses.replace(c, a=reitem(c.a, view_of), b=reitem(c.b, view_of)) for c in connections
    )
    net_groups = tuple(
        dataclasses.replace(g, ports=tuple(reitem(r, view_of) for r in g.ports)) for g in net_groups
    )
    rail_ends = tuple(dataclasses.replace(e, ref=reitem(e.ref, view_of)) for e in rail_ends)
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
    connections, crossing, off_texts = (
        (*connections, *offs),
        (*split[1], *joins, *offs),
        (*off_texts, *off_more),
    )
    off_ends = (*off_ends, *ends_more)
    label_texts = (
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

    return StageInputs(
        functions=specs,
        connections=connections,
        net_groups=net_groups,
        rails=rails,
        chains=reading.chains(model),
        choices=(*reading.symbol_choices(model), *view_choices),
        groups=reading.group_infos(model),
        locations=reading.location_infos(model),
        units=reading.unit_infos(model),
        hints=reading.page_hints(model),
        label_texts=label_texts,
        profile=profile,
        sheet=sheet,
        sheet_format=sheet_format,
        unused_sheet_formats=unused_sheets,
        read_findings=tuple(
            sorted(
                (
                    *connection_findings,
                    *group_findings,
                    *unused_sheet_findings(sheet, sheet_format, unused_sheets),
                ),
                key=lambda f: (f.code, f.subjects),
            )
        ),
        mates=pin_mates(model, pin_of),
        crossing=crossing,
        off_texts=off_texts,
        off_ends=off_ends,
        power=power_ends(model),
        power_slot=POWER_SLOT,
        rail_ends=rail_ends,
        item_north=north,
        item_south=south,
        spares=spares,
        feeds=box_feeds(model, specs, north, south),
    )
