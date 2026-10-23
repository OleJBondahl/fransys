"""The room anchored items need beyond their owners' footprints (R392a, layout-0377)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .geometry import shift
from .room import Room, joined

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .outputs import Placed
    from .values import Anchor, PlacementProblem, Pose


def _reach(pose: Pose, at: Placed, pin: tuple[int, int]) -> Room:
    box, foot = shift(pose.outline, *pin), at.footprint
    return Room(
        max(0, foot.x - box.x),
        max(0, box.x + box.w - foot.x - foot.w),
        max(0, foot.y - box.y),
        max(0, box.y + box.h - foot.y - foot.h),
    )


def _room(anchor: Anchor, at: Placed, side: str) -> Room:
    pin = next(xy for xy in at.pin_xy if xy.pin == anchor.pin.pin)
    return joined(*(_reach(p, at, (pin.x, pin.y)) for s, p in anchor.poses if s == side))


def anchor_rooms(problem: PlacementProblem, placed: Mapping[str, Placed]) -> Mapping[str, Room]:
    """Per owner, the deepest pose on each anchored pin's side, in the owner's placed orient."""
    syms = {s.id: s for s in problem.symbols}
    out: dict[str, Room] = {}
    for a in problem.anchors:
        if (at := placed.get(a.pin.sym)) is None:
            continue
        sym = syms[a.pin.sym]
        index = next(i for i, p in enumerate(sym.pins) if p.id == a.pin.pin)
        side = sym.views[at.orient].pins[index].side
        out[a.pin.sym] = joined(out.get(a.pin.sym, Room()), _room(a, at, side))
    return out
