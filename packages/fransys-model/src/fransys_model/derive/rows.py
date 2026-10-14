"""Report row shapes: one `@value` per Fransys output format (derive-queries.md and examples.md).

Defined once here; the query modules build them; Fransys formats them to CSV, XLSX, XML or
Typst and never reshapes them. Reference fields are ids; anything a human reads is
already rendered (`derive.designation`), so no formatter ever re-derives or re-parses a
label. All numeric fields are `int` or `Decimal`, never `float`; every sequence is a
`tuple`.

The list outputs' shared read of these rows lives in `derive.columns`, once: which fields of each
row shape a list prints and in what order (`*_COLUMNS`) and the terminal list's two ends labels
(`TERMINAL_LABELS`). The one text of a list cell (`cell_text`, `cell_parts`, `CELL_SEPARATOR`) and
the field extraction (`column_values`, `column_rows`, `pin_lines`) live in `derive.list_cells`.
The PDF lists and the CSVs both call them, so the two can never print a different header or
cell. This is a choice of fields and a text for one cell, never a reshaping of a row.
"""

from decimal import Decimal
from enum import Enum
from typing import Any

from fransys_model.kernel import AuthoringKey, Id, register_enum, value
from fransys_model.layout import OverviewRef, Page
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Function, Item, Port, Unit
from fransys_model.vocab.enums import FunctionKind, Gender, SignalType
from fransys_model.vocab.ratings import Operating, Rating
from fransys_model.vocab.templates import FunctionTemplate, Part

from .rows_cores import OpenCoreRow
from .rows_removed import RemovedAncestry


@value
class TerminalRow:
    """One terminal of a strip's connection list.

    An unused terminal has empty `internal`/`external` tuples; bridged terminals share one
    `jumper_group` number. `internal_ends` and `external_ends`
    are the rendered far-end port designations of those conductors, aligned index for index
    with `internal` and `external`: `internal_ends[i]` is where `internal[i]` goes. After those come
    the open cores landing there (`-W1 GY spare`), which have no conductor. Given a
    `context` location, `terminal_rows` prints an end outside it with its location path in
    front (`+EXT-M1:U1`) and one inside it short (`-B12:2/T1`).
    """

    terminal: Id[Item]
    designation: str
    group: str
    index: int
    internal: tuple[Id[Conductor], ...]
    external: tuple[Id[Conductor], ...]
    internal_ends: tuple[str, ...]
    external_ends: tuple[str, ...]
    jumper_group: int | None


@value
class BomLine:
    """One BOM line, by `Part`, `installed` non-external items only; or one nested unit.

    `mpn`/`manufacturer`/`description` are `Part`'s own fields, projected here
    so a formatter never looks the part back up. A unit line has `part=None`,
    the unit's name in `mpn`, an empty `manufacturer`, and its own `revision`, printed as
    `revision_text` (`"1.1"`); `revision` is `""` on every part line. A unit line's
    `designations` are per instance: its one root item's designation, else its location
    (`"+C1"`), else its root items' (`bom_lines`).
    Every designation a line prints carries its sign (`"-K1"`, `"-U2"`, `"-X1:L1:1"`,
    `"+C1"`).
    """

    part: Id[Part] | None
    mpn: str
    manufacturer: str
    description: str
    count: int
    designations: tuple[str, ...]
    revision: str


@value
class PlcChannelRow:
    """One pin of a PLC channel.

    `pin` is its printed designation (`-A2:5`), `channel_name` the
    channel's own number, `wired_to` the printed far ends at that port joined with `CELL_SEPARATOR`
    (`None` for none). The device fields and `signal_name` are `None` for an unbound channel.
    """

    channel: Id[Function]
    port: Id[Port]
    pin: str
    channel_name: str
    signal: SignalType
    wired_to: str | None
    field_device: Id[Function] | None
    field_device_designation: str | None
    signal_name: str | None


@value
class PlcTable:
    """One table of the PLC list: the channels of one controller or module.

    `item` carries the channels, `designation` is its printed designation, the table's heading;
    `rows` are its `PlcChannelRow`s in list order, never empty.
    """

    item: Id[Item]
    designation: str
    rows: tuple[PlcChannelRow, ...]


