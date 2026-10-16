"""Values of the placer core, input side: the problem, the options, stage 1 to 4 outputs.

Frozen plain data; outputs.py holds the placement, route, text and layout values, and
jsonform.py gives every value here a JSON form. Lengths are in G; x grows right, y down.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

XY = tuple[int, int]

Side = Literal["N", "E", "S", "W"]
Power = Literal["SUPPLY", "GROUND", "PE", "NONE"]
Orientation = Literal["R0", "R90", "R180", "R270", "MR0", "MR90", "MR180", "MR270"]
EndKind = Literal["stand", "boxpin", "boundary", "fan", "crosslink", "join", "open"]
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
    "NO_BLOCK",
    "BLOCK_NOT_PLACED",
    "CHAIN_NOT_DRAWN",
    "CHAIN_REFUSED",
    "ORDER_HINT_UNMET",
    "KEEP_TOGETHER_UNMET",
    "HEAD_OFF_LEGS",
    "ALIGN_DROPPED",
    "ROUTE_FAILED",
    "PAGE_OVERFLOW",
    "TEXT_OVERLAP",
    "FILL_UNDER_MIN",
    "WIDER_THAN_PAGE",
    "LANE_TURNED",
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


@dataclass(frozen=True, slots=True)
class PinRef:
    """A pin of one symbol, named by the symbol id and the pin id."""

    sym: str
    pin: str


@dataclass(frozen=True, slots=True)
class Pin:
    """Fact 1: side is the way the wire leaves (N E S W); node indexes Sym.nodes."""

    id: str
    side: Side
    dx: int
    dy: int
    node: int
    stand: Power | None = None


@dataclass(frozen=True, slots=True)
class BoxSpec:
    """Fact 16: movable pins in printed-marking order; margin is body beyond the end pins."""

    order: tuple[str, ...]
    natural_edge: str
    min_pitch: int
    margin: int


@dataclass(frozen=True, slots=True)
class Sym:
    """T1 to T3: row_group members at one column end in one row share y and use row_footprint.

    label is the size of the designation symbol and table the size of the contact-table symbol
    (layout-0274); the builder measures both and folds them into footprint. Text is the builder's.
    """

    id: str
    group: str | None
    unit: str
    label: Size
    body: Box
    keepout: Box
    footprint: Box
    pins: tuple[Pin, ...]
    nodes: tuple[tuple[str, ...], ...]
    orientations: frozenset[Orientation]
    box: BoxSpec | None = None
    row_footprint: Box | None = None
    row_group: str | None = None
    band: int | None = None
    item: str | None = None
    child_of: str | None = None
    table: Size | None = None
    boundary_of: str | None = None


@dataclass(frozen=True, slots=True)
class Rail:
    """Fact 4: a smaller rank draws higher; power SUPPLY, GROUND, PE draw stands, NONE wires."""

    rank: int
    power: Power


@dataclass(frozen=True, slots=True)
class Bundle:
    """Fact 10: nets with one id travel as one trunk; pole is the lane index at the source."""

    id: str
    pole: int


@dataclass(frozen=True, slots=True)
class Net:
    """A net: its id, the pins it joins, and its rail, bundle, unit-crossing and label facts."""

    id: str
    pins: tuple[PinRef, ...]
    rail: Rail | None = None
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
    """Problem facts: groups kept whole, units, mated pin pairs and row tags."""

    keep_whole: tuple[frozenset[str], ...] = ()
    units: tuple[Unit, ...] = ()
    mates: tuple[tuple[PinRef, PinRef], ...] = ()
    row_tags: tuple[tuple[str, Size], ...] = ()


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
class PlacementProblem:
    """The placer's input: the area, the symbols, the nets, the facts and the hints."""

    area: Size
    symbols: tuple[Sym, ...]
    nets: tuple[Net, ...]
    facts: Facts = field(default_factory=Facts)
    hints: Hints = field(default_factory=Hints)


@dataclass(frozen=True, slots=True)
class Options:
    """Design 2.2 with E4: pins spread, justify on; flow is top to bottom (spec ruling)."""

    margin: Size = field(default_factory=lambda: Size(16, 16))
    wiring_grid: int = 8
    wire_min: int = 8
    column_gap_min: int = 8
    row_gap: int = 24
    box_pin_pitch_min: int = 16
    box_pins: str = "spread"
    short_height: float = 0.4
    min_fill: float = 0.25
    exact_order_limit: int = 12
    exact_order_nodes: int = 50_000
    tag_stagger: bool = True
    justify: bool = True
    band_align: bool = True
    w_tag: float = 1.0
    w_arrow: float = 0.5
    w_ref: float = 3.0
    w_p: float = 2.0
    w_f: float = 1.0
    w_row: float = 0.05
    w_violation: float = 1_000_000.0
    bend_penalty: int = (
        19  # round(score.WEIGHTS["b"] / WEIGHTS["d"]): the router trades as the scorer does
    )
    crossing_penalty: int = 64  # round(score.WEIGHTS["x"] / WEIGHTS["d"])
    reroute_rounds: int = 3
    corner_order: tuple[str, ...] = ("KL", "KR", "BL", "TL", "BR", "TR")
    slack: tuple[int, ...] = (0, 8, 16)
    # layout-0305: the reference-marker symbol's keepout box in grid units, relative to its origin;
    # symdef data that fransys_el passes in, so the core types no size
    marker: Box | None = None
    cells: tuple[int, int] = (8, 6)
    wire_label_sides: tuple[str, ...] = ("N", "S")
    open_stub: int = 0
    box_columns: bool = True
    # layout-0309: a keep-whole fan wider alone than the page may wrap at a column;
    # False keeps it one row
    wrap_wide_fans: bool = True


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
    """A lane's end: stand, boxpin, boundary, fan, crosslink, join or open.

    lane is the index into the column's lanes this end belongs to; None means every lane.
    """

    kind: EndKind
    net: str | None = None
    pin: PinRef | None = None
    stand: str | None = None
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
    """Where a trunk meets a lane: pin of cell `cell` in lane `lane`; column None is a box pin."""

    column: str | None
    lane: int
    cell: int
    pin: PinRef


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


@dataclass(frozen=True, slots=True)
class CrossLink:
    """A net that crosses between column ends, given by its attachments."""

    net: str
    ends: tuple[Attach, ...]


@dataclass(frozen=True, slots=True)
class Stand:
    """A supply stand on a pin: its power kind and its rank."""

    sym: str
    pin: str
    power: Power
    rank: int


@dataclass(frozen=True, slots=True)
class CycleSplit:
    """How many bundles, ladders and cross links were cut to break cycles in the flow."""

    bundles: int
    ladders: int
    cross_links: int


@dataclass(frozen=True, slots=True)
class FlowGraph:
    """The flow after stage 2: columns, fans, cross links, stands, cycle split, drawn symbols."""

    columns: tuple[Column, ...]
    fans: tuple[Fan, ...]
    cross_links: tuple[CrossLink, ...]
    stands: tuple[Stand, ...]
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
