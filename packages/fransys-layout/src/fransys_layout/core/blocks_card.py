"""A card's edges (E4) and spill, measured by the row's own packing (layout-0279).

Each pin's own edge is the side it is drawn on; while the whole card fits one page width nothing
spills, else, per edge, the longest prefix of its columns that still fits. Every width is
`row_width` of `one_row`, the comparison stage 4 makes, so a kept card always fits a row.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple

from .flow_values import Block
from .geometry import pin_of
from .keys import natural_key
from .pack_row import row_width
from .rowspec import one_row
from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .flow_values import Column, FlowGraph
    from .sym_values import Sym
    from .values import BoxSpec, Options, PlacementProblem

PinEdges = tuple[tuple[str, str], ...]


class CardEdges(NamedTuple):
    """pin_edges maps every pin of the box to an edge; spilled are the columns left off the card."""

    pin_edges: PinEdges
    spilled: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _Trial:
    """The throwaway card that is measured: the box with some columns and a trial edge map."""

    box: Sym
    flow: FlowGraph
    problem: PlacementProblem
    options: Options
    pin_edges: PinEdges = ()

    def width(self, cols: Sequence[str]) -> int:
        """row_width of the card holding `cols` (in pin order) on the trial edges."""
        block = Block(
            "trial",
            "card",
            self.box.unit,
            tuple(cols),
            self.box.id,
            None,
            None,
            0,
            0,
            short=False,
            keep_whole=True,
            forced_break_before=False,
            seat="none",
            pin_edges=self.pin_edges,
        )
        return row_width(one_row(cols, (block,), self.flow, self.problem, self.options))


def box_pin(column: Column) -> str | None:
    """The id of the box pin the column's head or foot meets, the first found."""
    for end in (*column.heads, *column.feet):
        if end.kind == "boxpin" and end.pin is not None:
            return end.pin.pin
    return None


def pin_order(cols: Sequence[str], columns: Mapping[str, Column], spec: BoxSpec) -> list[str]:
    """The columns in the box's marking order of their pins; a pin off the list sorts last."""
    rank = {p: i for i, p in enumerate(spec.order)}
    return sorted(cols, key=lambda c: (rank.get(box_pin(columns[c]) or "", len(rank)), natural_key(c)))


def card_edges(
    box: str,
    attached: Sequence[str],
    flow: FlowGraph,
    problem: PlacementProblem,
    options: Options,
) -> CardEdges:
    """Pin edges and spilled columns of one box whose attached columns are given."""
    sym = next(s for s in problem.symbols if s.id == box)
    spec = sym.box
    if spec is None:
        return CardEdges((), ())
    columns = {c.id: c for c in flow.columns}
    cols = pin_order(attached, columns, spec)
    page = problem.area.w - 2 * options.margin.w
    natural = tuple((p, pin_of(sym, p).side) for p in spec.order)
    trial = _Trial(sym, flow, problem, options, natural)
    if trial.width(cols) <= page:
        return CardEdges(natural, ())
    return _spill(trial, natural, cols, {c: box_pin(columns[c]) or "" for c in cols}, page)


def _spill(trial: _Trial, edges: PinEdges, cols: Sequence[str], col_pin: Mapping[str, str], page: int) -> CardEdges:
    """Each pin keeps the edge it is drawn on; per edge the longest fitting prefix of its columns.

    N is fitted first with S empty, S then with N's kept columns. Behind a cut edge, which spans the page,
    a column of the other edge sharing a net with its kept columns has no path: it stands on a later page (CROSS-HALF-TAGS).
    """
    edge_of = dict(edges)
    north, south = ([c for c in cols if edge_of.get(col_pin[c], "S") == e] for e in ("N", "S"))
    kept_n = _prefix(trial, north, page)
    kept_s = _prefix(trial, south, page, kept_n)
    if len(kept_n) < len(north):
        kept_s = _unshared(trial, kept_s, kept_n)
    elif len(kept_s) < len(south):
        kept_n = _unshared(trial, kept_n, kept_s)
    return CardEdges(edges, tuple(c for c in cols if c not in (*kept_n, *kept_s)))


def _prefix(trial: _Trial, mine: Sequence[str], page: int, beside: Sequence[str] = ()) -> list[str]:
    """The longest prefix of `mine` that fits the page with the columns `beside` already on the card."""
    fit = 0
    while fit < len(mine) and trial.width((*beside, *mine[: fit + 1])) <= page:
        fit += 1
    return list(mine[:fit])


def _unshared(trial: _Trial, mine: Sequence[str], other: Sequence[str]) -> list[str]:
    """The columns of `mine` holding no net that a column of `other` also holds."""
    syms = {c.id: {x.sym for ln in c.lanes for x in ln.cells} for c in trial.flow.columns}
    nets_of = {c: {n.id for n in trial.problem.nets if any(p.sym in syms[c] for p in n.pins)} for c in (*mine, *other)}
    held = set().union(*(nets_of[c] for c in other))
    return [c for c in mine if not nets_of[c] & held]


def overfull(box: str, spilled: Sequence[str], total: int) -> Finding:
    """The CARD_OVERFULL finding of one box."""
    text = f"{box}: {len(spilled)} of {total} attached columns do not fit the card and stand on later pages, each joined by a tag pair"
    return Finding("CARD_OVERFULL", text, None, box)