@value
class ChannelScaling:
    """The `scaling` facet of a field device, projected so a formatter never looks it up."""

    unit: str
    raw_min: int
    raw_max: int
    eng_min: Decimal
    eng_max: Decimal


@value
class PlcRackChannel:
    """One channel of a rack module, bound or spare.

    The field fields are `None` for a spare channel, as in `PlcChannelRow`; `scaling` is also
    `None` for a bound device that carries no `scaling` facet.
    """

    channel: Id[Function]
    number: int
    signal: SignalType
    field_device: Id[Function] | None
    field_device_designation: str | None
    signal_name: str | None
    scaling: ChannelScaling | None


@value
class PlcRackModule:
    """One PLC module of a rack with its channels, for an output that walks the rack in order.

    `mpn` and `description` are the `Part`'s, projected as `BomLine` does. `position` is the
    item's own `position`, `None` when it was never authored.
    """

    module: Id[Item]
    designation: str
    mpn: str
    description: str
    position: int | None
    channels: tuple[PlcRackChannel, ...]


@value
class CableRow:
    """One core of one cable, both ends."""

    cable: Id[Item]
    cable_designation: str
    index: int
    colour: str
    conductor: Id[Conductor]
    end_a: Id[Port]
    end_a_designation: str
    end_b: Id[Port]
    end_b_designation: str


@value
class WireRow:
    """One wire of the wire list: its two ends, colour, cross-section and printed label."""

    conductor: Id[Conductor]
    from_: str
    to: str
    colour: str
    cross_section_mm2: Decimal
    label: str


@value
class DesignationRow:
    """One line of the tag/designation list (`designation_list`)."""

    item: Id[Item]
    designation: str
    reference: str
    description: str


@value
class NetlistPart:
    """One placed part on a `board_netlist` (connectivity.md: the board's netlist replaces SKiDL).

    `installed` is the item's own flag: a part not installed stays listed, and the output
    decides what to do with it.
    """

    item: Id[Item]
    designation: str
    mpn: str
    footprint_library: str
    footprint_name: str
    installed: bool


@value
class NetlistNet:
    """One net of a `board_netlist`, by the pins it joins."""

    name: str
    pins: tuple[Id[Port], ...]


@value
class BoardNetlist:
    """A board's parts, footprints and nets: one more Fransys output.

    `without_footprint` are the board's descendants with a part whose part carries no
    `footprint`: the parts a netlist cannot place, which the query omits from `parts`. An accessory,
    which prints its holder's designation, is no part of its own and is never listed.
    """

    board: Id[Item]
    board_designation: str
    parts: tuple[NetlistPart, ...]
    nets: tuple[NetlistNet, ...]
    without_footprint: tuple[Id[Item], ...]


@value
class ConnectorPin:
    """One pin of a board connector, the net on it and the pin it mates with.

    `marking` is the port's name. `net` is the name of the declared net that lists the port,
    named as `board_netlist` names its nets; `None` when no declared net lists it. The mate's
    pin is the port of equal name on the mated function (a `Mate` carries no pin map).
    `ends` are the far ends of every conductor on the pin or its mate, as `far_ends` prints them.
    """

    port: Id[Port]
    marking: str
    net: str | None
    mate_port: Id[Port] | None
    mate_port_designation: str | None
    ends: tuple[str, ...]


@value
class ConnectorRow:
    """One connector of a board, as listed by `connector_rows`.

    `designation` and `mate_designation` are `connector_designation`: the connector's own item's
    designation, plus `-<label>` when that item carries two or more labelled connector functions
    (`-JB1-J1`; a device's connectors print as sub-parts); an item with one never shows it.
    `style`, `pincount` and `gender` are
    the `connector` facet of the function's template, projected here so a formatter never looks
    them up; `gender` is `None` when the part file states none. `mate` is
    the connector plugged into this one, `None` when unmated.
    """

    connector: Id[Function]
    designation: str
    style: str
    pincount: int
    gender: Gender | None
    mate: Id[Function] | None
    mate_designation: str | None
    pins: tuple[ConnectorPin, ...]


