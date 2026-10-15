"""The row graph: segments left to right, box pins spread to their columns, justify on.

One constraint graph per row. `solve_row` places a row on the page and `row_width` measures
it, so the stages that need a row's width ask here and never re-derive it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import pairwise
from typing import TYPE_CHECKING

from .constraints import Graph
from .geometry import column_extent
from .pack_sep import separation
from .values import Lane

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .pack import Attached, PlacedColumn
    from .values import Block, Options, Sym

Reach = tuple[str, int]


@dataclass(frozen=True, slots=True)
class RowSpec:
    """One row: its columns, blocks and placed columns, with what the x graph reads.

    attach maps an attached column to (box, pin, lane offset); reserves maps a (left, right)
    column pair to the tracks its gap must hold (stage 7).
    """

    cols: tuple[str, ...]
    blocks: tuple[Block, ...]
    pcs: dict[str, PlacedColumn]
    syms: dict[str, Sym]
    in_row: frozenset[str]
    options: Options
    attach: Attached
    reserves: dict[tuple[str, str], int] = field(default_factory=dict)


def segments(
    cols: tuple[str, ...], blocks: tuple[Block, ...]
) -> list[tuple[Block | None, list[str]]]:
    """A card is one segment; consecutive non-card blocks form one run of columns."""
    block_of = {c: b for b in blocks for c in b.columns}
    out: list[tuple[Block | None, list[str]]] = []
    for b in blocks:
        here = [c for c in cols if block_of.get(c) is b]
        if b.kind == "card":
            out.append((b, here))
        elif here and out and out[-1][0] is None:
            out[-1][1].extend(here)
        elif here:
            out.append((None, here))
    return out


def _extent(spec: RowSpec, col: str) -> tuple[int, int]:
    pc = spec.pcs[col]
    lanes = tuple(Lane(cells, off) for cells, off in zip(pc.lanes, pc.offsets, strict=True))
    return column_extent(spec.syms, lanes, spec.in_row)


def _margin(spec: RowSpec, box: str) -> int:
    """Body beyond the end pins of a box: its spec margin, else 16 G."""
    box_spec = spec.syms[box].box
    return box_spec.margin if box_spec else 16


def _sep(spec: RowSpec, a: str, b: str) -> int:
    return separation(spec.pcs[a], spec.pcs[b], spec.syms, spec.in_row, spec.options)


def build_row_graph(spec: RowSpec, extra: int) -> tuple[Graph, list[Reach]]:
    """Segments left to right; extra widens every gap and pitch (justify); returns right reaches."""
    g = Graph()
    prev: Reach | None = None
    rights: list[Reach] = []
    for block, here in segments(spec.cols, spec.blocks):
        left, right = _segment(g, spec, block, here, extra)
        gap = (
            prev[1] + left[1] + spec.options.column_gap_min + extra
            if prev
            else spec.options.margin.w + left[1]
        )
        if prev:
            g.after(prev[0], left[0], gap)
        else:
            g.at_least(left[0], gap)
        prev = right
        rights.append(right)
    _reserve(g, spec, extra)
    return g, rights


def _segment(
    g: Graph, spec: RowSpec, block: Block | None, here: Sequence[str], extra: int
) -> tuple[Reach, Reach]:
    """Constrain one segment; its left and right node with the reach past each."""
    if block is not None:
        _card(g, spec, block, here, extra)
        return (f"slot:{block.id}:L", 0), (f"slot:{block.id}:R", 0)
    _run(g, spec, here, extra)
    return (f"col:{here[0]}", -_extent(spec, here[0])[0]), (
        f"col:{here[-1]}",
        _extent(spec, here[-1])[1],
    )


def _reserve(g: Graph, spec: RowSpec, extra: int) -> None:
    """A reserved pair keeps its separation, the justify extra and a grid per extra track.

    A pair not both in this row is skipped (a block moved to another row).
    """
    here = set(spec.cols)
    for (a, b), tracks in sorted(spec.reserves.items()):
        if tracks > 1 and a in here and b in here:
            g.after(
                f"col:{a}",
                f"col:{b}",
                _sep(spec, a, b) + extra + spec.options.wiring_grid * (tracks - 1),
            )


def _run(g: Graph, spec: RowSpec, cols: Sequence[str], extra: int) -> None:
    for a, b in pairwise(cols):
        g.after(f"col:{a}", f"col:{b}", _sep(spec, a, b) + extra)


def _card(g: Graph, spec: RowSpec, block: Block, cols: Sequence[str], extra: int) -> None:
    """Pins in marking order per edge at least the pitch apart; each attached column on its pin."""
    box = block.anchor or ""
    edge_of = dict(block.pin_edges)
    for edge in ("N", "S"):
        _pin_chain(g, spec, box, [p for p, e in block.pin_edges if e == edge], extra)
        _run(
            g,
            spec,
            [c for c in cols if c in spec.attach and edge_of.get(spec.attach[c][1], "") == edge],
            extra,
        )
    _card_columns(g, spec, block.id, box, cols)
    g.after(f"slot:{block.id}:L", f"box:{box}:L", 0)
    g.after(f"box:{box}:R", f"slot:{block.id}:R", 0)
    g.after(
        f"box:{box}:L", f"box:{box}:R", 2 * _margin(spec, box) if cols else spec.syms[box].body.w
    )


def _card_columns(g: Graph, spec: RowSpec, block: str, box: str, cols: Sequence[str]) -> None:
    for c in cols:
        if c in spec.attach:
            g.equal(f"col:{c}", f"pin:{box}:{spec.attach[c][1]}", spec.attach[c][2])
        lo, hi = _extent(spec, c)
        g.after(f"slot:{block}:L", f"col:{c}", -lo)
        g.after(f"col:{c}", f"slot:{block}:R", hi)


def _pin_chain(g: Graph, spec: RowSpec, box: str, pins: Sequence[str], extra: int) -> None:
    margin = _margin(spec, box)
    for a, b in pairwise(pins):
        g.after(f"pin:{box}:{a}", f"pin:{box}:{b}", spec.options.box_pin_pitch_min + extra)
    if pins:
        g.after(f"box:{box}:L", f"pin:{box}:{pins[0]}", margin)
        g.after(f"pin:{box}:{pins[-1]}", f"box:{box}:R", margin)


def _solve(spec: RowSpec, extra: int) -> tuple[dict[str, int], int] | None:
    """The solved x per node and the row's right edge; None when the constraints contradict."""
    g, rights = build_row_graph(spec, extra)
    x = g.solve()
    if x is None:
        return None
    return x, max(x[node] + reach for node, reach in rights)


