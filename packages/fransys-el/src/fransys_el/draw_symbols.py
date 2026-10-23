"""The symbols of a core layout as `Drawing` values.

Each builder returns `(page id, symbol)` pairs in the order the layout places them. The ids are
the ones the retired symbol records had (`drawn_ids`), so the order of a page is unchanged.
"""

from typing import TYPE_CHECKING

from electrical_symbols import drawn_slots
from fransys_layout.core import junctions
from fransys_layout.drawing import DrawnSymbol

from .drawn_identity import outline_of
from .drawn_ids import symbol_id
from .placement_kit import refuse
from .write_drawn import _leads, _offsets, _sides

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from fransys_layout.core import CoreLayout, PlacementProblem
    from fransys_model.kernel import Id
    from fransys_model.layout import Page

__all__ = ["junction_dots", "placed_symbols"]

_KEY = ("layout", "core")


def placed_symbols(
    layout: CoreLayout,
    problem: PlacementProblem,
    pages: Mapping[int, Page],
    shown: Mapping[str, tuple[str, tuple[tuple[str, ...], ...], int, tuple[str, ...]]],
    marks: Mapping[str, Mapping[str, str]],
) -> Iterator[tuple[Id[Page], DrawnSymbol]]:
    """One symbol per placed symbol: its key, texts, poles (`shown`), box, pins and slots."""
    syms = {s.id: s for s in problem.symbols}
    wired = dict(layout.wired)
    for page in layout.placement.pages:
        for p in page.placed:
            if p.sym not in shown:
                refuse(
                    f"symbol {p.sym}",
                    "the kit has no pick for its function: pass the build's kit",
                    p.sym,
                )
            key, texts, poles, ports = shown[p.sym]
            slots = {**drawn_slots(key, texts), **marks.get(p.sym, {})}
            yield (
                pages[p.page].id,
                DrawnSymbol(
                    id=symbol_id(*_KEY, "drawn_symbol", p.sym),
                    key=key,
                    x=p.x,
                    y=p.y,
                    orient=p.orient,
                    slots=tuple(slots.items()),
                    offsets=tuple(_offsets(p, syms[p.sym]).items()),
                    sides=tuple(_sides(syms[p.sym]).items()),
                    leads=_leads(syms[p.sym], wired),
                    poles=poles,
                    texts=texts,
                    outline=p.body,
                    ports=ports,
                ),
            )


def junction_dots(
    layout: CoreLayout, pages: Mapping[int, Page]
) -> Iterator[tuple[Id[Page], DrawnSymbol]]:
    """One `junction-dot` per junction point the core reports (layout-0335).

    Its id names no document number, so a unit's page draws in one order alone and in a parent.
    """
    for j in junctions(layout):
        key = (*_KEY, "drawn_junction", j.net, str(j.page), str(j.x), str(j.y))
        yield (
            pages[j.page].id,
            DrawnSymbol(
                id=symbol_id(*key),
                key="junction-dot",
                x=j.x,
                y=j.y,
                orient="R0",
                outline=outline_of("junction-dot", "R0", j.x, j.y),
            ),
        )
