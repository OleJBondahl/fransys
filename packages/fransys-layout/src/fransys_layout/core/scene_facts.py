"""The facts `outputs.scene` reads from the problem and the flow, as plain lookups.

A `CoreLayout` holds geometry only. The scorer also reads each pin's net, node, end bias and side,
whether a box pin is movable, which boxes head a hung column or a fan and a row-group tag.
Each is read once here and never asked of a symbol kind.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .fan_head import fan_head

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .outputs import CoreLayout
    from .sym_values import Sym
    from .values import Column, End, FlowGraph, Orientation, PlacementProblem, Side


@dataclass(frozen=True, slots=True)
class PinFact:
    net: str | None
    node: int
    biased: bool
    sides: Mapping[Orientation, Side]
    box: bool


@dataclass(frozen=True, slots=True)
class SceneFacts:
    pins: dict[tuple[str, str], PinFact]
    attached: frozenset[str]
    heads: frozenset[tuple[str, str]]
    strips: dict[str, str]


def _pin_facts(sym: Sym, nets: frozendict[tuple[str, str], str]) -> dict[tuple[str, str], PinFact]:
    movable = frozenset(sym.box.order) if sym.box is not None else frozenset()
    return {
        (sym.id, p.id): PinFact(
            nets.get((sym.id, p.id)),
            p.node,
            p.end_bias != 0,
            frozendict({o: v.pins[i].side for o, v in sym.views.items()}),
            p.id in movable,
        )
        for i, p in enumerate(sym.pins)
    }


def _lanes(col: Column, ends: tuple[End, ...]) -> set[int]:
    """The lane indices the boxpin ends name; an end with no lane names every lane."""
    named = [e.lane for e in ends if e.kind == "boxpin"]
    return {i for n in named for i in (range(len(col.lanes)) if n is None else (n,))}


def _attached(flow: FlowGraph) -> frozenset[str]:
    """A column hung on a box pin: its lanes' first cells at a boxpin head, last cells at a foot."""
    found: set[str] = set()
    for col in flow.columns:
        found |= {col.lanes[i].cells[0].sym for i in _lanes(col, col.heads)}
        found |= {col.lanes[i].cells[-1].sym for i in _lanes(col, col.feet)}
    return frozenset(found)


def scene_facts(problem: PlacementProblem, flow: FlowGraph) -> SceneFacts:
    nets = frozendict({(r.sym, r.pin): n.id for n in problem.nets for r in n.pins})
    pins: dict[tuple[str, str], PinFact] = {}
    for sym in problem.symbols:
        pins |= _pin_facts(sym, nets)
    return SceneFacts(
        pins,
        _attached(flow),
        frozenset((h.pin.sym, h.pin.pin) for f in flow.fans if (h := fan_head(f)) is not None),
        {s.id: s.row_group for s in problem.symbols if s.row_group is not None},
    )


def page_fill(layout: CoreLayout) -> tuple[float, ...]:
    """Per page: the rows' spans (height times width) over the whole area, as rows are (h, w).

    The margin is not in a layout, so the area is not reduced by it.
    """
    area = layout.area.w * layout.area.h
    return tuple(sum(h * w for h, w in page.rows) / area for page in layout.placement.pages)