@value
class HarnessPin:
    """One port of a harness cable's end that a core of that cable lands on.

    `marking` is the port's own name, except for a port of a terminal with a parent (its end
    is grouped by strip): there it is the terminal's own bare `group:index`
    designation (`"L1:1"`), never dashed or strip-prefixed -- the end's
    own `designation` already names the strip, dashed (`product_designation`), and every
    consumer that draws a pin next to its end joins the two itself, so a dashed, strip-prefixed
    marking here would print the strip twice.
    """

    port: Id[Port]
    marking: str


@value
class HarnessCore:
    """One core of a harness cable: the facts of a `CableRow`, plus the label its wire carries.

    `label` is the label of the `wire` facet of the core's conductor, `None` when it has none.
    `end_a`/`end_b` are `CableRow`'s own -- `cable_rows` itself orients every core of one cable
    to run from its one lower-ranked end to its one higher-ranked end
    (`cable_end_rank`, a unit member first; `cable_end_owner`), not `Conductor.a`/`.b`'s raw
    port-id order, so `end_a` is always the same physical end for every core that lands on it.
    """

    conductor: Id[Conductor]
    index: int
    colour: str
    label: str | None
    end_a: Id[Port]
    end_a_designation: str
    end_b: Id[Port]
    end_b_designation: str


@value
class HarnessEnd:
    """One item a core lands on: a connector housing, a plain device, or a strip of terminals.

    A core that lands on a terminal with a parent lands on that terminal's strip instead:
    `item` is the strip and `pins` holds one `HarnessPin` per landed
    terminal port, marked by the terminal's own bare designation (`"L1:1"`,
    not dashed or strip-prefixed here) rather than a raw port name. `designation` is the item's
    `product_designation` for every end: a strip, a connector plug
    or a plain device alike, e.g. `"-X1"` unplaced, `"+C1-X1"` or `"+EXT-M1"` placed, never with
    a function segment; the same text the terminal list prints and the cable list's
    `from_label`/`to_label` repeat. The connector fields (`connector`, `style`, `pincount`,
    `gender`) are filled from the `connector` facet of a connector function of the item that a
    core lands on, and are `None` for a plain device or a strip alike (a strip is never itself a
    `connector`-kind function). Any other end -- a connector or a plain device -- has `item` the
    device itself and `pins` one per landed port, marked by the port's own name.
    """

    item: Id[Item]
    designation: str
    connector: Id[Function] | None
    style: str | None
    pincount: int | None
    gender: Gender | None
    mpn: str | None
    pins: tuple[HarnessPin, ...]


@value
class HarnessCable:
    """One cable of a harness with its product facts, cores and ends.

    `mpn` and `description` are the cable `Part`'s; `core_count`, `gauge_mm2` and `shielded` are
    its `cable_product` facet; `length_mm` is the item's `cable` facet. Each is `None` where the
    part or the facet is absent. `designation` is the cable's `printed_designation` (`"-W1"`),
    the text the drawing's cable node title prints. `open_cores` are the cable's spares and
    one-ended screens (`open_core_rows`), which have no conductor and so are not in `cores`.
    """

    cable: Id[Item]
    designation: str
    mpn: str | None
    description: str | None
    core_count: int | None
    gauge_mm2: Decimal | None
    shielded: bool | None
    length_mm: int | None
    cores: tuple[HarnessCore, ...]
    ends: tuple[HarnessEnd, ...]
    open_cores: tuple[OpenCoreRow, ...] = ()


@value
class _CableFacts:
    """The facts `CableListRow` and `ContentsRow` share: `HarnessCable`'s, `None` if absent."""

    cable: Id[Item]
    designation: str
    mpn: str | None
    description: str | None
    core_count: int | None
    gauge_mm2: Decimal | None
    length_mm: int | None


