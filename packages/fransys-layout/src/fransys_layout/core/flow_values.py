"""Values of the placer core, flow side: columns, fans, blocks and the stage 4 result.

Frozen plain data over `values`; outputs.py holds the placement, route, text and layout values,
and jsonform.py gives every value here a JSON form. Lengths are in G.
"""

from dataclasses import dataclass, field
from itertools import pairwise
from typing import Literal
lazy from collections.abc import Iterator, Mapping

lazy from .values import Finding, Orientation, PageSpec, PinRef

EndKind = Literal["biased", "boxpin", "boundary", "fan", "crosslink", "join", "open"]

BlockKind = Literal["card", "fan", "column", "blackbox"]

Seat = Literal["none", "beside", "alone"]


@dataclass(frozen=True, slots=True)
class Cell:
    """One symbol in a lane; top_pin is on the head side and bottom_pin on the foot side."""

    sym: str
    orient: Orientation
    top_pin: str | None
    bottom_pin: str | None
    hold: int = 0  # G of extra gap above the cell


@dataclass(frozen=True, slots=True)
class Lane:
    """Cells from head to foot; offset is the lane's x against lane 0 of its column."""

    cells: tuple[Cell, ...]
    offset: int


@dataclass(frozen=True, slots=True)
class End:
    """A lane's end: biased, boxpin, boundary, fan, crosslink, join or open.

    lane is the index into the column's lanes a boxpin end belongs to.
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


def hop_wires(
    col: Column, net_of: Mapping[PinRef, str], net_pins: Mapping[str, tuple[PinRef, ...]]
) -> Iterator[tuple[int, Cell, Cell, str, PinRef | None, PinRef | None]]:
    """Each other net of a chain hop: (pair index, upper cell, lower cell, net, its pin on each); a pin is None when unplaced.

    The lane's own wire draws the anchor net. Placement counts these wires and route draws them.
    """
    cells = col.lanes[0].cells if col.is_chain else ()
    for i, ((a, b), nets) in enumerate(zip(pairwise(cells), col.hops, strict=False)):
        anchored = net_of.get(PinRef(a.sym, a.bottom_pin or ""))
        for net in (n for n in nets if n != anchored):
            pins = net_pins.get(net, ())
            yield i, a, b, net, next((r for r in pins if r.sym == a.sym), None), next((r for r in pins if r.sym == b.sym), None)


@dataclass(frozen=True, slots=True)
class Attach:
    """Where a trunk meets a lane: pin of cell `cell` in lane `lane`; column None is a box pin.

    `pole` is a lane index, a value the caller passes; `lane` is the column's own index.
    `net` is the net the attach joins, set once when the fan is drafted; always given.
    """

    column: str | None
    lane: int
    cell: int
    pin: PinRef
    pole: int = 0
    net: str = field(kw_only=True)


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
    head: Attach | None = None


@dataclass(frozen=True, slots=True)
class CrossLink:
    """A net that crosses between column ends, given by its attachments."""

    net: str
    ends: tuple[Attach, ...]
    tagged: bool = False  # layout-0440: drawn as a tag pair, never routed


@dataclass(frozen=True, slots=True)
class BiasedEnd:
    """A pin that prefers an end of its chain, with its rank among the biased ends."""

    sym: str
    pin: str
    rank: int


@dataclass(frozen=True, slots=True)
class FlowGraph:
    """The flow after stage 2: columns, fans, cross links, biased ends, drawn."""

    columns: tuple[Column, ...]
    fans: tuple[Fan, ...]
    cross_links: tuple[CrossLink, ...]
    biased: tuple[BiasedEnd, ...]
    drawn: tuple[str, ...]
    findings: tuple[Finding, ...] = ()
    joined: frozenset[frozenset[str]] = frozenset()  # symbol pairs of lane cells with no facing pin: a cross-link joins them (layout-0482)


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


def block_id(kind: str, name: str) -> str:
    """The id of a block of `kind` named by its anchor or first column: the one place that makes it, never read back."""
    return f"{kind}:{name}"


@dataclass(frozen=True, slots=True)
class BlockList:
    """The blocks of one unit, with the findings raised while building them."""

    unit: str
    blocks: tuple[Block, ...]
    findings: tuple[Finding, ...] = ()


@dataclass(frozen=True, slots=True)
class CutResult:
    """The spec, plus the flow and blocks after tall-column cuts; later stages read these."""

    spec: PageSpec
    flow: FlowGraph
    blocks: tuple[BlockList, ...]
    row_tags: frozenset[str] = frozenset()  # fan ids a row or page cut wraps: routing draws their wire, no trunk (layout-0529)
