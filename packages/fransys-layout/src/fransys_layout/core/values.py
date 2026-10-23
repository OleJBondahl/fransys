"""Values of the placer core, input side: the problem, the options, stage 1 to 4 outputs.

Frozen plain data; outputs.py holds the placement, route, text and layout values, and
jsonform.py gives every value here a JSON form. Lengths are in G; x grows right, y down.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal
lazy from collections.abc import Mapping

lazy from .annex_values import Annex
lazy from .series_values import Series
lazy from .sym_values import Sym

XY = tuple[int, int]

Side = Literal["N", "E", "S", "W"]
Orientation = Literal["R0", "R90", "R180", "R270", "MR0", "MR90", "MR180", "MR270"]
EndKind = Literal["biased", "boxpin", "boundary", "fan", "crosslink", "join", "open"]
BlockKind = Literal["card", "fan", "column", "blackbox"]
Seat = Literal["none", "beside", "alone"]


class RefKind(StrEnum):
    """What a reference is; read through `ref_kind.kind_of`, the one reader (layout-0292)."""

    TAG = "tag"
    ARROW = "arrow"
    STAR = "star"
    STUB = "stub"
    COPY = "copy"


MarkerKind = RefKind
WireKind = Literal["straight", "drop", "riser", "trunk", "routed", "join"]
FindingCode = Literal[
    "CARD_OVERFULL",
    "NO_CELL",
    "LANE_WIRE_DROPPED",
    "NO_BLOCK",
    "BLOCK_NOT_PLACED",
    "CHAIN_REFUSED",
    "ORDER_HINT_UNMET",
    "KEEP_TOGETHER_UNMET",
    "HEAD_OFF_LEGS",
    "ALIGN_DROPPED",
    "ROUTE_FAILED",
    "PAGE_OVERFLOW",
    "TEXT_OVERLAP",
    "ANNEX_UNPLACED",
    "FILL_UNDER_MIN",
    "WIDER_THAN_PAGE",
    "LANE_TURNED",
    "MARKER_UNPLACED",
    "WIRE_MEETS_NET",
]


@dataclass(frozen=True, slots=True)
class Box:
    """A rectangle; relative to a symbol origin at R0 unless a field says absolute."""

    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True, slots=True)
class Size:
    """A width and height, in G."""

    w: int
    h: int


@dataclass(frozen=True, slots=True, order=True)
class PinRef:
    """A pin of one symbol, named by the symbol id and the pin id."""

    sym: str
    pin: str


@dataclass(frozen=True, slots=True)
class Pin:
    """Fact 1: side is the way a wire leaves; node indexes Sym.nodes; end_bias < 0 heads, > 0 feet.

    end_rank orders the biased ends among themselves, a smaller rank first.
    """

    id: str
    side: Side
    dx: int
    dy: int
    node: int
    end_bias: int = 0
    end_rank: int = 0


@dataclass(frozen=True, slots=True)
class BoxSpec:
    """Fact 16: movable pins in printed-marking order; margin is body beyond the end pins."""

    order: tuple[str, ...]
    natural_edge: str
    min_pitch: int
    margin: int


@dataclass(frozen=True, slots=True)
class Bundle:
    """Nets with one id travel as one trunk; `pole` is the lane index the caller passes for it."""

    id: str
    pole: int


@dataclass(frozen=True, slots=True)
class Net:
    """A net: its id, the pins it joins, and its bundle, unit-crossing and label facts."""

    id: str
    pins: tuple[PinRef, ...]
    bundle: Bundle | None = None
    crosses_unit: bool = False
    label: Size | None = None


@dataclass(frozen=True, slots=True)
class Unit:
    """A unit: its id, its parent unit, and the pins on its boundary."""

    id: str
    parent: str | None
    boundary: tuple[PinRef, ...]


@dataclass(frozen=True, slots=True)
class Facts:
    """Problem facts: groups kept whole, units, mated pins, one series per region."""

    keep_whole: tuple[frozenset[str], ...] = ()
    units: tuple[Unit, ...] = ()
    mates: tuple[tuple[PinRef, PinRef], ...] = ()
    series: tuple[Series, ...] = ()


@dataclass(frozen=True, slots=True)
class Hints:
    """Authored hints; every name is a group or a symbol id, resolved by the builder."""

    group_order: tuple[str, ...] = ()
    break_before: frozenset[str] = frozenset()
    keep_together: tuple[frozenset[str], ...] = ()
    order_pairs: tuple[tuple[str, str], ...] = ()
    chains: tuple[tuple[str, ...], ...] = ()
    draw_in: tuple[tuple[str, str], ...] = ()
    sides: tuple[tuple[PinRef, str], ...] = ()


@dataclass(frozen=True, slots=True)
class Pose:
    """How an anchored item sits at a pin; `origin`, `outline` and `port` are relative to it (SB4).

    `port` is where the lead from the pin ends.
    """

    turn: Orientation
    origin: tuple[int, int]
    outline: Box
    port: tuple[int, int]


@dataclass(frozen=True, slots=True)
class Anchor:
    """A one-port item anchored at the end of `pin`: its Pose for each side the pin may leave on."""

    pin: PinRef
    poses: tuple[tuple[Side, Pose], ...]


@dataclass(frozen=True, slots=True)
class PlacementProblem:
    """The placer's input: the area, the symbols, the nets, the facts and the hints."""

    area: Size
    symbols: tuple[Sym, ...]
    nets: tuple[Net, ...]
    facts: Facts
    hints: Hints = field(default_factory=Hints)
    anchors: tuple[Anchor, ...] = ()
    annexes: tuple[Annex, ...] = ()


