"""The pair step: the y a pair of consecutive cells needs for the flags on the wire between them.

A flag box reaches along the wire from its pin; the step between two cells keeps both.
"""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING

from .geometry import stub_views
from .ref_kind import kind_of
from .row_extent import grid_up
from .values import PinRef, RefKind

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .place_env import PageEnv
    from .place_room import Step
    from .values import RefEnd


def _ends(env: PageEnv) -> list[tuple[PinRef, str, RefEnd]]:
    """(pin, kind, end) of every flag end of the page: each reference end but an arrow's."""
    return [
        (end.pin, str(kind_of(ref)), end)
        for ref in env.refs
        if kind_of(ref) is not RefKind.ARROW
        for end in ref.ends
        if end.pin is not None and end.page == env.plan.page
    ]


def _reach(env: PageEnv, ends: Sequence[tuple[PinRef, str, RefEnd]], sym: str, pin: str | None, *, below: bool) -> int:
    """The G the tallest flag at `pin` of `sym` reaches along the wire, below it or above it."""
    face = env.options.marker_below if below else env.options.marker_above
    reach = 0
    for p, kind, end in ends:
        boxes = (
            stub_views(env.options.stub_lines, env.options.stub_table, p, end.also, end.far)
            or env.options.marker_fit.get((p, kind))
            or env.options.marker
        )
        if pin is not None and (p.sym, p.pin) == (sym, pin) and boxes and face is not None and face in boxes:
            box = boxes[face]
            reach = max(reach, box.y + box.h if below else -box.y)
    return reach


def pair_steps(env: PageEnv) -> dict[Step, int]:
    """The pin-to-pin y step each pair of consecutive cells needs for the flags between them.

    The flags of the upper cell's bottom pin and the lower cell's top pin stand on the wire
    between them. The fold holds a lane end's flags in its footprint, so only a pair has a step.
    """
    ends = _ends(env)
    out: dict[Step, int] = {}
    for pc in env.pcs.values():
        for li, cells in enumerate(pc.lanes):
            for i, (a, b) in enumerate(pairwise(cells)):
                need = _reach(env, ends, a.sym, a.bottom_pin, below=True) + _reach(env, ends, b.sym, b.top_pin, below=False)
                if need:
                    out[pc.id, li, i] = grid_up(need, env.options.wiring_grid)
    return out
