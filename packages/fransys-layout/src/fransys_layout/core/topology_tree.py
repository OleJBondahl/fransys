"""Stage 1: a series-parallel tree of single poles stands as one column (SERIES-PARALLEL SP4).

`series_tree.tree_lanes` deals the tree's leaves into lanes. Lane 0 is left to the chain walk; each
other lane's poles leave the nets, as `fold_parallel` members do, and come back after the chain
walk as a member lane, joined at head and foot to the lane on its left.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .errors import CoreError
from .series_tree import has_parallel, leaves_of, tree_holds, tree_lanes
from .topology_chains import (
    MemberDraft,
    Node,
    branch_floor,
    cells_of,
    member_offset,
)
from .topology_orient import orient_chain
from .values import End, PinRef

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .series_tree import TreeLane
    from .series_values import Series
    from .sym_values import Sym
    from .topology_chains import Ends, Facts
    from .topology_elements import Elem
    from .topology_fans import LaneDraft
    from .values import Cell, Options

_FORMS = ("pole", "single")  # a single is a pole with one pin wired: it may end lane 0


@dataclass(frozen=True, slots=True)
class TreeFold:
    """One joined lane: its element keys in tree order, and the span of the lane it joins.

    `after` is the earlier fold beside the same span it joins instead, as `member_lanes` steps.
    `source` is lane 0's first and last pole, which stands source first; `holds` the (symbol, G).
    """

    members: tuple[str, ...]
    span: tuple[str, ...]
    after: int | None
    source: tuple[str, str]
    holds: tuple[tuple[str, int], ...] = ()


def tree_folds(
    series: Sequence[Series],
    ends: Ends,
    elems: Mapping[str, Elem],
    drawn: tuple[Mapping[str, Sym], int],
) -> tuple[Ends, tuple[TreeFold, ...]]:
    """The ends without the joined lanes' poles, and one fold per joined lane, tree by tree.

    A tree stands so when it holds a Parallel, every leaf is a drawn single pole on no net with a
    through end, and every pole of a joined lane is wired at both pins.
    """
    poles, wired = _poles(ends, elems)
    folds: list[TreeFold] = []
    for tree in series:
        if has_parallel(tree) and all(x in poles for x in leaves_of(tree)):
            found = _folds(tree, poles, drawn, len(folds))
            if all(wired[m] for f in found for m in f.members):
                folds.extend(found)
    members = {m for f in folds for m in f.members}
    out: Ends = {}
    for net, es in ends.items():
        kept = tuple(e for e in es if e.elem not in members)
        if kept:
            out[net] = kept
    return out, tuple(folds)


def _poles(ends: Ends, elems: Mapping[str, Elem]) -> tuple[dict[str, str], dict[str, bool]]:
    """Each symbol of one pole element on no net with a through end to it; each, wired at both."""
    per_sym = Counter(e.sym for e in elems.values())
    roles: dict[str, set[str]] = {}
    for es in ends.values():
        through = any(e.site == "through" for e in es)
        for e in es:
            if e.elem and e.site in ("top", "bottom"):
                roles.setdefault(e.elem, set()).add("through" if through else e.site)
    poles = {
        e.sym: e.key
        for e in elems.values()
        if e.form in _FORMS and per_sym[e.sym] == 1 and "through" not in roles.get(e.key, set())
    }
    return poles, {k: roles.get(k) == {"top", "bottom"} for k in poles.values()}


def _folds(
    tree: Series, poles: Mapping[str, str], sized: tuple[Mapping[str, Sym], int], base: int
) -> list[TreeFold]:
    """One fold per joined lane of `tree`; `base` is the number of folds before it."""
    drawn, wire_min = sized
    heights = {leaf: drawn[leaf].footprint.h for leaf in leaves_of(tree)}
    lanes = tree_lanes(tree, heights)
    holds = tuple(tree_holds(tree, heights, wire_min).items())
    out: list[TreeFold] = []
    source = (poles[lanes[0].leaves[0]], poles[lanes[0].leaves[-1]])
    for i, lane in enumerate(lanes[1:], start=1):
        parent = lanes[lane.parent or 0].leaves
        span = parent[parent.index(lane.head or "") : parent.index(lane.foot or "") + 1]
        left = _sibling(lanes, i)
        members = tuple(poles[x] for x in lane.leaves)
        after = None if left is None else base + left - 1
        out.append(TreeFold(members, tuple(poles[x] for x in span), after, source, holds))
    return out


def _sibling(lanes: Sequence[TreeLane], i: int) -> int | None:
    """The last lane before lane `i` joined at the same span, else None."""
    key = (lanes[i].parent, lanes[i].head, lanes[i].foot)
    found = [j for j in range(1, i) if (lanes[j].parent, lanes[j].head, lanes[j].foot) == key]
    return found[-1] if found else None


def source_first(
    paths: Sequence[tuple[Node, ...]], folds: Sequence[TreeFold], facts: Facts
) -> tuple[tuple[Node, ...], ...]:
    """The chains with each tree's lane 0 turned to stand source first, the rest as given."""
    ends = {f.source for f in folds}
    return tuple(orient_chain(p, facts, turn=True) if _upside_down(p, ends) else p for p in paths)


