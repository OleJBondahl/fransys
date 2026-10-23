"""Stage 1, part 6: boxes joined box to box are one column of boxes (layout-0289; owner F1a).

A hop is a set of nets that each join one pin of one box to one pin of another box and no third
end. A chain is two or more boxes whose hops form a path; each box has the hop pins facing its
neighbours (N toward the previous box, S toward the next) and no other net but an attachment to
a column. Its order is the run of a `Series` that holds its boxes (SERIES-PARALLEL SP3), else
from the end whose natural key sorts first. Any other shape keeps today's flow and gets a
CHAIN_REFUSED finding that names its boxes and the reason.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING

from .keys import natural_key
from .series_values import Series
from .topology_boxtree import BoxChain, HopFacts, box_lane, pin_on, tree_column, tree_of
from .topology_elements import NetEnd
from .topology_fans import LaneDraft, attached_pin
from .unionfind import UnionFind
from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .series_values import SeriesPart
    from .sym_values import Sym
    from .topology_boxtree import Given, Made
    from .topology_chains import Ends
    from .values import Options

PAIR = 2
MAX_NEIGHBOURS = 2
Pair = tuple[str, str]
Hops = dict[Pair, list[str]]
Runs = list[tuple[str, ...]]


def box_chains(
    ends: Ends, drawn: Mapping[str, Sym], options: Options, series: Sequence[Series] = ()
) -> tuple[Ends, list[LaneDraft], tuple[Finding, ...]]:
    """The ends without the hop nets, the lanes of each column of boxes, a finding per refusal.

    A column box's net to a column becomes a "chain" end; with box_columns off every box is a card.
    `series` gives the order: a tree of exactly a component's boxes stands as its tree (SP4).
    """
    hops = _hops(ends) if options.box_columns else {}
    lanes: list[LaneDraft] = []
    boxes: set[str] = set()
    gone: set[str] = set()
    notes: list[Finding] = []
    for comp in _components(hops):
        made = _column(comp, hops, (ends, drawn, options), series)
        if isinstance(made, str):
            names = ", ".join(sorted(comp, key=natural_key))
            notes.append(
                Finding("CHAIN_REFUSED", f"{names}: {made}", None, min(comp, key=natural_key))
            )
        else:
            lanes += made[0]
            boxes |= set(comp)
            gone |= made[1]
    return _without_hops(ends, boxes, gone), lanes, tuple(notes)


def _column(comp: Sequence[str], hops: Hops, given: Given, series: Sequence[Series]) -> Made | str:
    """The lanes of the component's column and the hop nets they draw, else why it is none."""
    ends, drawn, _ = given
    tree = tree_of(comp, series)
    if tree is not None:
        return _other_reason(comp, hops, ends) or tree_column(
            tree, _hop_facts(comp, hops, ends, drawn), given
        )
    runs = series_runs(series)
    reason = _refusal(comp, hops, (ends, runs), drawn)
    if reason is not None:
        return reason
    chain = _chain(_path(comp, hops, runs), hops, ends, drawn)
    return [box_lane(chain, ends)], {n for hop in chain.hops for n in hop}


def _pair(a: str, b: str) -> Pair:
    lo, hi = sorted((a, b), key=natural_key)
    return lo, hi


def _hops(ends: Ends) -> Hops:
    """Box pair to the nets that join exactly those two boxes by one pin each."""
    out: Hops = defaultdict(list)
    for net in sorted(ends, key=natural_key):
        es = ends[net]
        syms = [e.pin.sym for e in es]
        if len(es) == PAIR and syms[0] != syms[1] and all(e.site == "boxpin" for e in es):
            out[_pair(syms[0], syms[1])].append(net)
    return out


def _components(hops: Hops) -> list[list[str]]:
    uf = UnionFind()
    for a, b in hops:
        uf.union(a, b)
    groups: dict[str, list[str]] = defaultdict(list)
    for box in sorted({x for pair in hops for x in pair}, key=natural_key):
        groups[uf.find(box)[0]].append(box)
    return sorted(groups.values(), key=lambda g: natural_key(g[0]))


def _neighbours(comp: Sequence[str], hops: Hops) -> dict[str, list[str]]:
    near: dict[str, list[str]] = {b: [] for b in comp}
    for a, b in sorted(hops, key=lambda p: (natural_key(p[0]), natural_key(p[1]))):
        if a in near:
            near[a].append(b)
            near[b].append(a)
    return near


def series_runs(series: Sequence[SeriesPart]) -> Runs:
    """Each run of two or more leaves side by side in a `Series` of the trees, in tree order."""
    out: Runs = []
    for part in series:
        if isinstance(part, str):
            continue
        run: list[str] = []
        for p in (*part.parts, None):
            if isinstance(p, str) and isinstance(part, Series):
                run.append(p)
                continue
            out.extend([tuple(run)] if len(run) > 1 else [])
            run = []
            out.extend(series_runs((p,)) if p is not None else [])
    return out


