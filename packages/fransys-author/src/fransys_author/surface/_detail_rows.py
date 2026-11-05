"""A row-read `wire=`: one row's wiring, and the maker of a wire with no row yet."""

from functools import partial
from typing import TYPE_CHECKING

from fransys_author.errors import AuthorError
from fransys_author.surface._rows import table

if TYPE_CHECKING:
    from collections.abc import Callable

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
