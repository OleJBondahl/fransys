"""The diagram engine's row order in each column (BD5): one pass down, one pass up, then stop.

Down: columns 1..last, by the mean row of neighbours in the previous column, as already reordered.
Up: columns last-1..0, the same with neighbours in the next column only, never both sides.
No such neighbour: the box's current row is its key. Ties by text rank; same-column lines ignored.
The mean is weighted by lines: parallel lines to one neighbour count once each.
"""

from fractions import Fraction
lazy from collections.abc import Hashable, Iterable, Mapping


def _sorted_by[B: Hashable](
    column: tuple[B, ...],
    reference: tuple[B, ...],
    ends: Mapping[B, list[B]],
    rank: Mapping[B, int],
) -> tuple[B, ...]:
    """`column` sorted by the mean reference row of each box's line ends, ties by text rank."""
    row = {box: i for i, box in enumerate(reference)}
    keys = {}
    for current, box in enumerate(column):
        rows = [row[o] for o in ends[box] if o in row]
        keys[box] = Fraction(sum(rows), len(rows)) if rows else Fraction(current)
    return tuple(sorted(column, key=lambda box: (keys[box], rank[box])))


def order_columns[B: Hashable](
    columns: tuple[tuple[B, ...], ...], lines: Iterable[tuple[B, B]], rank: Mapping[B, int]
) -> tuple[tuple[B, ...], ...]:
    """Reorder each column's rows by one pass down, one up; `rank` is each box's text rank."""
    ends: dict[B, list[B]] = {box: [] for column in columns for box in column}
    for a, b in lines:
        ends[a].append(b)
        ends[b].append(a)
    result = list(columns)
    for i in range(1, len(result)):
        result[i] = _sorted_by(result[i], result[i - 1], ends, rank)
    for i in range(len(result) - 2, -1, -1):
        result[i] = _sorted_by(result[i], result[i + 1], ends, rank)
    return tuple(result)
