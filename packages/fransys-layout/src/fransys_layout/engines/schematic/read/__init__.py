"""Schematic engine, reading: model records to stage inputs.

The only place, with `write/`, where the model vocabulary meets the stages. The work of
reading each `StageInputs` field is in `reading.py`, `labels.py`, `views.py`, `connections.py`
and `offstubs.py`; this module orchestrates it. `labels.label_requests` builds the label
requests once `resolve` has chosen the symbols.
"""

from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.read import reading, steps
from fransys_layout.engines.schematic.read.labels import LabelText
from fransys_layout.engines.schematic.read.pairs import box_feeds
from fransys_layout.engines.schematic.read.power import power_ends
from fransys_layout.engines.schematic.read.sheets import text_floor_findings, unused_sheet_findings
from fransys_layout.engines.schematic.read.views import pin_mates, without_idle_terminals
from fransys_layout.stages import (
    BoxFeed,
    Chain,
    Connection,
    FunctionSpec,
    GroupInfo,
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
from fransys_layout.stages.offstubs import OffEnd, PortText
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
    # Conductors between two locations (not laid out), the joins of a net group's
    # location parts, and, per near port, the stub's `StubText`
    crossing: tuple[Connection, ...] = ()
    off_texts: tuple[PortText, ...] = ()
    off_ends: tuple[OffEnd, ...] = ()
    # The terminal chains, derived once by the engine before the columns are joined
    terminal_chains: TerminalChains = NO_CHAINS
    # layout-0094: each port on a power net with its symbol and text, by port (`power.power_ends`)
    power: tuple[PowerEnd, ...] = ()
    # The slot of a power symbol's label, the model's one spelling (a stage may not import it)
    power_slot: str = ""
    # Each drawn pin end of a rail wire (not drawn); the pin takes the rail's power symbol
    rail_ends: tuple[RailEnd, ...] = ()
    # layout-0099: the ports of item boxes that the side order puts on top, and those it puts below
    item_north: tuple[Id[Any], ...] = ()
    item_south: tuple[Id[Any], ...] = ()
    # The functions the switch leaves off every page (the contact table lists them, later)
    spares: tuple[FunctionSpec, ...] = ()
    # layout-0107: the item boxes that stand over the pin group they feed
    feeds: tuple[BoxFeed, ...] = ()
    # layout-0154: the conductors harness lines carry, out of `connections` and `crossing`
    carried: tuple[Connection, ...] = ()


def read_inputs(model: Model, unit: Id[Any] | None = None) -> StageInputs:
    """Read the drawn functions, their connections and every authored hint.

    The profile and sheet are `unit`'s (`None`: the top design's), whatever is drawn.
    """
    indexes = build_indexes(model)
    specs, undrawn, wires, rail_ends = steps.rail_reads(model, indexes)
    profile, sheet, sheet_format = reading.profile_and_sheet(model, unit)
    unused_sheets = reading.unused_sheet_formats(model)
    refs, rails, findings, wired = steps.split_reads(model, specs, undrawn, wires, rail_ends)
    # A terminal on no connection, net group or mate is not drawn (terminal list only)
    specs = without_idle_terminals(model, specs, wired)
    drawn = {spec.function for spec in specs}
    specs, pin_of, refs, landings = steps.pin_reads(model, specs, wired, refs)
    specs, spares, drawn = steps.unused_reads(model, specs, drawn, profile)
    specs, view_of, view_choices, (north, south), refs = steps.item_reads(
        model, specs, wired, refs, landings
    )
    refs, crossing, off_texts, off_ends = steps.off_reads_of(model, specs, refs, pin_of)
    connections, net_groups, rail_ends = refs
    return StageInputs(
        functions=specs,
        connections=connections,
        net_groups=net_groups,
        rails=rails,
        chains=reading.chains(model, view_of),
        choices=(*reading.symbol_choices(model), *view_choices),
        groups=reading.group_infos(model),
        locations=reading.location_infos(model),
        units=reading.unit_infos(model),
        hints=reading.page_hints(model),
        label_texts=steps.label_texts(model, indexes, drawn, (pin_of, view_of, landings)),
        profile=profile,
        sheet=sheet,
        sheet_format=sheet_format,
        unused_sheet_formats=unused_sheets,
        read_findings=tuple(
            sorted(
                (
                    *findings,
                    *unused_sheet_findings(sheet, sheet_format, unused_sheets),
                    *text_floor_findings(model, unit),
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
