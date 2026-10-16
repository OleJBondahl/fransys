"""The diagram engine's stage columns: a box's column is its line distance from the first box.

The first box has the most lines (a line counts at both ends), ties by text rank. A box not joined
to it starts a new component: its first box follows the same rule, at the last column so far + 1.
"""

from collections import defaultdict, deque
lazy from collections.abc import Collection, Hashable, Iterable, Mapping, Sequence


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


def _reaches[B: Hashable](boxes: tuple[B, ...], lines: Iterable[tuple[B, B]]) -> list[dict[B, int]]:
    """Each component's line distances from its first box, in the order the first boxes rank."""
    joined: dict[B, list[B]] = defaultdict(list)
    for a, b in lines:
        joined[a].append(b)
        joined[b].append(a)
    by_rule = sorted(range(len(boxes)), key=lambda i: (-len(joined[boxes[i]]), i))
    seen: set[B] = set()
    reaches = []
    for i in by_rule:
        if boxes[i] not in seen:
            reaches.append(_distances(boxes[i], joined))
            seen.update(reaches[-1])
    return reaches


def pieces[B: Hashable](
    boxes: tuple[B, ...], lines: Iterable[tuple[B, B]]
) -> tuple[tuple[B, ...], ...]:
    """The separate pieces of a diagram, each its boxes in text order, in column order."""
    return tuple(
        tuple(b for b in boxes if b in reached) for reached in _reaches(boxes, tuple(lines))
    )


def assign_columns[B: Hashable](
    boxes: tuple[B, ...], lines: Iterable[tuple[B, B]]
) -> tuple[tuple[B, ...], ...]:
    """Columns left to right, each a tuple of boxes in text order; `boxes` arrive in text order."""
    column: dict[B, int] = {}
    used = 0
    for reached in _reaches(boxes, lines):
        column.update({box: used + d for box, d in reached.items()})
        used += max(reached.values()) + 1
    return tuple(tuple(b for b in boxes if column[b] == c) for c in range(used))


def _depths[B: Hashable](column: Sequence[B], joined: Mapping[B, Sequence[B]]) -> dict[B, int]:
    """Each box's line distance from the nearest box of `column`."""
    depth = dict.fromkeys(column, 0)
    queue = deque(column)
    while queue:
        box = queue.popleft()
        for other in joined[box]:
            if other not in depth:
                depth[other] = depth[box] + 1
                queue.append(other)
    return depth


def _side[B: Hashable](part: Sequence[B], depth: Mapping[B, int], left: Collection[B]) -> int:
    """-1 when most of `part`'s boxes beside the column are in `left`, else 1."""
    near = [b for b in part if depth[b] == 1]
    return -1 if 2 * sum(b in left for b in near) > len(near) else 1


def _stand[B: Hashable](
    boxes: tuple[B, ...], joined: Mapping[B, Sequence[B]], column: Sequence[B], left: Collection[B]
) -> dict[B, int]:
    """Each box's place beside `column`: 0 in it, else its distance from it, signed by its side.

    The boxes left once `column` is taken out fall into parts; a part stands on one side, so no
    line runs across the column.
    """
    depth = _depths(column, joined)
    at = dict.fromkeys(column, 0)
    for first in boxes:
        if first in at or first not in depth:
            continue
        part, queue = {first: depth[first]}, deque([first])
        while queue:
            for other in joined[queue.popleft()]:
                if other not in at and other not in part:
                    part[other] = depth[other]
                    queue.append(other)
        side = _side(list(part), depth, left)
        at.update({box: side * d for box, d in part.items()})
    return at


def column_columns[B: Hashable](
    boxes: tuple[B, ...], lines: Iterable[tuple[B, B]], column: Sequence[B], left: Collection[B]
) -> tuple[tuple[B, ...], ...]:
    """Columns with `column` as one column; the other boxes stand beside it by `_stand`.

    A part that touches `column` stands left when most of its boxes beside the column are in
    `left`, else right. Boxes that reach none of `column` follow, right of the rest.
    """
    lines = tuple(lines)
    joined: dict[B, list[B]] = defaultdict(list)
    for a, b in lines:
        joined[a].append(b)
        joined[b].append(a)
    at = _stand(boxes, joined, column, left)
    low = min(at.values())
    placed = [
        tuple(b for b in boxes if at.get(b) == i + low) for i in range(max(at.values()) - low + 1)
    ]
    rest = tuple(b for b in boxes if b not in at)
    return (*placed, *assign_columns(rest, lines)) if rest else tuple(placed)
