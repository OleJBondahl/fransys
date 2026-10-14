"""layout-0214: the copies a crossing end draws at.

Its stub stands where `stages.black_box.stub_places` seats it (layout-0217): a nested unit's
function at its black boxes, any other at its home. A copy in a set its far end stands in stays too.
"""

from typing import TYPE_CHECKING

from fransys_layout.stages.black_box import black_box_tops, is_black_box, stub_places
from fransys_layout.stages.types import Home

from .read.units import black_box_reads, unit_nesting

if TYPE_CHECKING:
    from collections.abc import Set as AbstractSet

    from fransys_layout.stages.types import Column, Connection, Handle
    from fransys_model.kernel import Model

    from .read import StageInputs


def stub_seats(
    model: Model,
    inputs: StageInputs,
    columns: tuple[Column, ...],
    stubbed: AbstractSet[Handle],
) -> frozenset[tuple[Handle, int]]:
    """Each `(function, column index)` of `stubbed` where its stub stands."""
    reads = black_box_reads(model, unit_nesting(model, {s.unit for s in inputs.functions}).nested)
    tops = black_box_tops(inputs.functions, reads)
    unit_of = {s.function: s.unit for s in inputs.functions}
    boxes: dict[Handle, set[int]] = {}
    homes: dict[Handle, set[int]] = {}
    for i, column in enumerate(columns):
        for cell in column.cells:
            f = cell.function
            if f not in stubbed:
                continue
            if is_black_box(unit_of[f], column.unit, tops.get(f), reads.nested):
                boxes.setdefault(f, set()).add(i)
            elif cell.home is not Home.ELSEWHERE:
                homes.setdefault(f, set()).add(i)
    return frozenset(
        (f, i) for f in stubbed for i in stub_places(boxes.get(f, ()), homes.get(f, ()))
    )


def far_set_seats(
    columns: tuple[Column, ...], crossing: tuple[Connection, ...], stubbed: AbstractSet[Handle]
) -> frozenset[tuple[Handle, int]]:
    """Each `(function, column index)` of `stubbed` in a set a crossing far end stands in."""
    stands: dict[Handle, set[tuple[Handle | None, Handle | None]]] = {}
    for column in columns:
        for cell in column.cells:
            stands.setdefault(cell.function, set()).add(column.drawing_set_key)
    sets: dict[Handle, set[tuple[Handle | None, Handle | None]]] = {}
    for c in crossing:
        for near, far in ((c.a, c.b), (c.b, c.a)):
            sets.setdefault(near.function, set()).update(stands.get(far.function, ()))
    return frozenset(
        (cell.function, i)
        for i, column in enumerate(columns)
        for cell in column.cells
        if cell.function in stubbed and column.drawing_set_key in sets.get(cell.function, ())
    )
