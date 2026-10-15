"""A row-read `wire=`: one row's wiring, and each detail wire's row from its ports' givens."""

from functools import partial
from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_author.errors import AuthorError
from fransys_author.surface._potential import Given
from fransys_author.surface._rows import table

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_author.handles import Port
    from fransys_author.surface._rows import WiringRow
    from fransys_author.surface._wire import RowWire
    from fransys_author.wiring import Wiring

    from .design import Design

_NO_SIZE = "give a size: wire=0.75, or a row with a size"


def row_wiring(design: Design, row: WiringRow, wire: RowWire) -> Wiring:
    """The wiring of one row: its colour from the table, its size from `wire=` else the table."""
    colour, gauge = table(wire.rows, design._wiring)[row]
    gauge = gauge if wire.size is None else wire.size
    if gauge is None:
        raise AuthorError(_NO_SIZE)
    return design._engine.wiring(colour=colour, gauge=gauge)


def hint_maker(design: Design, wire: RowWire) -> Callable[..., None]:
    """The wire maker for a wire with no row yet: the table in force and the size, no facet."""
    rows = {row.value: spec for row, spec in table(wire.rows, design._wiring).items()}
    return partial(design._engine._wire_hints(), rows=rows, size=wire.size)


def wire_pairs(
    design: Design, ports: list[Port], wire: RowWire, *, n: int | None, label: str | None
) -> None:
    """One wire per neighbouring pair; each takes the row a given end of its pair carries (S4)."""
    for a, b in pairwise(ports):
        given = design._given.get(a.id) or design._given.get(b.id)
        if given is None:
            hint_maker(design, wire)(a, b, n=n, label=label)
            continue
        row_wiring(design, given.row, wire).run(a, b, n=n, label=label)
        design._given[a.id] = design._given[b.id] = Given(given.row, power=False)