@value
class CableListRow(_CableFacts):
    """One top-level cable of the system document's cable list.

    `mpn`, `description`, `core_count`, `gauge_mm2` and `length_mm` are `HarnessCable`'s own
    facts, `None` where the part or facet is absent. `designation` is the cable's
    `printed_designation` (`"-W1"`). Ends are ordered by `cable_end_rank` (a unit member first),
    so a cable authored either way round reads the same way round. `from_label` is the first end's
    `HarnessEnd.designation`, the text the drawing prints. `to_label` lists every other end's
    designation in that order, joined by `", "`. With one end `to_label` is `""`, with none
    both are. `pairs` is the number of twisted pairs of the product, `None` for a product with none.
    """

    from_label: str
    to_label: str
    pairs: int | None = None


@value
class ContentsRow(_CableFacts):
    """One cable of a document's CONTENTS page.

    `mpn`, `description`, `core_count`, `gauge_mm2` and `length_mm` are `HarnessCable`'s own
    facts, as in `CableListRow`. `designation` is the cable's `printed_designation` (`"-W1"`).
    `ends` is every end's `designation` in the cable's end order, joined by an en dash, a blank
    end (outside a nested unit) dropped with its dash; unlike `CableListRow` it keeps
    every end. It is text, not a tuple, so `cell_text` cannot join it with `CELL_SEPARATOR`.
    """

    ends: str


@register_enum
class ItemKind(Enum):
    """What an item is, as the overview colours and filters it.

    One value per item. `TERMINAL` is a strip's terminal, `STRIP` the item holding terminals.
    `DEVICE` is everything the other seven do not name.
    """

    TERMINAL = "terminal"
    STRIP = "strip"
    CONNECTOR = "connector"
    PLC_MODULE = "plc_module"
    CABLE = "cable"
    HARNESS = "harness"
    BOARD = "board"
    DEVICE = "device"


@register_enum
class SignalKind(Enum):
    """The form and direction of a PLC signal."""

    DIGITAL_IN = "digital_in"
    DIGITAL_OUT = "digital_out"
    ANALOGUE_IN = "analogue_in"
    ANALOGUE_OUT = "analogue_out"


@register_enum
class OverviewLinkKind(Enum):
    """How two items are connected in the overview: the closed set of kinds.

    `WIRE` is a conductor with no carrier, `CABLE` a conductor carried by a cable item, `MATE`
    a `Mate` between functions of the two items.
    """

    WIRE = "wire"
    CABLE = "cable"
    MATE = "mate"


@value
class OverviewNode:
    """One item of the overview graph.

    `designation` is `None` for an item that has none yet: `overview_graph` is the one query that
    tolerates it, so an overview of a half-finished design still draws. Otherwise it is
    `printed_designation`, behind its sign (`"-K1"`, `"-X1:L1:1"`), as a list prints it.
    """

    item: Id[Item]
    designation: str | None
    description: str
    parent: Id[Item] | None
    location_label: str | None
    mpn: str | None
    installed: bool


@value
class OverviewLink:
    """The connections between two items of one kind and one carrier, aggregated.

    `a` and `b` are the two items, the smaller id first. `via` is the cable item of a `CABLE`
    link, `None` otherwise; `via_designation` is that cable's `printed_designation` (`"-W1"`),
    `None` when there is no `via` or the cable has no designation yet. `count` is the number of
    conductors, or of mates for a `MATE` link; `conductors` are those conductors in id order,
    empty for a `MATE` link.
    """

    a: Id[Item]
    b: Id[Item]
    kind: OverviewLinkKind
    via: Id[Item] | None
    via_designation: str | None
    count: int
    conductors: tuple[Id[Conductor], ...]


@value
class OverviewPort:
    """One port of a signal: its item, the port and its marking (the port's name)."""

    item: Id[Item]
    port: Id[Port]
    marking: str


@value
class OverviewSignal:
    """One physical net that spans at least two items, for tracing a signal through the overview."""

    ports: tuple[OverviewPort, ...]


@value
class OverviewGraph:
    """Everything the overview output draws: the items, how they connect, the signals."""

    nodes: tuple[OverviewNode, ...]
    links: tuple[OverviewLink, ...]
    signals: tuple[OverviewSignal, ...]


# -- overview levels (`derive.overview_levels`, model-0197) ------------------


