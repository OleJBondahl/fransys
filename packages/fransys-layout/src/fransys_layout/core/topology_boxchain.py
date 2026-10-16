"""Stage 1, part 6: boxes joined box to box are one column of boxes (layout-0289; owner F1a).

A hop is a set of nets that each join one pin of one box to one pin of another box and no third
end. A chain is two or more boxes whose hops form a path; each box has the hop pins facing its
neighbours (N toward the previous box, S toward the next) and no other net but an attachment to
a column. It starts at the end whose natural key sorts first. Any other shape keeps today's
flow and gets a CHAIN_REFUSED finding that names its boxes and the reason.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING

from .keys import natural_key
from .topology_elements import NetEnd
from .topology_fans import LaneDraft, attached_pin
from .unionfind import UnionFind
from .values import Cell, Finding

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .topology_chains import Ends
    from .values import Sym

PAIR = 2
MAX_NEIGHBOURS = 2
Pair = tuple[str, str]
Hops = dict[Pair, list[str]]


@dataclass(frozen=True, slots=True)
class BoxChain:
    """The boxes of one chain from its first end, and the nets of each hop between them."""

    boxes: tuple[str, ...]
    hops: tuple[tuple[str, ...], ...]


def box_chains(
    ends: Ends, drawn: Mapping[str, Sym], *, enabled: bool
) -> tuple[Ends, list[LaneDraft], tuple[Finding, ...]]:
    """The ends without the hop nets, one lane per chain, and a finding per refused shape.

    A chain box's net to a column becomes a "chain" end, so the fan stage cross-links the two.
    With `enabled` False (option box_columns, LC4) every box stays a card.
    """
    hops = _hops(ends) if enabled else {}
    chains: list[BoxChain] = []
    notes: list[Finding] = []
    for comp in _components(hops):
        reason = _refusal(comp, hops, ends, drawn)
        if reason is None:
            chains.append(_chain(comp, hops, ends, drawn))
        else:
            boxes = ", ".join(sorted(comp, key=natural_key))
            notes.append(
                Finding("CHAIN_REFUSED", f"{boxes}: {reason}", None, min(comp, key=natural_key))
            )
    lanes = [_lane(c, ends) for c in chains]
    return _without_hops(ends, chains), lanes, tuple(notes)


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


def _path(comp: Sequence[str], hops: Hops) -> list[str]:
    """The boxes from the end that sorts first; only called on a component that is a path."""
    near = _neighbours(comp, hops)
    start = min((b for b in comp if len(near[b]) == 1), key=natural_key)
    out, prev = [start], ""
    while len(out) < len(comp):
        out.append(next(b for b in near[out[-1]] if b != prev))
        prev = out[-2]
    return out


def _refusal(comp: Sequence[str], hops: Hops, ends: Ends, drawn: Mapping[str, Sym]) -> str | None:
    """Why the component is no chain of boxes, or None when it is one."""
    near = _neighbours(comp, hops)
    if any(len(v) > MAX_NEIGHBOURS for v in near.values()):
        return "not one column: a box is joined to three or more boxes"
    if all(len(v) == MAX_NEIGHBOURS for v in near.values()):
        return "not one column: the boxes form a ring"
    own = {n for a, b in hops if a in near for n in hops[a, b]}
    other = _other_net(comp, own, ends)
    if other is not None:
        return f"not one column: a box is also wired by net {other}, which is no column attachment"
    path = _path(comp, hops)
    for a, b in pairwise(path):
        if not _facing(a, b, hops, ends, drawn):
            return f"not one column: the pins of {a} and {b} do not face (N up, S down)"
    return None


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


def _chain(comp: Sequence[str], hops: Hops, ends: Ends, drawn: Mapping[str, Sym]) -> BoxChain:
    """The path with each hop's nets from the pin nearest the box's left edge, then by key.

    The first net of a hop is the one the lane anchors both boxes on, so equal pin offsets on
    both boxes of a hop run straight down.
    """
    path = _path(comp, hops)
    out = []
    for a, b in pairwise(path):
        nets = hops[_pair(a, b)]
        out.append(tuple(sorted(nets, key=lambda n: (_dx(n, a, ends, drawn), natural_key(n)))))
    return BoxChain(tuple(path), tuple(out))


def _dx(net: str, box: str, ends: Ends, drawn: Mapping[str, Sym]) -> int:
    pin = _pin_on(net, box, ends)
    return next(p.dx for p in drawn[box].pins if p.id == pin)


def _pin_on(net: str, box: str, ends: Ends) -> str:
    return next(e.pin.pin for e in ends[net] if e.pin.sym == box)


def _lane(chain: BoxChain, ends: Ends) -> LaneDraft:
    """One lane of the chain's boxes: top pin on the previous hop, bottom pin on the next."""
    cells = []
    for i, box in enumerate(chain.boxes):
        top = _pin_on(chain.hops[i - 1][0], box, ends) if i else None
        bottom = _pin_on(chain.hops[i][0], box, ends) if i < len(chain.hops) else None
        cells.append(Cell(box, "R0", top, bottom))
    return LaneDraft(f"c:{chain.boxes[0]}", 0, cells, hops=chain.hops)


def _without_hops(ends: Ends, chains: Sequence[BoxChain]) -> Ends:
    """Hop nets leave the ends; a chain box's other end is marked "chain"."""
    boxes = {b for c in chains for b in c.boxes}
    gone = {n for c in chains for hop in c.hops for n in hop}
    return {
        net: tuple(NetEnd(e.net, e.elem, e.pin, "chain") if e.pin.sym in boxes else e for e in es)
        for net, es in ends.items()
        if net not in gone
    }
