"""S20 M9 (the owner's "C2"): room for a vertical box between two ports stacked along a stub.

Where the next symbol's port stands straight out along an N or S port's direction and one of
the two carries a reference or stub text, place spaces the two cells as far apart as the texts
at them reach out (`stand.reach_at`): for a reference the band's length (M4: a box's length and
one grid, `place._reference_band`), so the box stands between them; a text at each of the two
takes its own reach, as both boxes stand between them. Room's one primitive does it
(`grow_keepout`): the upper cell's keep-out grows downward until the two ports are that far
apart at the gap `gaps_below` will give the rows, so every later step (the spacing, the joins,
the bands) reads a bigger cell and no gap changes.

layout-0117 (`clear_symbols`): a pin row whose power symbol would reach into the box it faces
grows every cell of that item by one whole-grid delta, so the row moves away whole.
"""

from itertools import pairwise
from typing import TYPE_CHECKING, Any, Protocol

from fransys_layout.geometry import Box, Facing, meets, snap_up

from .room import grow_keepout
from .texts.power import own_places
from .texts.stand import reach_at

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from fransys_layout.geometry import Point, PortGeometry, SymbolGeometry
    from fransys_model.kernel import Id

    from .texts.stand import PageTexts
    from .types import DrawnFunction, Profile


class _Cell(Protocol):
    """A cell as the rule reads and grows it."""

    function: Id[Any]
    geometry: SymbolGeometry
    origin: Point
    boxy: bool
    host: Id[Any] | None


def make_room(
    page: Sequence[list[list[Any]]],
    drawn_of: Mapping[Id[Any], DrawnFunction],
    texts: PageTexts | None,
    *,
    gaps_of: Callable[[list[list[Any]]], list[int]],
    profile: Profile,
) -> None:
    """Grow each upper keep-out so two stacked ports leave room for their texts (M9, M11)."""
    if texts is None:
        return
    for rows in page:
        below = gaps_of(rows)
        for index, (upper, lower) in enumerate(pairwise(rows)):
            for cell in upper:
                shortfall = max(
                    (
                        reach_at(cell.geometry, drawn_of[cell.function], texts, a, profile)
                        + reach_at(other.geometry, drawn_of[other.function], texts, b, profile)
                        - _distance(cell, other, a, b, below[index])
                        for other in lower
                        for a, b in _stacked_ports(cell, other)
                    ),
                    default=0,
                )
                if shortfall > 0:
                    k = cell.geometry.keepout
                    reach = Box(x=k.x, y=k.y + k.height + shortfall, width=k.width, height=0)
                    cell.geometry = grow_keepout(cell.geometry, [reach])
    clear_symbols(page, drawn_of, texts, gaps_of=gaps_of)


def _stacked_ports(upper: _Cell, lower: _Cell) -> list[tuple[PortGeometry, PortGeometry]]:
    """The pairs of an S port of `upper` and an N port of `lower` that stand on one x."""
    return [
        (a, b)
        for a in upper.geometry.ports
        if a.facing is Facing.S
        for b in lower.geometry.ports
        if b.facing is Facing.N and upper.origin.x + a.at.x == lower.origin.x + b.at.x
    ]


def _distance(upper: _Cell, lower: _Cell, a: PortGeometry, b: PortGeometry, gap: int) -> int:
    """The y distance of ports `a` and `b` once `gap` stands between the two keep-outs."""
    ku, kl = upper.geometry.keepout, lower.geometry.keepout
    return (ku.y + ku.height - a.at.y) + gap + (b.at.y - kl.y)


def clear_symbols(
    page: Sequence[list[list[Any]]],
    drawn_of: Mapping[Id[Any], DrawnFunction],
    texts: PageTexts,
    *,
    gaps_of: Callable[[list[list[Any]]], list[int]],
) -> None:
    """layout-0117: a row whose power symbol reaches into the box it faces moves away, whole.

    Each item's cells of the row move by one grid delta, so its pins keep one height.
    """
    for rows in page:
        below = gaps_of(rows)
        for index, pair in enumerate(pairwise(rows)):
            _move(pair, drawn_of, texts, below[index], Facing.S)
            _move(pair, drawn_of, texts, below[index], Facing.N)


def _deltas(
    pair: tuple[Sequence[_Cell], Sequence[_Cell]],
    drawn_of: Mapping[Id[Any], DrawnFunction],
    texts: PageTexts,
    gap: int,
    facing: Facing,
) -> dict[Id[Any], int]:
    """Per item of the moving row, the fewest grids that clear its symbols facing the other."""
    row, other = pair if facing is Facing.S else pair[::-1]
    found: dict[Id[Any], int] = {}
    for cell in row:
        item = drawn_of[cell.function].item
        decisions = texts.owned.get(cell.function, ())
        for one in own_places(decisions, drawn_of[cell.function], texts, cell.geometry):
            faced = _faced(cell, one.body, other) if one.facing is facing else []
            if not faced:
                continue
            if facing is Facing.S:
                need = _need_down(cell, one.body, row, gap, _height(row, item, drawn_of))
            else:
                need = _need_up(cell, one.body, other, faced, gap)
            found[item] = max(found.get(item, 0), need)
    return {item: need for item, need in found.items() if need > 0}


def _faced(cell: _Cell, body: Box, other: Sequence[_Cell]) -> list[_Cell]:
    """The cells of `other` whose keep-out shares x with `cell`'s `body`; an edge counts."""
    left = cell.origin.x + body.x
    span = (left, left + body.width)
    return [
        o
        for o in other
        if meets(span, (x := o.origin.x + o.geometry.keepout.x, x + o.geometry.keepout.width))
    ]


def _height(row: Sequence[_Cell], item: Id[Any], drawn_of: Mapping[Id[Any], DrawnFunction]) -> int:
    """The tallest keep-out of `item`'s cells in `row`: their bottom below the row's top."""
    return max(c.geometry.keepout.height for c in row if drawn_of[c.function].item == item)


def _need_down(cell: _Cell, body: Box, row: Sequence[_Cell], gap: int, own: int) -> int:
    """The grids an upper item grows down by so `body` stops short of the lower row, else 0."""
    bottom = body.y + body.height - cell.geometry.keepout.y
    if bottom < max(c.geometry.keepout.height for c in row) + gap:
        return 0
    return snap_up(bottom - gap - own + 1)


def _need_up(
    cell: _Cell, body: Box, upper: Sequence[_Cell], faced: Sequence[_Cell], gap: int
) -> int:
    """The grids a lower item drops by so `body` stays below every box it faces, else 0."""
    top = max(c.geometry.keepout.height for c in upper) + gap + body.y - cell.geometry.keepout.y
    box = max(c.geometry.keepout.height for c in faced)
    return 0 if top > box else snap_up(box - top + 1)


def _move(
    pair: tuple[Sequence[_Cell], Sequence[_Cell]],
    drawn_of: Mapping[Id[Any], DrawnFunction],
    texts: PageTexts,
    gap: int,
    facing: Facing,
) -> None:
    """Grow each cell of a moved item by its delta: the upper row down, the lower row up.

    A lower cell grown up keeps its top, so `at_top` drops its origin and its pins by the delta.
    """
    deltas = _deltas(pair, drawn_of, texts, gap, facing)
    for cell in pair[0] if facing is Facing.S else pair[1]:
        delta = deltas.get(drawn_of[cell.function].item, 0)
        if delta:
            k = cell.geometry.keepout
            y = k.y + k.height + delta if facing is Facing.S else k.y - delta
            cell.geometry = grow_keepout(cell.geometry, [Box(x=k.x, y=y, width=k.width, height=0)])