@dataclass(frozen=True, slots=True)
class Options:
    """Design 2.2 with E4: pins spread, justify on; flow is top to bottom (spec ruling)."""

    margin: Size = field(kw_only=True)
    wiring_grid: int = field(kw_only=True)
    wire_min: int = field(kw_only=True)
    column_gap_min: int = field(kw_only=True)
    row_gap: int = field(kw_only=True)
    box_pin_pitch_min: int = field(kw_only=True)
    box_pins: str = field(kw_only=True)
    short_height: float = field(kw_only=True)
    min_fill: float = field(kw_only=True)
    exact_order_limit: int = field(kw_only=True)
    exact_order_nodes: int = field(kw_only=True)
    tag_stagger: bool = field(kw_only=True)
    label_gap: int = field(kw_only=True)  # the distance a designation keeps from a wire
    justify: bool = field(kw_only=True)
    # False: justify leaves a card's pin and column pitch at the footprint minimum
    justify_cards: bool = field(kw_only=True)
    # edge pairs (e.g. ("N", "S")): pin k of the first edge and pin k of the second share one x
    pin_pairs: tuple[tuple[str, str], ...] = field(kw_only=True)
    band_align: bool = field(kw_only=True)
    w_tag: float = field(kw_only=True)
    w_arrow: float = field(kw_only=True)
    w_ref: float = field(kw_only=True)
    w_p: float = field(kw_only=True)
    w_f: float = field(kw_only=True)
    w_row: float = field(kw_only=True)
    w_violation: float = field(kw_only=True)
    # round(score.WEIGHTS["b"] / WEIGHTS["d"]): the router trades as the scorer does
    bend_penalty: int = field(kw_only=True)
    crossing_penalty: int = field(kw_only=True)  # round(score.WEIGHTS["x"] / WEIGHTS["d"])
    box_margin: int = field(kw_only=True)  # body beyond a box's end pins when its spec gives none
    column_wire_lanes: int = field(kw_only=True)  # grids a column's height holds past its cells
    jog_lanes: int = field(kw_only=True)  # grids a jog at level 0 takes between its two pins
    spare_cells: int = field(kw_only=True)  # grid cells an occupancy keeps past its extent
    reroute_rounds: int = field(kw_only=True)
    recut_rounds: int = field(kw_only=True)
    solve_rounds: int = field(
        kw_only=True
    )  # layouts after the first that hold missed anchor outlines
    # owner 2026-10-18: a designation stands in a corner of its symbol, top left by default
    corner_order: tuple[str, ...] = field(kw_only=True)
    slack: tuple[int, ...] = field(kw_only=True)
    # layout-0305, SB4: the reference-marker symbol's keepout box at each orientation, in grid
    # units relative to its origin; the symdef layer measures it, so the core types no size
    marker: Mapping[Orientation, Box] | None = None
    # R318: the boxes of a marker whose text the caller fitted, by (pin, kind text); the symdef
    # layer measured each, and a marker not named here takes `marker`
    marker_fit: Mapping[tuple[PinRef, str], Mapping[Orientation, Box]] = field(
        default_factory=frozendict
    )
    # R377: the views whose box lies above or below its pin, and the one that lies above; el
    # passes them from the marker symbol's facing, so the core names no view
    marker_vertical: frozenset[Orientation] = frozenset()
    marker_above: Orientation | None = None
    marker_below: Orientation | None = None
    # R350: the box of an arrow, fitted to the widest text it can print
    link_fit: Mapping[Orientation, Box] | None = None
    cells: tuple[int, int] = field(kw_only=True)
    # layout-0310: a run direction ("horiz" or "vert") then the sides a wire label tries, in order
    wire_label_sides: tuple[tuple[str, ...], ...] = (("horiz", "N", "S"), ("vert", "E", "W"))
    open_stub: int = field(kw_only=True)
    box_columns: bool = field(kw_only=True)
    bundle_direction: bool = False  # layout-0363: a bundle takes one direction, else one per chain
    # layout-0309: a keep-whole fan wider alone than the page may wrap at a column;
    # False keeps it one row
    wrap_wide_fans: bool = field(kw_only=True)
    # layout-0334 (from layout-0031 and layout-0035): whole wiring lanes kept free above row 0
    # and below the last row, so a turn and its label stay inside the content box;
    # `margin.h` is no longer read
    top_headroom_lanes: int = field(kw_only=True)
    bottom_headroom_lanes: int = field(kw_only=True)
    # how far a pin's end_bias pulls its chain end toward the head (below 0) or the foot (above 0),
    # against the one-step pull of the pin's side
    end_bias_weight: int = field(kw_only=True)
    # the turn that flips a chain's cell; the base orientation is R0
    flip_turn: Orientation = field(kw_only=True)
    # the first driver column of a fan block stands first
    driver_first: bool = field(kw_only=True)
    # the sides a reference arrow's first and second end stand on, at the trunk's end on that side
    arrow_sides: tuple[Side, Side] = field(kw_only=True)

    @property
    def top_headroom(self) -> int:
        """The G above row 0 that stay free (layout-0031)."""
        return self.top_headroom_lanes * self.wiring_grid

    @property
    def page_headroom(self) -> int:
        """The G the top and bottom headroom take from a page's height (layout-0031, 0035)."""
        return (self.top_headroom_lanes + self.bottom_headroom_lanes) * self.wiring_grid


