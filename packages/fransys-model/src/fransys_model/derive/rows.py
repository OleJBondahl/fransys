"""Report row shapes: one `@value` per Fransys output format (derive-queries.md and examples.md).

Defined once here; the query modules build them; Fransys formats them to CSV, XLSX, XML or
Typst and never reshapes them. Reference fields are ids; anything a human reads is
already rendered (`derive.designation`), so no formatter ever re-derives or re-parses a
label. All numeric fields are `int` or `Decimal`, never `float`; every sequence is a
`tuple`.

The list outputs' shared read of these rows lives at the bottom, once: which fields of each
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
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import Gender, SignalType
from fransys_model.vocab.ratings import Operating, Rating
from fransys_model.vocab.templates import Part


@value
class TerminalRow:
    """One terminal of a strip's connection list.

    An unused terminal has empty `internal`/`external` tuples; bridged terminals share one
    `jumper_group` number. `internal_ends` and `external_ends`
    are the rendered far-end port designations of those conductors, aligned index for index
    with `internal` and `external`: `internal_ends[i]` is where `internal[i]` goes. Given a
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
    """One PLC channel's wiring line: channel, signal, where it is wired.

    `wired_to` is where the builder wires the channel's pin: the printed far end of every
    conductor at the channel function's ports, sorted and joined with `CELL_SEPARATOR`, `None`
    when nothing is printed. `field_device` and
    `field_device_designation` are the device bound to the channel, `signal_name` its request's: the
    rack modules read the same fields (`PlcRackChannel`); the list prints `signal_name` but not
    `field_device` or `field_device_designation` (`PLC_COLUMNS`). All three are `None` for an
    allocated-but-unbound channel. Every designation is signed (`"-A3:1"`,
    `"-B12"`, `"-J1:1"`).
    """

    channel: Id[Function]
    channel_designation: str
    signal: SignalType
    wired_to: str | None
    field_device: Id[Function] | None
    field_device_designation: str | None
    signal_name: str | None


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
    """One line of the tag/designation list (design/derive-queries.md `designation_list`)."""

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
    `footprint`: the parts a netlist cannot place, which the query omits from `parts`.
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
    """

    port: Id[Port]
    marking: str
    net: str | None
    mate_port: Id[Port] | None
    mate_port_designation: str | None


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
    (`designation.cable_end_rank`/`cable_end_owner`), not `Conductor.a`/`.b`'s raw port-id order, so
    `end_a` is always the same physical end for every core that lands on it.
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
    the text the drawing's cable node title prints.
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


@value
class CableListRow:
    """One top-level cable of the system document's cable list.

    `mpn`, `description`, `core_count`, `gauge_mm2` and `length_mm` are `HarnessCable`'s own
    facts, `None` where the part or facet is absent. `designation` is the cable's
    `printed_designation` (`"-W1"`). `from_label` and `to_label` are the `HarnessEnd.designation`
    of the two lowest-ranked ends (`designation.cable_end_rank`), the text
    the drawing prints, so a cable authored either way round reads the same way round. With one
    end `to_label` is `""`, with none both are; ends beyond the second are left out.
    """

    cable: Id[Item]
    designation: str
    mpn: str | None
    description: str | None
    core_count: int | None
    gauge_mm2: Decimal | None
    length_mm: int | None
    from_label: str
    to_label: str


@value
class ContentsRow:
    """One cable of a document's CONTENTS page.

    `mpn`, `description`, `core_count`, `gauge_mm2` and `length_mm` are `HarnessCable`'s own
    facts, as in `CableListRow`. `designation` is the cable's `printed_designation` (`"-W1"`).
    `ends` is every end's `designation` in the cable's end order, joined by an en dash, a blank
    end (outside a nested unit) dropped with its dash; unlike `CableListRow` it keeps
    every end. It is text, not a tuple, so `cell_text` cannot join it with `CELL_SEPARATOR`.
    """

    cable: Id[Item]
    designation: str
    mpn: str | None
    description: str | None
    core_count: int | None
    gauge_mm2: Decimal | None
    length_mm: int | None
    ends: str


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


# -- baseline listing rows (baseline spec L2, `derive.baseline`) ----------------------------


@value
class BaselineUnit:
    """The `unit` key of a baseline listing: the listed unit's own release facts."""

    name: str
    version: int
    revision: int
    interface: str


@value
class BaselineItem:
    """One `items` entry of a baseline listing: an item of the listed unit itself."""

    designation: str
    mpn: str
    manufacturer: str
    installed: bool
    external: bool
    position: int | None


@value
class BaselineNestedUnit:
    """One `units` entry: a unit release directly nested in the listed unit, with its instances.

    `instances` names each instance sharing this `(name, version, revision)` release: the
    smallest, in sort order, of its own root items' unit designations in the listed unit.
    """

    name: str
    version: int
    revision: int
    interface: str
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
    """One `conductors` entry: a conductor belonging to the listed unit (units spec U6)."""

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
class BaselineNet:
    """One `nets` entry: a `Net` with a member port on an item of the listed unit itself."""

    name: str | None
    net_class: str
    potential: str | None
    ports: tuple[str, ...]


