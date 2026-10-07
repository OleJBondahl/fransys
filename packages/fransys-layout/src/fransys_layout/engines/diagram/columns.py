"""The diagram engine's stage columns (BD5): a box's column is its line distance from the first box.

The first box has the most lines (a line counts at both ends), ties by text rank. A box not joined
to it starts a new component: its first box follows the same rule, at the last column so far + 1.
"""

from collections import defaultdict, deque
lazy from collections.abc import Hashable, Iterable, Mapping, Sequence


def _distances[B: Hashable](first: B, joined: Mapping[B, Sequence[B]]) -> dict[B, int]:
    """Breadth-first line distance from `first` to every box it reaches."""
    dist = {first: 0}
    queue = deque([first])
    while queue:
        box = queue.popleft()
        for other in joined[box]:
            if other not in dist:
                dist[other] = dist[box] + 1
                queue.append(other)
    return dist


def assign_columns[B: Hashable](
    boxes: tuple[B, ...], lines: Iterable[tuple[B, B]]
) -> tuple[tuple[B, ...], ...]:
    """Columns left to right, each a tuple of boxes in text order; `boxes` arrive in text order."""
    joined: dict[B, list[B]] = defaultdict(list)
    for a, b in lines:
        joined[a].append(b)
        joined[b].append(a)
    by_rule = sorted(range(len(boxes)), key=lambda i: (-len(joined[boxes[i]]), i))
    column: dict[B, int] = {}
    used = 0
    for i in by_rule:
        if boxes[i] in column:
            continue
        reached = _distances(boxes[i], joined)
        column.update({box: used + d for box, d in reached.items()})
        used += max(reached.values()) + 1
    return tuple(tuple(b for b in boxes if column[b] == c) for c in range(used))
