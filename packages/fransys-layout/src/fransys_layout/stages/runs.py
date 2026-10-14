"""Runs of placements and their boxes: the general half of an outline (OUTLINES BO5).

Takes a set of members' placements, the page's placements and plain options; returns runs and
run boxes. It names no black box and no frame: the caller passes its convention as an option.
"""

from typing import TYPE_CHECKING

from fransys_layout.geometry import Box, cut_runs, hull, overlaps, translate

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.kernel import AuthoringKey

    from .types import PlacedFunction


def column_stretches(
    members: Sequence[PlacedFunction], placed: Sequence[PlacedFunction]
) -> list[list[AuthoringKey]]:
    """The columns of `members` by x, cut where a column of none of them stands between two."""
    own = {one.column for one in members}
    x_of: dict[AuthoringKey, int] = {}
    for one in members:
        x_of[one.column] = min(x_of.get(one.column, one.at.x), one.at.x)
    others = [one.at.x for one in placed if one.column not in own]
    ordered = sorted(own, key=lambda key: (x_of[key], str(key)))
    return cut_runs(ordered, lambda key: x_of[key], others)


def _cut_by_foreign(
    run: Sequence[PlacedFunction], placed: Sequence[PlacedFunction]
) -> list[list[PlacedFunction]]:
    """OUTLINE-ENCLOSE: a non-member in a member's column between two members cuts the run."""
    names = {m.function for m in run}
    parts: dict[int, list[PlacedFunction]] = {}
    for one in run:
        ys = [m.at.y for m in run if m.column == one.column]
        cuts = [
            f.at.y
            for f in placed
            if f.column == one.column and f.function not in names and min(ys) < f.at.y < max(ys)
        ]
        parts.setdefault(sum(c < one.at.y for c in cuts), []).append(one)
    return [parts[k] for k in sorted(parts)]


def body_box(one: PlacedFunction) -> Box:
    """The placed function's body box on the page."""
    return translate(one.geometry.body, dx=one.at.x, dy=one.at.y)


def _cut_by_obstacles(
    run: Sequence[PlacedFunction], obstacles: Sequence[Box]
) -> list[list[PlacedFunction]]:
    """BO6: cut `run` where an obstacle box falls inside its box, left of it or above it."""
    whole = hull(body_box(m) for m in run)
    for hit in (o for o in obstacles if overlaps(whole, o)):
        for axis in ("x", "y"):
            centre = hit.x + hit.width / 2 if axis == "x" else hit.y + hit.height / 2
            before = [m for m in run if getattr(m.at, axis) < centre]
            if before and len(before) < len(run):
                after = [m for m in run if m not in before]
                return [*_cut_by_obstacles(before, obstacles), *_cut_by_obstacles(after, obstacles)]
    return [list(run)]


def member_runs(
    members: Sequence[PlacedFunction],
    placed: Sequence[PlacedFunction],
    *,
    enclose: bool = True,
    obstacles: Sequence[Box] = (),
) -> list[list[PlacedFunction]]:
    """`members` cut into runs so a box never spans unrelated columns.

    A column of none of the members between two cuts the run; with `enclose` so does a non-member
    between two members of a column. An `obstacles` box inside a run's box cuts it (BO6).
    """
    runs = []
    for stretch in column_stretches(members, placed):
        run = [one for column in stretch for one in members if one.column == column]
        for part in _cut_by_foreign(run, placed) if enclose else [run]:
            runs.extend(_cut_by_obstacles(part, obstacles))
    return runs


def run_box(
    members: Sequence[PlacedFunction], texts: Sequence[Box] = (), *, padding: int, floor: int = 0
) -> Box:
    """The box round the members' bodies and `texts`, `padding` each side, never left of `floor`."""
    whole = hull([*(translate(m.geometry.body, dx=m.at.x, dy=m.at.y) for m in members), *texts])
    left = max(whole.x - padding, floor)
    top = whole.y - padding
    return Box(
        x=left,
        y=top,
        width=whole.x + whole.width + padding - left,
        height=whole.y + whole.height + padding - top,
    )
