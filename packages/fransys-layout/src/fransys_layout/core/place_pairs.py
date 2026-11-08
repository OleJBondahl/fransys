"""Stage 5, place: an arrow reference stands at both its ends or at neither, decided with the lanes (R1488)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .cut_end_rooms import arrow_poles
from .place_assemble import assemble
from .ref_kind import kind_of
from .values import RefKind

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .flow_values import Fan
    from .outputs import PagePlacement, Trunk
    from .place_env import PageEnv
    from .values import PagePlan, Ref


def _lost(ref: Ref, fan: Fan, trunks: Sequence[Trunk], plans: Mapping[int, PagePlan]) -> bool:
    """Whether a lane end where `ref` stands found no stand (`Trunk.stood`)."""
    where = {(e.page, e.row) for e in ref.ends}
    for t in (t for t in trunks if t.fan == fan.id and (t.page, t.row) in where and t.stood):
        left, right = arrow_poles(fan, [ref], plans[t.page], t.row)
        if any(not t.stood[j][0] for j in left) or any(not t.stood[j][1] for j in right):
            return True
    return False


def _unstood(t: Trunk, fan: Fan, dead: Sequence[Ref], live: Sequence[Ref], plan: PagePlan) -> Trunk:
    """`t` with `stood` False at every lane end where only a dead arrow stands: no marker is drawn there, MARKER_UNPLACED says so."""
    gone, kept = arrow_poles(fan, dead, plan, t.row), arrow_poles(fan, live, plan, t.row)
    stood = tuple((s[0] and not (j in gone[0] and j not in kept[0]), s[1] and not (j in gone[1] and j not in kept[1])) for j, s in enumerate(t.stood))
    return replace(t, stood=stood)


def settled(stages: Sequence[tuple[PageEnv, Mapping[str, int], Mapping[str, int]]], pages: Sequence[PagePlacement]) -> list[PagePlacement]:
    """The pages with every arrow whose end found no stand cleared: both its ends, their lanes re-run to their hull and `stood` False.

    The one verdict of the pair (R436 moved from the marker stage); the page's other lanes are as placed.
    """
    refs = stages[0][0].refs if stages else ()
    fans = {f.id: f for f in stages[0][0].flow.fans} if stages else {}
    trunks, plans = [t for p in pages for t in p.trunks], {env.plan.page: env.plan for env, _, _ in stages}
    dead = [r for r in refs if kind_of(r) is RefKind.ARROW and r.net in fans and _lost(r, fans[r.net], trunks, plans)]
    if not dead:
        return list(pages)
    live = [r for r in refs if r not in dead]
    hit = {e.page for r in dead for e in r.ends}
    out = []
    for (env, x, y), page in zip(stages, pages, strict=True):
        if page.page not in hit:
            out.append(page)
            continue
        again = assemble(replace(env, refs=tuple(live)), x, y)
        out.append(replace(again, runs=page.runs, trunks=tuple(_unstood(t, fans[t.fan], dead, live, env.plan) for t in again.trunks)))
    return out