@value
class Listing:
    """A unit's baseline listing (baseline spec L2): designation-relative, format-versioned."""

    unit: BaselineUnit
    items: tuple[BaselineItem, ...]
    units: tuple[BaselineNestedUnit, ...]
    boundary: tuple[BaselineBoundary, ...]
    conductors: tuple[BaselineConductor, ...]
    mates: tuple[BaselineMate, ...]
    nets: tuple[BaselineNet, ...]


@value
class Change:
    """One difference between two listings of the same unit (`derive.baseline.diff`, M1).

    `subject` is the CSV-ready identity text (`Change`'s own `field`/`before`/`after` are
    always plain `str`, never a bare int or bool — the value already rendered). `parts` is the
    identity's own rendered pieces with NO backticks and NO joining, for a renderer that needs
    "between `a` and `b`" or "`instance` (name)" shapes without ever parsing `subject` (reports
    package rule: never parse a designation). `detail` is a short rendered description for an
    `added`/`removed` row that needs more than its bare identity to be legible (populated only
    for `items` and `boundary`, per the spec's own worked example -- every other section's
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
    """The change list from listing `a` to listing `b` (`derive.baseline.diff`, M1)."""

    a: BaselineUnit
    b: BaselineUnit
    changes: tuple[Change, ...]


CHANGE_COLUMNS = ("section", "change", "subject", "field", "before", "after")


# -- numbering pins (fixed-designations spec FD3, `derive.numbering_pins`) ------------------


@value
class NumberingItem:
    """One `items` entry of a unit's numbering pins (FD3): an item that prints a designation.

    `key` is `derive.unit_relative_key`'s (FD2). `scope` is the relative key of the board or
    harness the item's designation reads through, `None` for none. `code` is the item's
    part's `class_code`, or `None` for a part-less item -- one record, one spelling of
    absence, matching `scope`'s own `None` (designer ruling 2026-09-27); `code` never gates
    reuse, a reserved text is taken by its `text` alone in its group (FD5). `text` is the
    item's OWN label (`derive.designation.own_designation_or_none`), never the full
    `item_designation` chain -- the release check (FD6) compares on this field, not the
    chain. `authored` says whether the engineer wrote it (a tag) or the pass assigned it.
    """

    key: AuthoringKey
    scope: AuthoringKey | None
    code: str | None
    text: str
    authored: bool


@value
class NumberingRetired:
    """One `retired` entry (FD3, FD5): a designation given out earlier in this version.

    Its item is gone, or has moved to a different group or class code. `code` is `None` for
    a part-less item, the same spelling `NumberingItem.code` uses.
    """

    scope: AuthoringKey | None
    code: str | None
    text: str


@value
class NumberingPins:
    """A unit's numbering pins at release (FD3): `baseline/numbering.json`'s own shape."""

    items: tuple[NumberingItem, ...]
    retired: tuple[NumberingRetired, ...]


# -- what the list outputs print of these rows (the PDF lists and the CSVs, one read) -------

# The human-readable fields of each row shape, in the row's field order. An `Id` field is left
# out where the row carries its rendered twin (`terminal` and `designation`, `part` and `mpn`,
# `internal` and `internal_ends`).
TERMINAL_COLUMNS = (
    "designation",
    "group",
    "index",
    "internal_ends",
    "external_ends",
    "jumper_group",
)
# The terminal list's two ends columns are the terminal's port roles, internal then external
# (owner ruling 2026-09-24): headed by these labels, not by the field name. The CSV's header is
# the same label lower-cased with `_` for the space (`side_a`, `side_b`).
TERMINAL_LABELS = {"internal_ends": "Side A", "external_ends": "Side B"}
PLC_COLUMNS = ("channel_designation", "signal", "wired_to", "signal_name")
BOM_COLUMNS = ("mpn", "revision", "manufacturer", "description", "count", "designations")
WIRE_COLUMNS = ("from_", "to", "colour", "cross_section_mm2", "label")
WIRE_LABELS = {"from_": "from"}  # the CSV header of the one column whose field name is a keyword
DESIGNATION_COLUMNS = ("designation", "reference", "description")
# A connector row repeats on each of its pins, so a line is the connector's fields, then the pin's.
CONNECTOR_COLUMNS = ("designation", "style", "pincount", "gender", "mate_designation")
PIN_COLUMNS = ("marking", "net", "mate_port_designation")
CABLE_LIST_COLUMNS = (
    "designation",
    "mpn",
    "description",
    "core_count",
    "gauge_mm2",
    "length_mm",
    "from_label",
    "to_label",
)
CONTENTS_COLUMNS = (
    "designation",
    "mpn",
    "description",
    "core_count",
    "gauge_mm2",
    "length_mm",
    "ends",
)
