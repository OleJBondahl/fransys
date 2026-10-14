"""Overview engine, reading: which lane a box with no function group stands in (LO4).

A plain-value function: the caller passes the groups' lanes, the strips and the box pairs.
"""

from collections import Counter
lazy from collections.abc import Collection, Hashable, Iterable, Mapping, Sequence

from fransys_layout.engines.overview.lanes.flow import neighbours

PASSES = 3


def lane_rule[K: Hashable](
    order: Sequence[K],
    group: Mapping[K, int | None],
    strips: Collection[K],
    pairs: Iterable[tuple[K, K]],
    shared: int,
) -> dict[K, int]:
    """Each box's lane: its group's, `shared` for a strip with none, else its neighbours' majority.

    A box with no group takes its grouped neighbours' majority lane, in `order`, three passes, a tie
    to the earlier lane; else `shared`. Neighbours in `shared` do not vote.
    """
    near = neighbours(order, pairs)
    lane = {b: shared if group[b] is None and b in strips else group[b] for b in order}
    for _ in range(PASSES):
        for box in order:
            votes = Counter(lane[o] for o in near[box] if lane[o] is not None and lane[o] != shared)
            if lane[box] is None and votes:
                lane[box] = min(votes, key=lambda ix: (-votes[ix], ix))
    return {b: shared if ix is None else ix for b, ix in lane.items()}