@value
class LineRef:
    """The identity of a line on a level: its two boxes in text order, its kind and its carrier.

    A box is a unit instance or an item id. `via` is the cable item of a cable line, else `None`.
    """

    a: Id[Any]
    b: Id[Any]
    kind: OverviewLinkKind
    via: Id[Item] | None


@value
class OverviewBox:
    """One box of a level: a nested unit, a folded strip or an item.

    `box` is a unit instance or an item id; `kind` is the item's kind, `None` for a unit.
    `lines` is the box text as the block diagram prints it, `tabs` the boundary or connector
    designations that stand on its border. `terminals` is a strip's terminal count, else 0.
    `group` and `location` are the item's effective function and location nodes.
    """

    box: Id[Any]
    kind: ItemKind | None
    lines: tuple[str, ...]
    tabs: tuple[str, ...]
    dashed: bool
    group: Id[AspectNode] | None
    location: Id[AspectNode] | None
    terminals: int


@value
class OverviewLine:
    """One line of a level, lifted from the connections it stands for.

    `count` is those connections: conductors, or mates for a mate line. `label` is the carrier's
    designation, "" for none. `conductors` is empty for a mate line.
    """

    ref: LineRef
    label: str
    count: int
    conductors: tuple[Id[Conductor], ...]


@value
class OverviewStub:
    """The outside end of connections leaving an opened unit, read as the schematic's stub is.

    `box` is the visible box inside the level. `far` is the far device's designation and `ports`
    its port tails (`stub_far_end`); `end` is its root item, `count` the connections it stands for.
    """

    box: Id[Any]
    kind: OverviewLinkKind
    via: Id[Item] | None
    far: str
    ports: str
    end: OverviewRef
    count: int


@value
class OverviewLevel:
    """One level of the overview: the system (`unit=None`) or an opened unit."""

    unit: Id[Unit] | None
    boxes: tuple[OverviewBox, ...]
    lines: tuple[OverviewLine, ...]
    stubs: tuple[OverviewStub, ...]


@value
class StripTerminal:
    """One terminal of an open strip, with its lines to the level's visible boxes."""

    item: Id[Item]
    label: str
    lines: tuple[OverviewLine, ...]


@value
class StripView:
    """An open strip: its terminals in strip order (group, then index)."""

    strip: Id[Item]
    terminals: tuple[StripTerminal, ...]


# -- overview matrix, lens and marks (model-0197) ----------------------------


@value
class MatrixCell:
    """The cables between two boxes of the matrix: `row` before `col` on the axis.

    `row` and `col` index `UnitMatrix.axis`; `count` is the number of distinct cables.
    """

    row: int
    col: int
    count: int
    cables: tuple[Id[Item], ...]


@value
class UnitMatrix:
    """The system-level boxes against each other: the axis in text order, the pairs with cables."""

    axis: tuple[OverviewBox, ...]
    cells: tuple[MatrixCell, ...]


@value
class LensChannel:
    """One channel of a PLC module for the Signals lens: its signal kind and field device.

    The device fields are `None` for a spare channel.
    """

    channel: Id[Function]
    number: int
    kind: SignalKind
    signal_name: str | None
    device: Id[Function] | None
    device_item: Id[Item] | None
    device_designation: str | None


@value
class LensModule:
    """One PLC module of the Signals lens with its channels in channel order."""

    module: Id[Item]
    designation: str
    channels: tuple[LensChannel, ...]


@value
class DiffMark:
    """The drawn boxes and lines one `ListingDiff` row marks on a level.

    `change` indexes `ListingDiff.changes`; `status` is that row's `added`, `removed` or `changed`.
    A removed row, or one of a section nothing draws, marks nothing.
    """

    change: int
    status: str
    boxes: tuple[Id[Any], ...]
    lines: tuple[LineRef, ...]


@value
class ExtUsage:
    """One `(kind, key)` pair still stored in some record's escape-hatch `ext` field.

    Not a Fransys output format: read by whoever maintains this repo to decide what
    to promote to a real field next, keeping `ext` honest (kernel-records.md 5.3 and
    derive-queries-structure.md).
    """

    kind: str
    key: str
    count: int
    subjects: tuple[Id[Any], ...]