def _path(comp: Sequence[str], hops: Hops, runs: Runs) -> list[str]:
    """The boxes in the order of the series run that joins them hop by hop, else from the first end.

    Only called on a component that is a path.
    """
    for run in runs:
        for i in range(len(run) - len(comp) + 1):
            window = run[i : i + len(comp)]
            if set(window) == set(comp) and all(_pair(a, b) in hops for a, b in pairwise(window)):
                return list(window)
    near = _neighbours(comp, hops)
    start = min((b for b in comp if len(near[b]) == 1), key=natural_key)
    out, prev = [start], ""
    while len(out) < len(comp):
        out.append(next(b for b in near[out[-1]] if b != prev))
        prev = out[-2]
    return out


def _refusal(
    comp: Sequence[str], hops: Hops, given: tuple[Ends, Runs], drawn: Mapping[str, Sym]
) -> str | None:
    """Why the component is no chain of boxes, or None when it is one."""
    ends, runs = given
    near = _neighbours(comp, hops)
    if any(len(v) > MAX_NEIGHBOURS for v in near.values()):
        return "not one column: a box is joined to three or more boxes"
    if all(len(v) == MAX_NEIGHBOURS for v in near.values()):
        return "not one column: the boxes form a ring"
    other = _other_reason(comp, hops, ends)
    if other is not None:
        return other
    path = _path(comp, hops, runs)
    for a, b in pairwise(path):
        if not _facing(a, b, hops, ends, drawn):
            return f"not one column: the pins of {a} and {b} do not face (N up, S down)"
    return None


def _other_reason(comp: Sequence[str], hops: Hops, ends: Ends) -> str | None:
    """Why a box of the component is no column cell: it is wired by a net that is no hop."""
    other = _other_net(comp, {n for a, b in hops if a in comp for n in hops[a, b]}, ends)
    if other is None:
        return None
    return f"not one column: a box is also wired by net {other}, which is no column attachment"


def _other_net(comp: Sequence[str], own: AbstractSet[str], ends: Ends) -> str | None:
    """The first net that touches a box of the component and is neither a hop nor an attachment."""
    for net in sorted(ends, key=natural_key):
        touches = any(e.pin.sym in comp for e in ends[net])
        if touches and net not in own and attached_pin(ends[net]) is None:
            return net
    return None


def _facing(a: str, b: str, hops: Hops, ends: Ends, drawn: Mapping[str, Sym]) -> bool:
    """True when the hop nets leave a by S pins and reach b by N pins."""
    key = _pair(a, b)
    side = {(s.id, p.id): p.side for s in (drawn[a], drawn[b]) for p in s.pins}
    pins = [e.pin for net in hops[key] for e in ends[net]]
    return all(side[p.sym, p.pin] == ("S" if p.sym == a else "N") for p in pins)


def _chain(path: Sequence[str], hops: Hops, ends: Ends, drawn: Mapping[str, Sym]) -> BoxChain:
    """The path with each hop's nets from the pin nearest the box's left edge, then by key.

    The first net of a hop is the one the lane anchors both boxes on, so equal pin offsets on
    both boxes of a hop run straight down.
    """
    out = []
    for a, b in pairwise(path):
        nets = hops[_pair(a, b)]
        out.append(tuple(sorted(nets, key=lambda n: (_dx(n, a, ends, drawn), natural_key(n)))))
    return BoxChain(tuple(path), tuple(out))


def _hop_facts(comp: Sequence[str], hops: Hops, ends: Ends, drawn: Mapping[str, Sym]) -> HopFacts:
    """Each hop of the component both ways up: its nets in lane order, and whether it faces."""
    nets: dict[tuple[str, str], tuple[str, ...]] = {}
    for a, b in (k for k in hops if k[0] in comp):
        for up, down in ((a, b), (b, a)):
            nets[up, down] = _chain((up, down), hops, ends, drawn).hops[0]
    faces = {p for p in nets if _facing(p[0], p[1], hops, ends, drawn)}
    return HopFacts(nets, faces)


def _dx(net: str, box: str, ends: Ends, drawn: Mapping[str, Sym]) -> int:
    pin = pin_on(net, box, ends)
    return next(p.dx for p in drawn[box].pins if p.id == pin)


def _without_hops(ends: Ends, boxes: AbstractSet[str], gone: AbstractSet[str]) -> Ends:
    """The nets a column draws leave the ends; a column box's other end is marked "chain"."""
    return {
        net: tuple(NetEnd(e.net, e.elem, e.pin, "chain") if e.pin.sym in boxes else e for e in es)
        for net, es in ends.items()
        if net not in gone
    }
