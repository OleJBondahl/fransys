"""Stage 1: boxes that make one series-parallel tree stand as one column (SERIES-PARALLEL SP4).

`series_tree.tree_lanes` deals the boxes into lanes; the tree's order comes first and each hop of
a Series must face (N up, S down), else the boxes keep today's flow with a CHAIN_REFUSED. Lane 0
is a chain lane; every other lane is a member lane beside it, joined by its first hop net to the
box after it in the lane it joins, level with the first box it stands beside. A member below a
box is refused for now: its head join would level it with that box, not beside its span. The
caller measures each hop once (`HopFacts`).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING

from .series_tree import has_parallel, leaves_of, tree_lanes
from .topology_chains import MemberDraft, member_offset
from .topology_fans import LaneDraft
from .values import Cell, End, PinRef

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .series_tree import TreeLane
    from .series_values import Series
    from .sym_values import Sym
    from .topology_chains import Ends
    from .values import Options

type Given = tuple[Ends, Mapping[str, Sym], Options]
type Made = tuple[list[LaneDraft], set[str]]


@dataclass(frozen=True, slots=True)
class BoxChain:
    """The boxes of one chain from its first end, and the nets of each hop between them."""

    boxes: tuple[str, ...]
    hops: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class HopFacts:
    """Each hop from an upper box to a lower one: its nets in lane order, and whether it faces."""

    nets: Mapping[tuple[str, str], tuple[str, ...]]
    faces: AbstractSet[tuple[str, str]]


def tree_of(comp: Sequence[str], series: Sequence[Series]) -> Series | None:
    """The tree whose leaves are exactly the component's boxes and that holds a Parallel."""
    boxes = set(comp)
    return next((t for t in series if has_parallel(t) and _same(leaves_of(t), boxes)), None)


def _same(leaves: Sequence[str], boxes: AbstractSet[str]) -> bool:
    return len(leaves) == len(boxes) and set(leaves) == boxes


def tree_column(tree: Series, hops: HopFacts, given: Given) -> Made | str:
    """The lanes of the tree's column and the hop nets they draw, else why it is no column."""
    ends, drawn, _ = given
    lanes = tree_lanes(tree, {b: drawn[b].footprint.h for b in leaves_of(tree)})
    used = [p for i in range(len(lanes)) for p in _pairs(lanes, i)]
    reason = _refusal(used, hops) or _below_a_box(lanes)
    if reason is not None:
        return reason
    first = lanes[0].leaves
    main = BoxChain(first, tuple(hops.nets[p] for p in pairwise(first)))
    made: list[LaneDraft] = [box_lane(main, ends)]
    gone = {n for hop in main.hops for n in hop}
    for i in range(1, len(lanes)):
        draft, anchors = _member(lanes, i, (hops, made), given)
        made.append(draft)
        gone |= anchors
    return made, gone


def _around(lanes: Sequence[TreeLane], i: int) -> tuple[str | None, str | None]:
    """The box before and the box after lane i's span in the lane it joins."""
    lane = lanes[i]
    parent = lanes[lane.parent or 0].leaves
    k, m = parent.index(lane.head or ""), parent.index(lane.foot or "")
    return (parent[k - 1] if k else None), (parent[m + 1] if m + 1 < len(parent) else None)


def _pairs(lanes: Sequence[TreeLane], i: int) -> list[tuple[str, str]]:
    """Every hop lane i stands on: inside it, and for a joined lane its head and its foot."""
    leaves = lanes[i].leaves
    out = list(pairwise(leaves))
    if i:
        before, after = _around(lanes, i)
        out += [(before, leaves[0])] if before else []
        out += [(leaves[-1], after)] if after else []
    return out


def _refusal(used: Sequence[tuple[str, str]], hops: HopFacts) -> str | None:
    """Why the tree's boxes make no column: a missing or an extra hop, or a hop not facing."""
    missing = next(((a, b) for a, b in used if (a, b) not in hops.nets), None)
    if missing is not None:
        return f"not one column: {missing[0]} and {missing[1]} of one series share no wire"
    if {frozenset(p) for p in used} != {frozenset(p) for p in hops.nets}:
        return "not one column: a box is wired to a box out of its series"
    bad = next(((a, b) for a, b in used if (a, b) not in hops.faces), None)
    if bad is not None:
        return f"not one column: the pins of {bad[0]} and {bad[1]} do not face (N up, S down)"
    return None


def _below_a_box(lanes: Sequence[TreeLane]) -> str | None:
    """Why a joined lane cannot stand: a box above its span, where its head join would level it."""
    above = next((lane for i, lane in enumerate(lanes) if i and _around(lanes, i)[0]), None)
    if above is None:
        return None
    return (
        f"{above.leaves[0]}: a box in parallel below another box has no layout yet; drawn unchained"
    )


def _member(
    lanes: Sequence[TreeLane], i: int, at: tuple[HopFacts, Sequence[LaneDraft]], given: Given
) -> tuple[MemberDraft, set[str]]:
    """Lane i as a member lane, and the nets it draws: its head, inner and foot hop anchors."""
    hops, made = at
    ends, drawn, options = given
    leaves, (before, after) = lanes[i].leaves, _around(lanes, i)
    head = hops.nets[before, leaves[0]] if before else ()
    foot = hops.nets[leaves[-1], after] if after else ()
    links = [head, *(hops.nets[p] for p in pairwise(leaves)), foot]
    cells = tuple(
        Cell(box, "R0", _pin(links[j], box, ends), _pin(links[j + 1], box, ends))
        for j, box in enumerate(leaves)
    )
    top = End("join", None, PinRef(lanes[i].head or "", ""))  # level only: no box stands before
    offset = member_offset(made, cells, drawn, options, 0)
    draft = MemberDraft(made[0].column, i, list(cells), offset, (top, _join(foot, after, ends)))
    return draft, {hop[0] for hop in links if hop}


def _pin(hop: Sequence[str], box: str, ends: Ends) -> str | None:
    return pin_on(hop[0], box, ends) if hop else None


def _join(hop: Sequence[str], box: str | None, ends: Ends) -> End:
    """A join to `box` by the hop's first net; an open end when there is no hop."""
    if not hop or box is None:
        return End("open")
    return End("join", hop[0], PinRef(box, pin_on(hop[0], box, ends)))


def pin_on(net: str, box: str, ends: Ends) -> str:
    """The pin of `box` on `net`."""
    return next(e.pin.pin for e in ends[net] if e.pin.sym == box)


def box_lane(chain: BoxChain, ends: Ends) -> LaneDraft:
    """One lane of the chain's boxes: top pin on the previous hop, bottom pin on the next."""
    cells = []
    for i, box in enumerate(chain.boxes):
        top = pin_on(chain.hops[i - 1][0], box, ends) if i else None
        bottom = pin_on(chain.hops[i][0], box, ends) if i < len(chain.hops) else None
        cells.append(Cell(box, "R0", top, bottom))
    return LaneDraft(f"c:{chain.boxes[0]}", 0, cells, hops=chain.hops)
