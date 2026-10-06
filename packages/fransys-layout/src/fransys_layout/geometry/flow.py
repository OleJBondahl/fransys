"""Items laid one after another along an axis (cleanup step 2, F4)."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


def flow[T](
    items: Sequence[T],
    *,
    floor: int,
    gaps: Sequence[int],
    far_edge: Callable[[T, int], int],
    near_edge: Callable[[T], int] | None = None,
) -> list[tuple[int, int]]:
    """Moves `(index, floor)`; next floor = `far_edge(item, floor)` + gap; `near_edge` stops."""
    moves: list[tuple[int, int]] = []
    for index, item in enumerate(items):
        if near_edge is not None and near_edge(item) >= floor:
            break
        moves.append((index, floor))
        floor = far_edge(item, floor) + gaps[index]
    return moves
