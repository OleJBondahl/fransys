"""Open cores as the cable drawing draws them: where each stands, for `cable_drawing` (CC6).

A landed open core stands in the cell of the pin it lands on. An unlanded one stands in the
cell of its neighbour core. A core landed in the bottom row also holds a place in the top
row (`mate`), so its stub has a column of its own.
"""

from fransys_model.kernel import value
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Port
lazy from fransys_model.vocab.facets.cable import OpenCoreFacet

from .open_core_ends import _open_by_cable
lazy from .rows import HarnessCable
lazy from .rows_cores import OpenCoreRow


@value
class DrawnOpen:
    """One open core of a block: its facet, its row, the pin whose cell holds its place.

    `place` is its cable's place in the block's print order. `landed` is false for a core that
    lands nowhere: both its ends are stubs.
    """

    core: Id[OpenCoreFacet]
    cable: Id[Item]
    index: int
    anchor: Id[Port]
    landed: bool
    place: int
    row: OpenCoreRow
    mate: tuple[Id[Port], ...]


def _mate(cable: HarnessCable, row: OpenCoreRow) -> tuple[Id[Port], ...]:
    """The ends of the cable's core before this one (the first core if none): its neighbour.

    A core's stub stands in its neighbour's cell, so the rows keep core index order (CC10).
    """
    before = [core for core in cable.cores if core.index < row.index] or cable.cores[:1]
    return (before[-1].end_a, before[-1].end_b) if before else ()


def _anchor(row: OpenCoreRow, mate: tuple[Id[Port], ...]) -> Id[Port] | None:
    """The port whose cell holds the core's place: its landing, else its neighbour's end."""
    return row.at if row.at is not None else (mate[0] if mate else None)


def drawn_open_cores(model: Model, cables: tuple[HarnessCable, ...]) -> tuple[DrawnOpen, ...]:
    """The open cores of `cables` in print order; a cable with no core holds none (no anchor)."""
    found = []
    for place, cable in enumerate(cables):
        facets = _open_by_cable(model).get(cable.cable, ())
        for facet, row in zip(facets, cable.open_cores, strict=True):
            mate = _mate(cable, row)
            anchor = _anchor(row, mate)
            if anchor is not None:
                found.append(
                    DrawnOpen(
                        core=facet.id,
                        cable=cable.cable,
                        index=row.index,
                        anchor=anchor,
                        landed=row.at is not None,
                        place=place,
                        row=row,
                        mate=mate,
                    )
                )
    return tuple(found)
