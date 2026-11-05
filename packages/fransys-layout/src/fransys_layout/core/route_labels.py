"""Stage 6b: a page's labels, stood after its fixed wires and before its A* round (TEXT-CANDIDATES, layout-0515).

A label that is blocked at every candidate hands its need to the gap beside its column as a demand:
widen cuts the pitch again; still blocked after that, ANNEX_UNPLACED names it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .annex import place_labels, text_keeps
from .outputs import Demand

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .annex_values import Annex, AnnexBox
    from .clearance import Keep
    from .outputs import Wire
    from .route_env import RouteEnv
    from .values import Finding


def _need(env: RouteEnv, annex: Annex) -> Demand | None:
    """The tracks the gap beside the annex owner's column must hold for its box and the gap, else None (no gap beside it)."""
    col = next((c for c in env.columns if any(cell.sym == annex.owner for lane in c.lanes for cell in lane.cells)), None)
    if col is None:
        return None
    gap = next((g for g in env.gaps if g.left == col.id), None) or next((g for g in env.gaps if g.right == col.id), None)
    if gap is None:
        return None
    more = -(-(annex.size.w + env.options.label_gap) // env.options.wiring_grid)
    return Demand(gap.id, max(gap.tracks, 1) + more)


def page_labels(env: RouteEnv, wires: Sequence[Wire]) -> tuple[tuple[AnnexBox, ...], tuple[Keep, ...], tuple[Finding, ...], tuple[Demand, ...]]:
    """The page's labels, the keeps of those that stand, ANNEX_UNPLACED for the others and their demands on the gaps."""
    if not env.annexes:
        return (), (), (), ()
    ink = (wires, [k.box for k in env.obstacles])
    labels, found, blocked = place_labels(
        env.annexes, env.placed, ink, (env.page, env.area, env.options.label_gap, env.options.label_moves), env.labels
    )
    standing = text_keeps(a for i, a in enumerate(labels) if i not in blocked)
    needs = (_need(env, env.annexes[i]) for i in blocked)
    return tuple(labels), standing, tuple(found), tuple(d for d in needs if d)