def row_width(spec: RowSpec) -> int:
    """The width of the row's packed graph without the left margin: what stages 2, 4 and 7 ask."""
    base = _solve(spec, 0)
    if base is None:
        msg = "contradictory x constraints"
        raise ValueError(msg)
    return base[1] - spec.options.margin.w


def _widest_extra(spec: RowSpec, page_w: int) -> int:
    """The largest extra gap, in whole grids, whose row still ends inside the page margin."""
    grid = spec.options.wiring_grid
    lo, hi = 0, page_w // grid
    while lo < hi:
        mid = (lo + hi + 1) // 2
        trial = _solve(spec, mid * grid)
        if trial is not None and trial[1] <= page_w - spec.options.margin.w:
            lo = mid
        else:
            hi = mid - 1
    return lo * grid


def solve_row(spec: RowSpec, page_w: int) -> tuple[dict[str, int], int]:
    """Left-packed x, then the widest uniform extra gap that still fits the page (justify).

    Returns the positions and the overflow: G past the page's right margin, 0 when the row fits.
    A row wider than the page comes back left-packed; stage 5 turns an overflow into a finding.
    """
    base = _solve(spec, 0)
    if base is None:
        msg = "contradictory x constraints"
        raise ValueError(msg)
    overflow = max(0, base[1] - (page_w - spec.options.margin.w))
    if not spec.options.justify:
        return base[0], overflow
    best = _solve(spec, _widest_extra(spec, page_w))
    return (best[0] if best else base[0]), overflow
