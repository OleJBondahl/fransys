"""Values of the placer core, input side: the problem, the options, stage 1 to 4 outputs.

Frozen plain data; outputs.py holds the placement, route, text and layout values, and
jsonform.py gives every value here a JSON form. Lengths are in G; x grows right, y down.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Literal
lazy from collections.abc import Mapping

lazy from .annex_values import Annex
lazy from .series_values import Series
lazy from .sym_values import Sym

XY = tuple[int, int]

Side = Literal["N", "E", "S", "W"]
Orientation = Literal["R0", "R90", "R180", "R270", "MR0", "MR90", "MR180", "MR270"]


class RefKind(StrEnum):
    """What a reference is; read through `ref_kind.kind_of`, the one reader (layout-0292)."""

    TAG = "tag"
    ARROW = "arrow"
    STAR = "star"
    STUB = "stub"
    COPY = "copy"


class StandClass(StrEnum):
    """Where a reference end stands, decided with the end at the cut (CUT-LEDGER CL2): at its pin, at its fan's trunk end, or below its lane."""

    PIN = "pin"
    TRUNK_END = "trunk_end"
    LEG = "leg"


class RowTerm(StrEnum):
    """The term that set a placed row's height: its cells, its cards, the markers hung at them, its trunks' room or its annexes (R1939).

    Members are in tie order: of equal reaches the earlier member wins (`row_measure.row_term`).
    """

    BODY = "body"
    CARD = "card"
    MARKER_ROOM = "marker_room"
    STUB = "stub"
    ANNEX = "annex"


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
    "HEAD_OFF_LEGS",
    "ALIGN_DROPPED",
    "WIRE_AS_REFERENCE",
    "WIRE_THROUGH_BODY",
    "PAGE_OVERFLOW",
    "ANNEX_UNPLACED",
    "OUTLINE_NO_ROOM",
    "FILL_UNDER_MIN",
    "WIDER_THAN_PAGE",
    "LANE_TURNED",
    "MARKER_UNPLACED",
    "WIRE_MEETS_NET",
    "TAG_ACROSS_BODY",
    "PLACEMENT_PROBLEM",
]


@dataclass(frozen=True, slots=True)
class Box:
    """A rectangle; relative to a symbol origin at R0 unless a field says absolute."""

    x: int
    y: int
    w: int
    h: int


def g_text(units: int) -> str:
    """`units` layout units (eight to a G) as the engineer's G, an exact decimal: 2468 is "308.5", 960 is "120"."""
    return f"{Decimal(units) / 8:f}"


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
    margin: int


@dataclass(frozen=True, slots=True)
class Bundle:
    """Nets with one id travel as one trunk; `pole` is the lane index the caller passes for it.

    `form` names what the trunk is (the caller's word); `Options.trunk_forms` lists those that always trunk.
    """

    id: str
    pole: int
    form: str = ""


@dataclass(frozen=True, slots=True)
class CutEnd:
    """A pin whose net continues outside the set; pins of one `line` leave in one stub."""

    pin: PinRef
    line: str = ""


@dataclass(frozen=True, slots=True)
class Net:
    """A net: its id, pins, bundle, unit-crossing facts, `cut` ends off the set, and `tagged` links drawn as a tag pair (layout-0508)."""

    id: str
    pins: tuple[PinRef, ...]
    bundle: Bundle | None = None
    crosses_unit: bool = False
    cut: tuple[CutEnd, ...] = ()
    tagged: tuple[tuple[PinRef, ...], ...] = ()


@dataclass(frozen=True, slots=True)
class Unit:
    """A unit: its id, its parent unit, and the pins on its boundary."""

    id: str
    parent: str | None
    boundary: tuple[PinRef, ...]


@dataclass(frozen=True, slots=True)
class Facts:
    """Problem facts: groups kept whole, units, mated pins, series, page-free far ends, the model's required pin groups."""

    keep_whole: tuple[frozenset[str], ...] = ()
    units: tuple[Unit, ...] = ()
    mates: tuple[tuple[PinRef, PinRef], ...] = ()
    series: tuple[Series, ...] = ()
    far_ends: tuple[tuple[PinRef, PinRef], ...] = ()
    groups: tuple[tuple[PinRef, ...], ...] = ()


