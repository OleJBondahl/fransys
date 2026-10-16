"""Jumper groups as lanes: first fit over their row spans, so spans that overlap never share one."""

from collections.abc import Sequence  # noqa: TC003 -- signature tests resolve hints at runtime

from .rows_jumper_lanes import JumperLane, JumperLanes

__all__ = [
    "BRIDGE_PIECES",
    "bridge_piece_key",
    "first_fit_lanes",
    "jumper_lane_count",
    "jumper_lanes",
]

BRIDGE_PIECES = ("line", "tick")
"""The Bridge mark pieces render draws once: a lane's `line` and a member row's `tick`."""


def first_fit_lanes(spans: Sequence[tuple[int, int]]) -> tuple[int, ...]:
    """Each `(first, last)` span's lane in the given order: the lowest lane free before `first`."""
    lane_ends: list[int] = []  # lane_ends[lane] is the last index that lane is used through
    lanes: list[int] = []
    for first, last in spans:
        lane = next((i for i, end in enumerate(lane_ends) if end < first), None)
        if lane is None:
            lane = len(lane_ends)
            lane_ends.append(last)
        else:
            lane_ends[lane] = last
        lanes.append(lane)
    return tuple(lanes)


def jumper_lanes(groups: tuple[int | None, ...]) -> JumperLanes:
    """Each jumper group's lane, from `groups` (each row's `jumper_group`), by group number."""
    first: dict[int, int] = {}
    last: dict[int, int] = {}
    for index, group in enumerate(groups):
        if group is None:
            continue
        first.setdefault(group, index)
        last[group] = index
    numbers = sorted(first)
    spans = [(first[group], last[group]) for group in numbers]
    lanes = first_fit_lanes(spans)
    return JumperLanes(
        lanes=tuple(
            JumperLane(group=group, first=start, last=end, lane=lane)
            for group, (start, end), lane in zip(numbers, spans, lanes, strict=True)
        )
    )


def jumper_lane_count(lanes: JumperLanes) -> int:
    """The distinct lanes `lanes` uses (the highest lane plus one), not one per group."""
    return max((span.lane for span in lanes.lanes), default=-1) + 1


def bridge_piece_key(piece: str) -> str:
    """The key of a Bridge mark piece in the map render hands pdf; one spelling for both."""
    return f"bridge-{piece}"


BRIDGE_PIECE_KEYS = frozendict({piece: bridge_piece_key(piece) for piece in BRIDGE_PIECES})
"""Each Bridge mark piece's key: what render keys its drawings by and pdf looks them up with."""