@dataclass(frozen=True, slots=True)
class Cell:
    """One symbol in a lane; top_pin is on the head side and bottom_pin on the foot side."""

    sym: str
    orient: Orientation
    top_pin: str | None
    bottom_pin: str | None


@dataclass(frozen=True, slots=True)
class Lane:
    """Cells from head to foot; offset is the lane's x against lane 0 of its column."""

    cells: tuple[Cell, ...]
    offset: int


@dataclass(frozen=True, slots=True)
class End:
    """A lane's end: biased, boxpin, boundary, fan, crosslink, join or open.

    lane is the index into the column's lanes this end belongs to; None means every lane.
    """

    kind: EndKind
    net: str | None = None
    pin: PinRef | None = None
    fan: str | None = None
    lane: int | None = None

    @property
    def is_join(self) -> bool:
        """The one place that asks whether an end is a folded member's join."""
        return self.kind == "join"


@dataclass(frozen=True, slots=True)
class Column:
    """width and height are a cache of the cells' extent; width spans the full footprints."""

    id: str
    lanes: tuple[Lane, ...]
    heads: tuple[End, ...]
    feet: tuple[End, ...]
    height: int
    width: int
    hops: tuple[tuple[str, ...], ...] = ()

    @property
    def is_chain(self) -> bool:
        """The one place that asks whether a column is a chain of boxes."""
        return bool(self.hops)


@dataclass(frozen=True, slots=True)
class Attach:
    """Where a trunk meets a lane: pin of cell `cell` in lane `lane`; column None is a box pin.

    `pole` is a lane index, a value the caller passes; `lane` is the column's own index.
    """

    column: str | None
    lane: int
    cell: int
    pin: PinRef
    pole: int = 0