@dataclass(frozen=True, slots=True)
class Hints:
    """Authored hints; every name is a group or a symbol id, resolved by the builder."""

    group_order: tuple[str, ...] = ()
    order_pairs: tuple[tuple[str, str], ...] = ()
    frames: tuple[tuple[str, frozenset[str]], ...] = ()  # R900 G9: (unit key, member symbol ids) of each unit frame


@dataclass(frozen=True, slots=True)
class OutlineRoom:
    """What a unit frame needs of its symbol (R889, R900): the margin off the boxes it holds, the label slot box and the size it never draws below.

    `label` is relative to the frame's top-left corner; the symdef layer copies both fields from the library.
    """

    margin: int
    label: Box
    least: Size


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
    wider: tuple[
        tuple[Annex, ...], ...
    ] = ()  # the annexes at 2, 3, ... digits of a where-text page number (R1883): `widen` swaps them in as pages grow


@dataclass(frozen=True, slots=True)
class Options:
    """Design 2.2 with E4: pins spread, justify on; flow is top to bottom (spec ruling)."""

    margin: Size = field(kw_only=True)
    wiring_grid: int = field(kw_only=True)
    wire_min: int = field(kw_only=True)
    column_gap_min: int = field(kw_only=True)
    parallel_pitch: int = field(kw_only=True)  # G between the axes of two parallel branches
    row_gap: int = field(kw_only=True)
    box_pin_pitch_min: int = field(kw_only=True)
    box_pins: str = field(kw_only=True)
    short_height: float = field(kw_only=True)
    min_fill: float = field(kw_only=True)
    exact_order_limit: int = field(kw_only=True)
    exact_order_nodes: int = field(kw_only=True)
    tag_stagger: bool = field(kw_only=True)
    label_gap: int = field(kw_only=True)  # the distance a designation keeps from a wire
    # edge pairs (e.g. ("N", "S")): pin k of the first edge and pin k of the second share one x
    pin_pairs: tuple[tuple[str, str], ...] = field(kw_only=True)
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
    share_penalty: int = field(kw_only=True)  # a negotiated round's price of a cell another net holds
    history_step: int = field(kw_only=True)  # added to a shared cell's history after each round
    ripup_worst: int = field(kw_only=True)  # links laid alone again after a negotiation, most crossings first
    recut_rounds: int = field(kw_only=True)
    where_digit_rounds: int = field(kw_only=True)  # rises of the where-text page number's digit count `widen` follows (R1883)
    label_moves: int = field(kw_only=True)  # standing labels a blocked label may move before the recut (R1479)
    route_fallback_rounds: int = field(kw_only=True)  # routing and reference loop bound (R1246)
    solve_rounds: int = field(kw_only=True)  # layouts after the first that hold missed anchor outlines
    widen_rounds_limit: int = field(kw_only=True)  # widen passes before it raises CoreError (R1981)
    # owner 2026-10-18: a designation stands in a corner of its symbol, top left by default
    corner_order: tuple[str, ...] = field(kw_only=True)
    # layout-0305, SB4: the reference-marker symbol's keepout box at each orientation, in grid
    # units relative to its origin; the symdef layer measures it, so the core types no size
    marker: Mapping[Orientation, Box] | None = None
    # R318: the boxes of a marker whose text the caller fitted, by (pin, kind text); the symdef
    # layer measured each, and a marker not named here takes `marker`
    marker_fit: Mapping[tuple[PinRef, str], Mapping[Orientation, Box]] = field(default_factory=frozendict)
    # R1597: the width (G) of each line a stub prints for the conductor (near pin, far pin), an upper bound that needs no
    # placement, and the box (by orientation) of a stub with that widest width and that many lines; the ledger's lines pick the box
    stub_lines: Mapping[tuple[PinRef, PinRef], tuple[int, ...]] = field(default_factory=frozendict)
    stub_table: Mapping[tuple[int, int], Mapping[Orientation, Box]] = field(default_factory=frozendict)
    # R377: the views whose box lies above or below its pin, and the one that lies above; el
    # passes them from the marker symbol's facing, so the core names no view
    marker_vertical: frozenset[Orientation] = frozenset()
    # layout-0375: the turn that points a marker's box along each side of its pin; the symdef layer
    # passes `MARKER_FACING` once, and the core names no turn of its own
    marker_facing: Mapping[Side, Orientation] = field(kw_only=True)
    marker_above: Orientation | None = None
    marker_below: Orientation | None = None
    outline: OutlineRoom | None = None  # R889, R900: the unit frame's room; None draws no frame
    # R350: the box of an arrow, fitted to the widest text it can print
    link_fit: Mapping[Orientation, Box] | None = None
    cells: tuple[int, int] = field(kw_only=True)
    open_stub: int = field(kw_only=True)
    box_columns: bool = field(kw_only=True)
    # layout-0440: a pin on one side of a body wired to a column hung on its other side is a tag pair, not a wire round the body
    tag_across_body: bool = field(kw_only=True)
    bundle_direction: bool = False  # layout-0363: a bundle takes one direction, else one per chain
    trunk_forms: frozenset[str] = frozenset()  # layout-0421: bundles of these forms are trunks, never chain links
    # layout-0309: a keep-whole fan wider alone than the page may wrap at a column;
    # False keeps it one row
    # layout-0334 (from layout-0031 and layout-0035): whole wiring lanes kept free above row 0
    # and below the last row, so a turn and its label stay inside the content box;
    # `margin.h` is no longer read
    top_headroom_lanes: int = field(kw_only=True)
    bottom_headroom_lanes: int = field(kw_only=True)
    # how far a pin's end_bias pulls its chain end toward the head (below 0) or the foot (above 0),
    # against the one-step pull of the pin's side
    end_bias_weight: int = field(kw_only=True)
    # the pull of a box-drawn function's anchor on a chain end; it beats every other term
    anchor_weight: int = field(kw_only=True)
    boxpin_weight: int = field(kw_only=True)  # the pull of a box pin's side on a chain end
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
class RowPlan:
    """One row of a page plan: its columns and its blocks."""

    columns: tuple[str, ...]
    blocks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PagePlan:
    """One planned page of a unit: its rows and its groups."""

    page: int
    unit: str
    rows: tuple[RowPlan, ...]
    groups: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RefEnd:
    """One end of a reference: its page, column, pin, row and stand class.

    `also` are the other pins whose conductors this one end stands for: a bundle's one stub (BUNDLE, R1319).
    `far` are the far pins of the undrawn conductors a stub end stands for, in `stub_far_order` order: one box, a line each (R1581).
    """

    page: int
    column: str | None
    pin: PinRef | None
    row: int | None = None
    stand: StandClass = StandClass.PIN
    also: tuple[PinRef, ...] = ()
    far: tuple[PinRef, ...] = ()


