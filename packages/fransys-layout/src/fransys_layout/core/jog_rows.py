"""The bend row of each level of a jog nest, kept off the rows the page already holds (R428)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .clearance import clear
from .values import Box

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .clearance import Keep
    from .values import XY

type Taken = tuple[int, int, int]
"""A horizontal run already laid: its y and its x range."""

type Span = tuple[int, int, frozenset[str]]
"""A bend's x range and the symbols its wire belongs to."""


def taken_rows(runs: Sequence[tuple[XY, XY]]) -> tuple[Taken, ...]:
    """The horizontal runs among these segments, as (y, x0, x1)."""
    return tuple((a[1], min(a[0], b[0]), max(a[0], b[0])) for a, b in runs if a[1] == b[1] and a != b)


def _free(y: int, span: Span, taken: Sequence[Taken], keeps: Sequence[Keep], grid: int) -> bool:
    """No taken run on the grid row over the span, and no hard keep under it that the wire does not own."""
    x0, x1, own = span
    return not any(t[0] // grid == y // grid and t[1] <= x1 and x0 <= t[2] for t in taken) and not clear(
        Box(x0, y, x1 - x0, 0), keeps, {}, gap=-1, own=own
    )


def bend_rows(
    ys: Sequence[int],
    spans: Sequence[Sequence[Span]],
    taken: Sequence[Taken],
    keeps: Sequence[Keep] = (),
    *,
    grid: int,
) -> list[int | None]:
    """The row index of each level (spans[k] are level k's x spans; ys the rows' y, top down).

    A level takes the first row at or beyond its depth, below the one before it, that no taken run in its grid row or
    hard footprint keep meets over its spans; with none free it has no row, None: a loss (R1225).
    """
    room = len(ys)
    rows: list[int | None] = []
    last = -1
    for k, level in enumerate(spans):
        r = max(k, last + 1)
        while r < room and not all(_free(ys[r], s, taken, keeps, grid) for s in level):
            r += 1
        rows.append(r if r < room else None)
        last = r if r < room else last
    return rows