@dataclass(frozen=True, slots=True)
class Fan:
    """A trunk: drivers drop to it from above, legs hang from it; side says where it lies."""

    id: str
    nets: tuple[str, ...]
    drivers: tuple[Attach, ...]
    legs: tuple[Attach, ...]
    hub: str | None
    lanes: int
    side: str
    crossed: tuple[tuple[str, tuple[int, ...]], ...] = ()
    head: Attach | None = None


@dataclass(frozen=True, slots=True)
class CrossLink:
    """A net that crosses between column ends, given by its attachments."""

    net: str
    ends: tuple[Attach, ...]


@dataclass(frozen=True, slots=True)
class BiasedEnd:
    """A pin that prefers an end of its chain, with its rank among the biased ends."""

    sym: str
    pin: str
    rank: int


@dataclass(frozen=True, slots=True)
class CycleSplit:
    """How many bundles, ladders and cross links were cut to break cycles in the flow."""

    bundles: int
    ladders: int
    cross_links: int


@dataclass(frozen=True, slots=True)
class FlowGraph:
    """The flow after stage 2: columns, fans, cross links, biased ends, cycle split, drawn."""

    columns: tuple[Column, ...]
    fans: tuple[Fan, ...]
    cross_links: tuple[CrossLink, ...]
    biased: tuple[BiasedEnd, ...]
    cycle_split: CycleSplit
    drawn: tuple[str, ...]
    findings: tuple[Finding, ...] = ()


@dataclass(frozen=True, slots=True)
class Block:
    """pin_edges maps a card's pin to the edge it uses; id is opaque, read kind and anchor.

    seat: "beside" a column-less card stage 3 put after a fan block, "alone" one stage 3 gave a row
    of its own, "none" every other block (layout-0288); stage 4 cuts no other column-less card.
    """

    id: str
    kind: BlockKind
    unit: str
    columns: tuple[str, ...]
    anchor: str | None
    fan: str | None
    group: str | None
    width_est: int
    height_est: int
    short: bool
    keep_whole: bool
    forced_break_before: bool
    seat: Seat
    pin_edges: tuple[tuple[str, str], ...] = ()
    fixed_order: bool = False
    rise: int = 0

    @property
    def is_card(self) -> bool:
        """The one place that asks whether a block is a card box."""
        return self.kind == "card"


@dataclass(frozen=True, slots=True)
class BlockList:
    """The blocks of one unit, with the findings raised while building them."""

    unit: str
    blocks: tuple[Block, ...]
    findings: tuple[Finding, ...] = ()


@dataclass(frozen=True, slots=True)
class RowPlan:
    """One row of a page plan: its columns, its blocks and its estimated height."""

    columns: tuple[str, ...]
    blocks: tuple[str, ...]
    height_est: int


@dataclass(frozen=True, slots=True)
class PagePlan:
    """One planned page of a unit: its rows, whether it is forced to end, and its groups."""

    page: int
    unit: str
    rows: tuple[RowPlan, ...]
    forced_end: bool
    groups: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RefEnd:
    """One end of a reference: its page, column, pin and row."""

    page: int
    column: str | None
    pin: PinRef | None
    row: int | None = None


@dataclass(frozen=True, slots=True)
class Ref:
    """A cut net drawn as references at its ends."""

    net: str
    kind: RefKind
    ends: tuple[RefEnd, ...]


@dataclass(frozen=True, slots=True)
class Finding:
    """A finding the placer raised: its code, its text, and optionally its page and subject."""

    code: FindingCode
    text: str
    page: int | None = None
    subject: str | None = None


@dataclass(frozen=True, slots=True)
class PageSpec:
    """The page plan for all units, with the reference plan and the findings."""

    pages: tuple[PagePlan, ...]
    reference_plan: tuple[Ref, ...]
    findings: tuple[Finding, ...] = ()


@dataclass(frozen=True, slots=True)
class CutResult:
    """The spec, plus the flow and blocks after tall-column cuts; later stages read these."""

    spec: PageSpec
    flow: FlowGraph
    blocks: tuple[BlockList, ...]
