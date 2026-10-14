"""Layout-0256: leaving-line stubs whose boxes meet stand in a staircase, one tier each.

The upright stubs of a page that face the same way and whose boxes meet are lifted by whole
tiers, each box growing from its line toward one side. The stub nearest that side is the lowest
tier, so no line crosses a higher box. A cluster that finds no free staircase stays as it stands.
"""

from dataclasses import replace
from itertools import pairwise
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import WIRING_GRID, Box, Facing, Point, boxes_meet, port_exit
from fransys_layout.geometry.units import TEXT_GAP
from fransys_model.kernel import Finding, Severity

from .line_trunk import stub_edge
from .space import span
from .texts.candidates import Candidate, box_of, stub_anchor

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .line_shapes import LineStub

    type Path = tuple[Any, int, tuple[Point, ...]]  # harness, branch, points

_UPRIGHT = (Facing.N, Facing.S)
STUBS_NOT_STACKED = "STUBS_NOT_STACKED"


def _clusters(stubs: Sequence[LineStub]) -> list[list[int]]:
    """Indexes of the upright stubs, grouped by facing and by their boxes meeting."""
    groups: list[list[int]] = []
    for n, stub in enumerate(stubs):
        if stub.facing not in _UPRIGHT:
            continue
        joined = [
            g
            for g in groups
            if stubs[g[0]].facing is stub.facing
            and any(boxes_meet(stubs[m].box, stub.box, closed=True, gap=TEXT_GAP) for m in g)
        ]
        groups = [g for g in groups if g not in joined]
        groups.append([n, *(m for g in joined for m in g)])
    return [g for g in groups if len(g) > 1]


def _lifted(stub: LineStub, tier: int, *, right: bool) -> LineStub:
    """`stub` `tier` steps further out, its box starting at its line and growing to a side."""
    width, height = stub.box.width, stub.box.height
    at = port_exit(stub.at, stub.facing, tier * -(-(height + TEXT_GAP) // WIRING_GRID))
    box = box_of(Candidate(side=stub.facing, offset=0), stub_anchor(at), (width, height))
    return replace(
        stub, at=at, box=replace(box, x=at.x - TEXT_GAP if right else at.x + TEXT_GAP - width)
    )


def _run_on(points: tuple[Point, ...], old: Point, new: Point) -> tuple[Point, ...] | None:
    """`points` run on from its last point `old` to `new`, or `None` when it ends elsewhere."""
    if points[-1] != old:
        return None
    straight = len(points) > 1 and (
        points[-2].x == old.x == new.x or points[-2].y == old.y == new.y
    )
    return (*points[:-1], new) if straight else (*points, new)


def _carried(path: Path, old: Point, new: Point) -> Path | None:
    """`path` with whichever end is at `old` run on to `new`, or `None` when none is."""
    owner, branch, points = path
    forward = _run_on(points, old, new)
    back = None if forward is not None else _run_on(points[::-1], old, new)
    found = forward or (back[::-1] if back else None)
    return None if found is None else (owner, branch, found)


def _carry_all(
    paths: Sequence[Path], olds: Sequence[LineStub], news: Sequence[LineStub]
) -> tuple[list[Path], list[tuple[Box, int]]] | None:
    """The paths with each stub's line run on, and each stub's run box with its path's index."""
    result, runs = list(paths), []
    for old, new in zip(olds, news, strict=True):
        was, now = stub_edge(old.at, old.facing), stub_edge(new.at, new.facing)
        mine = [
            (n, c)
            for n, p in enumerate(result)
            if p[0] == old.harness and (c := _carried(p, was, now)) is not None
        ]
        if not mine:
            return None
        result[mine[0][0]] = mine[0][1]
        runs.append((span(was, now), mine[0][0]))
    return result, runs


def _free(
    news: Sequence[LineStub],
    laid: tuple[list[Path], list[tuple[Box, int]]],
    obstacles: Sequence[Box],
    content: Box,
) -> bool:
    """Whether the lifted boxes and runs stand in `content`, clear of each other, shapes, lines."""
    paths, runs = laid
    boxes = [one.box for one in news]
    right, bottom = content.x + content.width, content.y + content.height
    if not all(content.x <= b.x and b.x + b.width <= right for b in boxes):
        return False
    if not all(content.y <= b.y and b.y + b.height <= bottom for b in boxes):
        return False
    for n, (box, (run, own)) in enumerate(zip(boxes, runs, strict=True)):
        theirs = [b for m, b in enumerate(boxes) if m != n]
        lines = [
            span(one, two) for m, p in enumerate(paths) if m != own for one, two in pairwise(p[2])
        ]
        if any(boxes_meet(box, b, closed=True, gap=TEXT_GAP) for b in (*theirs, *lines)):
            return False
        if any(boxes_meet(run, b, closed=True) for b in (*theirs, *lines)):
            return False
        if any(boxes_meet(s, o, closed=True) for s in (box, run) for o in obstacles):
            return False
    return True


def _staircase(
    stubs: Sequence[LineStub],
    group: Sequence[int],
    paths: Sequence[Path],
    room: tuple[Sequence[Box], Box],
) -> tuple[dict[int, LineStub], list[Path]] | None:
    """The group's lifted stubs and the carried paths, growing right if free, else left."""
    for right in (True, False):
        order = sorted(group, key=lambda n: stubs[n].at.x, reverse=right)
        news = [_lifted(stubs[n], tier, right=right) for tier, n in enumerate(order)]
        laid = _carry_all(paths, [stubs[n] for n in order], news)
        if laid is not None and _free(news, laid, *room):
            return dict(zip(order, news, strict=True)), laid[0]
    return None


def _unstacked(stubs: Sequence[LineStub], group: Sequence[int]) -> Finding:
    """The note for a cluster that found no free staircase: its page and the lines of its stubs."""
    first = stubs[group[0]]
    harnesses = tuple(dict.fromkeys(stubs[n].harness for n in sorted(group)))
    return Finding(
        code=STUBS_NOT_STACKED,
        severity=Severity.INFO,
        subjects=harnesses,
        message=(
            f"p{first.drawing_set}.{first.page}: Fransys could not draw this cleanly; "
            "please report it with the smallest model. "
            f"The {len(group)} stubs of these lines found no free "
            "staircase, so their texts overlap"
        ),
    )


def stack_stubs(
    stubs: Sequence[LineStub], paths: Sequence[Path], obstacles: Sequence[Box], content: Box
) -> tuple[tuple[LineStub, ...], list[Path], tuple[Finding, ...]]:
    """`stubs` with every cluster of meeting boxes in a staircase, and the paths carried with.

    A cluster that finds no free staircase stays as it stands and gets a note (STUBS_NOT_STACKED).
    """
    result, carried, notes = list(stubs), list(paths), []
    for group in _clusters(stubs):
        found = _staircase(result, group, carried, (obstacles, content))
        if found is None:
            notes.append(_unstacked(stubs, group))
            continue
        for n, new in found[0].items():
            result[n] = new
        carried = found[1]
    return tuple(result), carried, tuple(notes)
