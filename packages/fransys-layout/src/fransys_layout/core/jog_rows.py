"""The bend row of each level of a jog nest, kept off the rows the page already holds (R428)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .values import XY

type Taken = tuple[int, int, int]
"""A horizontal run already laid: its y and its x range."""


def taken_rows(runs: Sequence[tuple[XY, XY]]) -> tuple[Taken, ...]:
    """The horizontal runs among these segments, as (y, x0, x1)."""
    return tuple(
        (a[1], min(a[0], b[0]), max(a[0], b[0])) for a, b in runs if a[1] == b[1] and a != b
    )


def _free(y: int, span: tuple[int, int], taken: Sequence[Taken]) -> bool:
    return not any(t[0] == y and t[1] <= span[1] and span[0] <= t[2] for t in taken)


def bend_rows(
    y0: int,
    grid: int,
    room: int,
    spans: Sequence[Sequence[tuple[int, int]]],
    taken: Sequence[Taken],
) -> list[int]:
    """The row index of each level (spans[k] are level k's x spans).

    A level takes the first row below the one before it, at or beyond its depth, that no taken run
    of the page lies on over its spans. When no row within `room` is free it keeps its depth row.
    """
    rows: list[int] = []
    for k, level in enumerate(spans):
        r = max(k, rows[-1] + 1 if rows else 0)
        while r < room and not all(_free(y0 + grid * (r + 1), s, taken) for s in level):
            r += 1
        rows.append(r if r < room else k)
    return rows