# -- baseline listing rows (`derive.baseline`) ----------------------------


@value
class BaselineUnit:
    """The `unit` key of a baseline listing: the listed unit's own release facts."""

    name: str
    version: int
    revision: int
    interface: str


@value
class BaselineItem:
    """One `items` entry of a baseline listing; `parent` is its parent's designation (0212)."""

    designation: str
    mpn: str
    manufacturer: str
    installed: bool
    external: bool
    position: int | None
    parent: str | None = None


@value
class BaselineNestedUnit(BaselineUnit):
    """One `units` entry: a unit release directly nested in the listed unit, with its instances.

    `instances` names each instance sharing this `(name, version, revision)` release: the
    smallest, in sort order, of its own root items' unit designations in the listed unit.
    """

    instances: tuple[str, ...]


@value
class BaselineBoundary:
    """One `boundary` entry: a boundary function of the listed unit, with its stated rating."""

    designation: str
    ports: tuple[str, ...]
    rating: Rating | None
    operating: Operating | None


@value
class BaselineConductor:
    """One `conductors` entry: a conductor belonging to the listed unit."""

    kind: str
    a: str
    b: str
    carrier: str | None
    colour: str | None
    gauge_mm2: str | None
    length_mm: int | None
    label: str | None


@value
class BaselineMate:
    """One `mates` entry: a `Mate` with a side on an item of the listed unit itself."""

    a: str
    b: str


@value
class MateRow:
    """One `Mate` of the model, at any level: its two CONNECTOR or TERMINAL functions, with texts.

    `a` and `b` keep the authored order of `d.mate`. A designation is the text the connector list
    prints for that connector at system level (`connector_designation`).
    """

    a: Id[Function]
    b: Id[Function]
    a_designation: str
    b_designation: str


@value
class BaselineNet:
    """One `nets` entry: a `Net` with a member port on an item of the listed unit itself."""

    name: str | None
    net_class: str
    potential: str | None
    ports: tuple[str, ...]


@value
class Listing:
    """A unit's baseline listing: designation-relative, format-versioned."""

    unit: BaselineUnit
    items: tuple[BaselineItem, ...]
    units: tuple[BaselineNestedUnit, ...]
    boundary: tuple[BaselineBoundary, ...]
    conductors: tuple[BaselineConductor, ...]
    mates: tuple[BaselineMate, ...]
    nets: tuple[BaselineNet, ...]


@value
class Change:
    """One difference between two listings of the same unit (`derive.baseline.diff`).

    `subject` is the CSV-ready identity text (`Change`'s own `field`/`before`/`after` are
    always plain `str`, never a bare int or bool — the value already rendered). `parts` is the
    identity's own rendered pieces with NO backticks and NO joining, for a renderer that needs
    "between `a` and `b`" or "`instance` (name)" shapes without ever parsing `subject` (reports
    package rule: never parse a designation). `detail` is a short rendered description for an
    `added`/`removed` row that needs more than its bare identity to be legible (populated only
    for `items` and `boundary`, per the worked example -- every other section's
    `added`/`removed` rows carry `detail=""`; `changed` rows always carry `detail=""` too, since
    `field`/`before`/`after` already say what changed).
    """

    section: str
    change: str
    subject: str
    field: str
    before: str
    after: str
    parts: tuple[str, ...]
    detail: str


@value
class ListingDiff:
    """The change list from listing `a` to listing `b` (`derive.baseline.diff`)."""

    a: BaselineUnit
    b: BaselineUnit
    changes: tuple[Change, ...]
    ancestry: tuple[RemovedAncestry, ...] = ()


CHANGE_COLUMNS = ("section", "change", "subject", "field", "before", "after")


# -- numbering pins (`derive.numbering_pins`) ------------------


