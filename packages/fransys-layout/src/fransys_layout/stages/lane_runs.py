"""Cut a row of lanes into runs no wider than a room.

Fill first, never parting lanes that overlap or are linked (decision layout-0182).
`fill_runs` is the same fill for column widths (layout-0230).
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


def held_boundaries(links: Iterable[tuple[int, int]]) -> set[int]:
    """The boundaries (the index of the lane after) that a link crosses."""
    return {i for a, b in links for i in range(min(a, b) + 1, max(a, b) + 1)}


def _blocks(
    extents: Sequence[tuple[int, int]], links: Iterable[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Maximal lane runs between open boundaries: no reach back over an earlier lane, no link."""
    held = held_boundaries(links)
    blocks: list[tuple[int, int]] = []
    start, reach = 0, extents[0][1]
    for i in range(1, len(extents)):
        if extents[i][0] >= reach and i not in held:
            blocks.append((start, i))
            start = i
        reach = max(reach, extents[i][1])
    blocks.append((start, len(extents)))
    return blocks


def _span(extents: Sequence[tuple[int, int]], start: int, stop: int) -> tuple[int, int]:
    """The low and high of lanes start..stop."""
    part = extents[start:stop]
    return min(low for low, _ in part), max(high for _, high in part)


def lane_runs(
    extents: Sequence[tuple[int, int]], links: Iterable[tuple[int, int]], room: int
) -> tuple[tuple[int, int], ...]:
    """Half-open lane ranges, each no wider than `room` unless one block alone is wider."""
    if not extents:
        return ()
    runs: list[tuple[int, int]] = []
    start = 0
    for first, stop in _blocks(extents, links):
        if first > start:
            low, high = _span(extents, start, stop)
            if high - low > room:
                runs.append((start, first))
                start = first
    runs.append((start, len(extents)))
    return tuple(runs)


def fill_runs(
    sizes: Sequence[int], links: Iterable[tuple[int, int]], room: int
) -> tuple[tuple[int, int], ...]:
    """Half-open ranges of `sizes`, each filled to `room` and ending at a boundary no link spans.

    A run keeps at least its first size; with no free boundary in reach it ends where it is full.
    """
    held = held_boundaries(links)
    runs: list[tuple[int, int]] = []
    start = 0
    while start < len(sizes):
        fits, used = start + 1, sizes[start]
        while fits < len(sizes) and used + sizes[fits] <= room:
            used += sizes[fits]
            fits += 1
        end = next((e for e in range(fits, start, -1) if e not in held), fits)
        runs.append((start, end))
        start = end
    return tuple(runs)