def _upside_down(path: Sequence[Node], ends: AbstractSet[tuple[str, str]]) -> bool:
    at = {n.elem: i for i, n in enumerate(path)}
    return any(a in at and b in at and at[a] > at[b] for a, b in ends)


def tree_member_lanes(
    folds: Sequence[TreeFold], lanes: Sequence[LaneDraft], facts: Facts, options: Options
) -> list[MemberDraft]:
    """One member lane per fold, right of its column, joined to its span or its left sibling."""
    out: list[MemberDraft] = []
    for fold in folds:
        home, top_cell, bottom_cell = _joined(fold, [*lanes, *out], out, facts)
        top = PinRef(top_cell.sym, top_cell.top_pin or "")
        bottom = PinRef(bottom_cell.sym, bottom_cell.bottom_pin or "")
        nets = (facts.net_of.get(top), facts.net_of.get(bottom))
        cells = _cells(fold.members, nets, facts)
        column = [lane for lane in (*lanes, *out) if lane.column == home.column]
        offset = member_offset(
            column, cells, facts.syms, options, branch_floor(column, options.parallel_pitch)
        )
        ends = (End("join", nets[0], top), End("join", nets[1], bottom))
        index = 1 + max(lane.index for lane in column)
        out.append(MemberDraft(home.column, index, list(cells), offset, ends))
    return out


def _joined(
    fold: TreeFold, lanes: Sequence[LaneDraft], made: Sequence[MemberDraft], facts: Facts
) -> tuple[LaneDraft, Cell, Cell]:
    """The lane a fold joins and its top and bottom cell: the left sibling's, else the span's."""
    if fold.after is not None:
        left = made[fold.after]
        return left, left.cells[0], left.cells[-1]
    syms = {facts.elems[k].sym for k in fold.span}
    home = next((lane for lane in lanes if any(c.sym in syms for c in lane.cells)), None)
    if home is None:
        msg = f"no lane holds the span {fold.span} a series-parallel member joins"
        raise CoreError(msg)
    at = [i for i, c in enumerate(home.cells) if c.sym in syms]
    return home, home.cells[min(at)], home.cells[max(at)]


def _cells(
    members: Sequence[str], nets: tuple[str | None, str | None], facts: Facts
) -> tuple[Cell, ...]:
    """The member poles head to foot, from the one on the joined top net, each pin to the next."""
    es = [facts.elems[k] for k in members]
    first = es[0]
    turn = nets[0] not in {facts.net_of.get(PinRef(first.sym, p or "")) for p in _ends(first)}
    nodes: list[Node] = []
    at = nets[1] if turn else nets[0]
    for e in es:
        top, bottom = _ends(e)
        if facts.net_of.get(PinRef(e.sym, top or "")) != at:
            top, bottom = bottom, top
        nodes.append(Node(e.key, top, bottom))
        at = facts.net_of.get(PinRef(e.sym, bottom or ""))
    path = orient_chain(tuple(nodes), facts, turn=turn)
    return cells_of(path, facts.elems, facts.syms, facts.flip_turn)


def _ends(e: Elem) -> tuple[str | None, str | None]:
    return e.n_pin, e.s_pin