@value
class NumberingItem:
    """One `items` entry of a unit's numbering pins: an item that prints a designation.

    `key` is `derive.unit_relative_key`'s. `scope` is the relative key of the board or
    harness the item's designation reads through, `None` for none. `code` is the item's
    part's `class_code`, or `None` for a part-less item -- one record, one spelling of
    absence, matching `scope`'s own `None` (ruling 2026-09-27); `code` never gates
    reuse, a reserved text is taken by its `text` alone in its group. `text` is the
    item's OWN label (`derive.designation.own_designation_or_none`), never the full
    `item_designation` chain -- the release check compares on this field, not the
    chain. `authored` says whether the engineer wrote it (a tag) or the pass assigned it.
    """

    key: AuthoringKey
    scope: AuthoringKey | None
    code: str | None
    text: str
    authored: bool


@value
class NumberingRetired:
    """One `retired` entry: a designation given out earlier in this version.

    Its item is gone, or has moved to a different group or class code. `code` is `None` for
    a part-less item, the same spelling `NumberingItem.code` uses.
    """

    scope: AuthoringKey | None
    code: str | None
    text: str


@value
class NumberingPins:
    """A unit's numbering pins at release: `baseline/numbering.json`'s own shape."""

    items: tuple[NumberingItem, ...]
    retired: tuple[NumberingRetired, ...]


@value
class PartFunctionRow:
    """One function a part declares, with the rating it has.

    A part with no function template has one row: `template` is `None`, `name` is `""`, `kind` is
    `None`, and `rating` is the part's own. Otherwise `rating` is `effective_rating`: the
    template's, else the part's.
    """

    part: Id[Part]
    mpn: str
    template: Id[FunctionTemplate] | None
    name: str
    kind: FunctionKind | None
    rating: Rating | None


@value
class HarnessLineEnd:
    """One end of a harness or cable line: `plug` is its connector function, else `ports` fan out.

    `branch` is the 1-based n of `-W13.n`. `mates` is the function `d.mate` joins `plug` to, or
    `None` for a fan-out or an unmated plug.
    """

    harness: Id[Item]
    branch: int
    plug: Id[Function] | None
    ports: tuple[Id[Port], ...]
    mates: Id[Function] | None


@value
class ReadabilityPage:
    """What `fr.readability` measures of one schematic page.

    `drawing_set` and `number` are as printed.
    `text_height_mm` is the profile's capital height of text
    and `min_text_height_mm` its floor for it. `fill_percent` is the share of the content box the
    drawn content covers, in whole percent. The four counts are the lint findings' own:
    `wire_crossings` (two wires of different conductors crossing), `struck_labels`
    (`WIRE_OVER_LABEL`), `text_overlaps` (`TEXT_OVERLAP`) and `lone_cells` (`LONE_CELL`).
    The references drawn on the page: contact images with the contacts they list, stars with the
    branches they name, and page cuts, which name one other page each. `single_*` counts the
    images with one contact and the stars with one branch; `single_contact_images_other_page` counts
    the single images whose contact is on another page.
    """

    page: Id[Page]
    unit: Id[Unit] | None
    drawing_set: int
    number: int
    text_height_mm: Decimal
    min_text_height_mm: Decimal
    fill_percent: int
    wire_crossings: int
    struck_labels: int
    text_overlaps: int
    lone_cells: int
    contact_images: int
    contact_image_targets: int
    single_contact_images: int
    single_contact_images_other_page: int
    stars: int
    star_branches: int
    single_branch_stars: int
    page_cuts: int


@value
class ReadabilityUnit:
    """One unit's pages together: counts add up, `text_height_mm` and `fill_percent` are the lowest.

    `unit` is `None` for the design's own pages. `min_text_height_mm` is the highest floor of them.
    """

    unit: Id[Unit] | None
    pages: int
    text_height_mm: Decimal
    min_text_height_mm: Decimal
    fill_percent: int
    wire_crossings: int
    struck_labels: int
    text_overlaps: int
    lone_cells: int
    contact_images: int
    contact_image_targets: int
    single_contact_images: int
    single_contact_images_other_page: int
    stars: int
    star_branches: int
    single_branch_stars: int
    page_cuts: int


@value
class ReadabilityReport:
    """What `fr.readability` returns: a row for each schematic page, and for each unit."""

    pages: tuple[ReadabilityPage, ...]
    units: tuple[ReadabilityUnit, ...]
