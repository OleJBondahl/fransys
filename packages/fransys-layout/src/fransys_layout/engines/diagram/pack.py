"""Packing separate pieces in rows to a target shape: a general technique over plain sizes.

Pieces keep their order and fill rows left to right. The row width is the one whose bounding box
is closest to the `shape` aspect, tried from each prefix width, so the shape is the caller's.
"""

from math import log
lazy from collections.abc import Sequence

type Size = tuple[int, int]


def _rows(sizes: Sequence[Size], limit: int, gap: int) -> list[list[int]]:
    """Indexes of `sizes` in rows, a row ending before its width passes `limit`."""
    rows: list[list[int]] = [[]]
    used = 0
    for i, (width, _) in enumerate(sizes):
        if rows[-1] and used + gap + width > limit:
            rows.append([])
            used = 0
        used += width + (gap if rows[-1] else 0)
        rows[-1].append(i)
    return rows


def _place(
    sizes: Sequence[Size], rows: Sequence[Sequence[int]], gap: int
) -> tuple[list[Size], Size]:
    """The top left of every piece for `rows`, and the bounding box."""
    at: list[Size] = [(0, 0)] * len(sizes)
    y = widest = 0
    for row in rows:
        x = 0
        for i in row:
            at[i] = (x, y)
            x += sizes[i][0] + gap
        widest = max(widest, x - gap)
        y += max(sizes[i][1] for i in row) + gap
    return at, (widest, y - gap)


def pack_rows(sizes: Sequence[Size], *, shape: Size, gap: int) -> tuple[Size, ...]:
    """The top left `(x, y)` of each `(width, height)` piece, packed in rows to `shape`.

    The row limits tried are the prefix widths; the best has its bounding box's aspect nearest
    the shape's (log distance), ties to the smaller area, then the narrower limit.
    """
    if not sizes:
        return ()
    target = log(shape[0] / shape[1])
    limits, total = [], -gap
    for width, _ in sizes:
        total += width + gap
        limits.append(total)
    tried = (_candidate(sizes, limit, gap, target) for limit in {max(w for w, _ in sizes), *limits})
    return tuple(min(tried, key=lambda c: c[0])[1])


def _candidate(
    sizes: Sequence[Size], limit: int, gap: int, target: float
) -> tuple[tuple[float, int, int], list[Size]]:
    """The ranking key and the placement for one row limit."""
    at, (w, h) = _place(sizes, _rows(sizes, limit, gap), gap)
    return (round(abs(log(max(w, 1) / max(h, 1)) - target), 9), w * h, limit), at