@dataclass(frozen=True, slots=True)
class Ref:
    """A cut net drawn as references at its ends.

    `cut` is the boundary the cut planned it at, -1 for a reference no cut planned (R550).
    """

    net: str
    kind: RefKind
    ends: tuple[RefEnd, ...]
    cut: int = -1


@dataclass(frozen=True, slots=True)
class Finding:
    """A finding the placer raised: its code, its text, and optionally its page and subject."""

    code: FindingCode
    text: str
    page: int | None = None
    subject: str | None = None


@dataclass(frozen=True, slots=True)
class PageSpec:
    """The page plan for all units, the reference plan, the findings, the drawn pairs."""

    pages: tuple[PagePlan, ...]
    reference_plan: tuple[Ref, ...]
    findings: tuple[Finding, ...] = ()
    drawn: frozenset[tuple[PinRef, PinRef]] = field(kw_only=True)
    stubbed: frozenset[PinRef] = field(kw_only=True, default=frozenset())
    leads: frozenset[PinRef] = field(kw_only=True, default=frozenset())
    unjoined: tuple[tuple[str, tuple[PinRef, PinRef]], ...] = field(
        kw_only=True, default=()
    )  # (net, (near, far)): pieces the loop must join; `widen._stand` stands each through the route fallback, no reserve and no re-cut (R1713)
