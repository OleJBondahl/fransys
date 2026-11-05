"""A padded bounding box around boxes, and the unit frames built on it: hulls, room findings, keeps (layout-0300, R900)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .clearance import Keep
from .errors import CoreError
from .geometry import inside, overlaps
from .outputs import Outline
from .values import Box, Finding

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .outputs import Placement
    from .values import Options, OutlineRoom, PlacementProblem


def outline_hull(boxes: Sequence[Box], margin: int) -> Box:
    """The smallest box holding every box, grown by margin on all four sides.

    The caller passes a margin on its grid.
    """
    if not boxes:
        msg = "outline_hull: no boxes; pass at least one box to outline"
        raise CoreError(msg)
    if margin < 0:
        msg = f"outline_hull: margin {margin} is negative; pass 0 or more"
        raise CoreError(msg)
    x0 = min(b.x for b in boxes) - margin
    y0 = min(b.y for b in boxes) - margin
    x1 = max(b.x + b.w for b in boxes) + margin
    y1 = max(b.y + b.h for b in boxes) + margin
    return Box(x0, y0, x1 - x0, y1 - y0)


def _framed(content: Sequence[Box], room: OutlineRoom) -> Box:
    """The hull of the members' rooms (`framed` gave each its margin and label room), widened to the label slot and the least size (R900)."""
    hull = outline_hull(content, 0)
    return Box(hull.x, hull.y, max(hull.w, room.label.x + room.label.w, room.least.w), max(hull.h, room.least.h))


def _grow(box: Box | None, room: OutlineRoom) -> Box | None:
    """`box` with the margin on every side and the label room above, at least the least size (runs are unknown before placement)."""
    top = room.label.y + room.label.h
    return box and Box(box.x - room.margin, box.y - top, max(box.w + 2 * room.margin, room.least.w), max(box.h + top + room.margin, room.least.h))


def framed(problem: PlacementProblem, options: Options) -> PlacementProblem:
    """`problem` whose frame members hold the room their frame needs: the margin on every side and the label room above (R1269).

    A footprint is a keep-out, so the pack, the y solve and the cut stand every other box off the frame by construction.
    """
    room = options.outline
    if room is None:
        return problem
    members = frozenset().union(*(m for _, m in problem.hints.frames))
    fits = {
        s.id: {o: replace(v, footprint=_grow(v.footprint, room), row_footprint=_grow(v.row_footprint, room)) for o, v in s.views.items()}
        for s in problem.symbols
        if s.id in members
    }
    return replace(problem, symbols=tuple(replace(s, views=fits[s.id]) if s.id in fits else s for s in problem.symbols))


def _runs(members: Sequence[Box], foreign: Sequence[Box]) -> list[list[Box]]:
    """The members in x order, split where the hull that takes the next one would hold a non-member (R1106)."""
    runs: list[list[Box]] = []
    for box in sorted(members, key=lambda b: (b.x, b.y)):
        if runs and not any(overlaps(outline_hull([*runs[-1], box], 0), f) for f in foreign):
            runs[-1].append(box)
        else:
            runs.append([box])
    return runs


def unit_hulls(placement: Placement, problem: PlacementProblem, options: Options) -> tuple[tuple[Outline, ...], tuple[Finding, ...]]:
    """One frame per run of a unit's members on a page, and OUTLINE_NO_ROOM for each run that has no room (R900, R1106).

    A frame never holds a non-member: a unit drawn in parts on one row gets one frame per part. A run that leaves
    the content box or has a footprint beside it too close is named, never shrunk. The members come from `Hints.frames`.
    """
    room = options.outline
    if room is None:
        return (), ()
    out: list[Outline] = []
    found: list[Finding] = []
    for page in placement.pages:
        for unit, members in problem.hints.frames:
            foreign = [p.footprint for p in page.placed if p.sym not in members]
            for run, boxes in enumerate(_runs([p.footprint for p in page.placed if p.sym in members], foreign)):
                box = _framed(boxes, room)
                if inside(box, problem.area, edge="closed") and not any(overlaps(box, f) for f in foreign):
                    out.append(Outline(unit, page.page, box, run))
                else:
                    found.append(Finding("OUTLINE_NO_ROOM", f"unit {unit}: no room for its frame on page {page.page}", page.page, unit))
    return tuple(out), tuple(found)


def outline_keeps(outlines: Sequence[Outline], room: OutlineRoom | None, page: int) -> tuple[Keep, ...]:
    """The page's frames as keeps: the four edges as 2-wide boxes on the line, and the label box (R900, UO6)."""
    keeps: list[Keep] = []
    for o in outlines:
        if o.page != page or room is None:
            continue
        b, lab = o.box, room.label
        wide, high = b.w + 2, b.h + 2
        edges = (Box(b.x - 1, b.y - 1, wide, 2), Box(b.x - 1, b.y + b.h - 1, wide, 2))
        sides = (Box(b.x - 1, b.y - 1, 2, high), Box(b.x + b.w - 1, b.y - 1, 2, high))
        label = Box(b.x + lab.x, b.y + lab.y, lab.w, lab.h)
        keeps += [Keep("", e, "outline", o.key) for e in (*edges, *sides, label)]
    return tuple(keeps)
