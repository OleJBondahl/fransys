"""Stage 4, the unit's items and what a cut costs: trunks cut (arrows), two-pin nets (tags), P2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .cut_pack import left_pack

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .cut_pack import Pack
    from .values import Block, BlockList, Column, Fan, FlowGraph, Options, PlacementProblem, Seat

HEIGHT_WIRES = 3  # grids a column's estimated height holds beyond its cells
TWO_ENDS = 2  # a trunk with two attachments is a two-pin net


@dataclass(frozen=True, slots=True)
class Item:
    """One cut unit: a column with its block; a whole block (card, bundle) never splits.

    at, lead and tail come from cut_pack's one left-pack of the unit: items i..j in one row are
    seq[j].at - seq[i].at + seq[i].lead + seq[j].tail wide, margin left out.
    """

    block: str
    column: str
    height: int  # item_height of the column
    short: bool
    whole: bool
    forced_break_before: bool
    at: int
    lead: int
    tail: int
    seat: Seat

    @property
    def bare(self) -> bool:
        """A seated column-less card: its column is its box, in no RowPlan.columns."""
        return self.seat != "none"

    @property
    def own_row(self) -> bool:
        """True for a card that stands in a row of its own."""
        return self.seat == "alone"


@dataclass(frozen=True, slots=True)
class Boundary:
    """A cut after one position: trunks it crosses (arrows), cut nets (tags), strict pairs (P2)."""

    arrows: int
    tags: int
    pairs: int
    fans: tuple[str, ...]
    nets: tuple[str, ...]
    copies: int = 0


def item_height(column: Column, options: Options) -> int:
    """The one home of a column's row height: its cells and the wires round them."""
    return column.height + HEIGHT_WIRES * options.wiring_grid


def sequence(
    unit: BlockList, flow: FlowGraph, problem: PlacementProblem, options: Options, page_h: int
) -> tuple[Item, ...]:
    """The unit's columns in block order, each with its pack and its height."""
    columns = {c.id: c for c in flow.columns}
    packed = left_pack(unit, flow, problem, options)
    limit = options.short_height * page_h
    out: list[Item] = []
    for b in unit.blocks:
        if b.seat != "none" and not b.columns:
            out.append(_bare_item(b, packed))
        for i, col in enumerate(b.columns):
            height = item_height(columns[col], options)
            short = b.short if b.keep_whole else height < limit
            out.append(
                Item(
                    b.id,
                    col,
                    height,
                    short,
                    b.keep_whole,
                    b.forced_break_before and i == 0,
                    *packed[col],
                    seat="none",
                )
            )
    return tuple(out)


def _bare_item(b: Block, packed: Mapping[str, Pack]) -> Item:
    """A seated column-less card is one whole item named by its box (layout-0288)."""
    box = b.anchor or ""
    return Item(
        b.id,
        box,
        b.height_est,
        short=b.short,
        whole=True,
        forced_break_before=b.forced_break_before,
        **packed[box]._asdict(),
        seat=b.seat,
    )


def positions(seq: Sequence[Item], blocks: Mapping[str, Block]) -> dict[str, int]:
    """Position of each column, and of each box (its card block's first column)."""
    pos = {item.column: i for i, item in enumerate(seq)}
    for b in blocks.values():
        if b.anchor is not None and b.columns:
            pos[b.anchor] = pos[b.columns[0]]
    return pos


def is_pair(fan: Fan) -> bool:
    """A two-pin net: its cut is a tag, any other trunk's an arrow."""
    return len(fan.drivers) + len(fan.legs) == TWO_ENDS and len(fan.nets) == 1


def ref_name(fan: Fan) -> str:
    """The name a fan's references carry: its net for a two-pin net, else its own id."""
    return fan.nets[0] if is_pair(fan) else fan.id


def fan_columns(fan: Fan) -> list[str]:
    return [a.column or a.pin.sym for a in (*fan.drivers, *fan.legs)]


class _Tally:
    """Per boundary: counts and names of what a cut there crosses."""

    def __init__(self, size: int) -> None:
        self.counts = {k: [0] * size for k in ("arrows", "tags", "pairs", "copies")}
        self.fans: list[list[str]] = [[] for _ in range(size)]
        self.nets: list[list[str]] = [[] for _ in range(size)]

    def add(self, span: tuple[int, int] | None, name: str, *, pair: bool, copy: bool) -> None:
        for b in range(*(span or (0, 0))):
            self.counts["tags" if pair else "arrows"][b] += 1
            self.counts["pairs"][b] += int(pair)
            self.counts["copies"][b] += int(copy)
            (self.nets if pair else self.fans)[b].append(name)


def _span(names: Sequence[str], pos: Mapping[str, int]) -> tuple[int, int] | None:
    here = [pos[n] for n in names if n in pos]
    return (min(here), max(here)) if len(here) > 1 else None


def boundaries(
    seq: Sequence[Item],
    flow: FlowGraph,
    blocks: Mapping[str, Block],
    copyable: frozenset[str] = frozenset(),
) -> tuple[Boundary, ...]:
    """What a cut after each position crosses; a two-pin net is a tag, any other trunk an arrow."""
    pos = positions(seq, blocks)
    tally = _Tally(len(seq))
    for fan in flow.fans:
        name = ref_name(fan)
        tally.add(_span(fan_columns(fan), pos), name, pair=is_pair(fan), copy=fan.id in copyable)
    for link in flow.cross_links:
        ends = [a.column or a.pin.sym for a in link.ends]
        tally.add(_span(ends, pos), link.net, pair=True, copy=False)
    c = tally.counts
    return tuple(
        Boundary(
            c["arrows"][b],
            c["tags"][b],
            c["pairs"][b],
            tuple(tally.fans[b]),
            tuple(tally.nets[b]),
            c["copies"][b],
        )
        for b in range(len(seq) - 1)
    )


def cut_cost(b: Boundary, options: Options, *, page: bool) -> float:
    """Q cost of a cut; a page cut through a two-pin net is a P2 pair and costs a violation."""
    arrows = b.arrows - (b.copies if page else 0)
    q = options.w_ref * (options.w_arrow * arrows + options.w_tag * b.tags)
    return q + (options.w_violation * b.pairs if page else 0.0)
